import dataclasses


class State:
    INITIAL = '0'
    IDENTIFIER_BEGIN = '1'
    IDENTIFIER_END = '2'
    NUMBER_BEGIN = '3'
    NUMBER_END = '4'
    ATTRIBUTION = '5'
    OPERATOR = '6'
    DELIMITER = '7'


class TokenType:
    IDENTIFIER = 'identifier'
    NUMBER = 'number'
    OPERATOR = 'operator'
    ATTRIBUTION = 'attribution'


@dataclasses.dataclass()
class Token:
    type: str
    text: str

    def __hash__(self) -> int:
        return hash(self.type + self.text)
