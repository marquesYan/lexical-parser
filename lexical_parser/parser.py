# -*- coding: utf8

import logging
import string
from typing import Union, List

from .data import Token, State, TokenType

logger = logging.getLogger('lexicalParser')

# Text used to identify some states
operators = '+-/*'
delimiters = '\r\n '


def read_file(path):
    with open(path) as fp:
        return fp.readlines()


class LexicalParser:
    # A quick state is a special type of state that when reached,
    # automatically calls the related state handler. 
    # 
    # Traditionally, states are not quick. When the state change,
    # the parser will only execute the related handler on the next loop. 
    QuickStates = [
        State.IDENTIFIER_BEGIN,
        State.OPERATOR,
        State.ATTRIBUTION,
        State.DELIMITER,
        State.NUMBER_BEGIN,
    ]

    def __init__(self, contents: List[str]):
        self.contents = contents
        self.tokens = set()

        # Represent the current state
        self.state = None

        # Some states need to store gathered chars that are
        # retrieved later on another state to create a token
        self.chars = []

        # Pending is a mechanism used for token delayed creation.
        # When a state may be composed by many characters, it
        # register a new pending in order for the parser to know 
        # that when it reaches a delimeter or end of line, a new token
        # should be created.
        #
        # One example is the Number token.
        #
        self.pending_names = []
        self.pending_finalizers = {}
        self.pending_meta = {}

        # Flag used to locate explicit parsing errors on the current line
        self.errored = False

        self.char_index, self.char = None, None
        self.line_index, self.line = None, None

        self.state_handlers = {
            State.INITIAL: self.handle_initial,
            State.IDENTIFIER_BEGIN: self.handle_identifier_begin,
            State.IDENTIFIER_END: self.handle_identifier_end,
            
            State.NUMBER_BEGIN: self.handle_number_begin,
            State.NUMBER_END: self.handle_number_end,

            State.OPERATOR: self.handle_operator,
            State.ATTRIBUTION: self.handle_attribution,

            State.DELIMITER: self.handle_delimiter,
        }

    @staticmethod
    def from_path(path):
        return LexicalParser(read_file(path))

    def handle_initial(self):
        if self.char in string.ascii_uppercase:
            self.set_state(State.IDENTIFIER_BEGIN)
        elif self.char in string.digits:
            self.set_state(State.NUMBER_BEGIN)
        elif self.char in operators:
            self.set_state(State.OPERATOR)
        elif self.char == '=':
            self.set_state(State.ATTRIBUTION)
        elif self.char in delimiters:
            self.set_state(State.DELIMITER)
        else:
            self.handle_unknow_char()

    def handle_unknow_char(self):
        self.errored = True
        self.debug_ctx()

        index = self.char_index if self.char_index == 0 else self.char_index - 1
        logger.error(
            'syntax error at line %d: %s',
            self.line_index + 1,
            self.line[index:]
        )

    def handle_identifier_begin(self):
        logger.debug('got identifier begin: (%s)', self.char)
        self.set_state(State.IDENTIFIER_END)

        self.add_pending(
            State.IDENTIFIER_END,
            lambda: self.add_token_chars(TokenType.IDENTIFIER)
        )

        # Call common code that check whether it's the end or not
        self.handle_identifier_end()

    def handle_identifier_end(self):
        logger.debug('got identifier end: (%s)', self.char)
        if self.at_the_end(string.ascii_letters + string.digits + '_'):
            self.finish_pending(State.IDENTIFIER_END)

    def handle_number_begin(self):
        logger.debug('got number begin: (%s)', self.char)
        self.set_state(State.NUMBER_END)

        self.add_pending(
            State.NUMBER_END,
            lambda: self.add_token_chars(TokenType.NUMBER)
        )

        # Call common code that check whether it's the end or not
        self.handle_number_end()

    def handle_number_end(self):
        logger.debug('got number end: (%s)', self.char)
        if self.at_the_end(string.digits):
            self.finish_pending(State.NUMBER_END)

    def handle_operator(self):
        self.add_token(TokenType.OPERATOR, self.char)
        self.set_state(State.INITIAL)

    def handle_attribution(self):
        self.add_token(TokenType.ATTRIBUTION, self.char)
        self.set_state(State.INITIAL)

    def handle_delimiter(self):
        logger.debug(
            'turning back to initial state, found delimeter: (ascii %s)',
            hex(ord(self.char))
        )

        self.set_state(State.INITIAL)
        self.finish_last_pending()

    def at_the_end(self, comparison):
        if self.char in comparison:
            self.chars.append(self.char)
            return self.is_last_char_of_line()

        self.set_state(State.INITIAL, now=True)
        return True

    def add_pending(self, name, finalizer):
        self.pending_names.append(name)
        self.pending_finalizers[name] = finalizer
        self.pending_meta[name] = {
            'line': self.line,
            'line_index': self.line_index,
            'char_index': self.char_index,
            'char': self.char,
        }

    def finish_last_pending(self):
        if len(self.pending_names) > 0:
            name = self.pending_names[-1]
            self.finish_pending(name)

    def finish_pending(self, name):
        if name in self.pending_finalizers:
            finalizer = self.pending_finalizers.pop(name)
            self.pending_names.remove(name)
            self.pending_meta.pop(name)
            finalizer()

    def add_token_chars(self, token_type):
        self.add_token(token_type, ''.join(self.chars))
        self.chars = []

    def add_token(self, token_type, text):
        token = Token(token_type, text)
        logger.debug('new token: %s', token)
        self.tokens.add(token)

    def is_end_of_line(self):
        return self.char_index == len(self.line)

    def is_last_char_of_line(self):
        return self.char_index == len(self.line) - 1

    def set_state(self, new_state, now=False):
        logger.debug('changing state: %s -> %s', self.state, new_state)
        self.state = new_state
        if now or new_state in self.QuickStates or self.is_end_of_line():
            self.call_state()

    def parse(self) -> Union[bool, List[Token]]:
        for line_index, line in enumerate(self.contents):
            # Remove bad characters considered delimeters (leading and trailing)
            self.line = line.strip(delimiters)
            self.line_index = line_index

            # Every line is a new beggining
            self.state = State.INITIAL

            for char_index, char in enumerate(self.line):
                if self.errored:
                    # This line is over, jump to the next
                    break

                self.char_index = char_index
                self.char = char

                logger.debug('reading character: (ascii %s)', hex(ord(self.char)))

                self.call_state()
                self.debug_ctx()

            logger.debug('finished line: %d', self.line_index)

        if self.errored:
            return False

        if len(self.pending_names) > 0:
            for name in self.pending_names:
                meta = self.pending_meta[name]
                logger.error(
                    'syntax error at line %d: %s',
                    meta['line_index'] + 1,
                    meta['line'][meta['char_index']:]
                )
            return False

        return self.tokens

    def debug_ctx(self):
        logger.debug(
            'state | index | char: %s | %d | %s',
            self.state,
            self.char_index,
            self.char
        )

    def call_state(self):
        if self.state in self.state_handlers:
            logger.debug('calling current state: %s', self.state)
            self.state_handlers[self.state]()