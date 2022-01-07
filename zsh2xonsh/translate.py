#a The actual translation logic

# Requires python 3.10 match statement
# However the rest of the code should be python 3.9 compatible....
from .ast import *

class XonshTranslator:
    __slots__ = "extra_functions", "_lines", "_parts"
    extra_functions: set[str]
    _lines: list[str]
    _parts: list[str]

    def __init__(self, *, extra_functions: set[str] = frozenset())
        self.extra_functions = extra_functions
        self._lines = []
        self._parts = []


    def write(self, s: str):
        assert s is not None
        self._parts.append(s)

    def writeline(self, txt: str=""):
        self._parts.append(txt)
        self._parts.append('\n')

    def expression(self, expr: Expression):
        match expr:
            cse
            case _:
                raise TypeError(f"Unkown expression type: {expr}")

    def statement(self, stmt: Statement):
        match stmt:
            ConditionalStmt():


    def lines(self) -> list[str]:
        if self._parts:
            text = ''.join(self._parts)
            self._lines.extend(text.splitlines())
            self._parts.clear()
        return self.lines
