# -*- coding: utf8

import argparse
import logging

from . import parser

logger = logging.getLogger('lexicalParser')


def setup_logging(level):
    log_fmt = logging.Formatter('[%(levelname)s] %(message)s')
    log_handler =  logging.StreamHandler()
    log_handler.setFormatter(log_fmt)
    logger.addHandler(log_handler)
    logger.setLevel(level)


def main():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('source',
                            help='Source code file path')
    arg_parser.add_argument('-d',
                            '--debug',
                            action='store_true',
                            help='Print debugging messages',
                            default=False)

    args = arg_parser.parse_args()

    setup_logging(logging.DEBUG if args.debug else logging.INFO)

    logger.debug('recv arguments: %s', args.__dict__)
    logger.info('source code to parse: %s', args.source)

    lex_parser = parser.LexicalParser.from_path(args.source)
    result = lex_parser.parse()

    if result == False:
        logger.error('failed to parse path')
    else:
        print()
        mask = '{:<20}{:<50}'
        print(mask.format('Type', 'Text'))
        print('-' * 70)
        for token in result:
            print(mask.format(token.type, token.text))
