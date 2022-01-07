"""Basic AST for zsh code"""
from abc import ABCMeta, abstractmethod
from dataclasses import dataclass

import ast as pyast

@dataclass(slots=True)
class Location:
    line: int
    offset: int

@dataclass(slots=True)
class Span:
    start: Location
    end: Location

@dataclass(slots=True)
class Statement(metaclass=ABCMeta):
    span: Span

    @abstractmethod
    def translate(self) -> str:
        pass

@dataclass(slots=True)
class Expression(metaclass=ABCMeta):
    span: Span

    @abstractmethod
    def translate(Self) -> str:
        pass

@dataclass
class ExprStmt(Statement):
    expr: Expression

    def translate(self) -> str:
        return self.expr.translate()

@dataclass
class QuotedExpression(Expression):
    # The text on the inside, without being interpreted
    inside_text: str

    def translate(self) -> str:
        


@dataclass
class SubcommandExpr(Expression):
    command: str

@dataclass
class LiteralExpr(Expression):
    text: str

@dataclass
class TestExpr(Expression):
    text: str

class AssignmentKind(Enum):
    EXPORT = "export"
    LOCAL = "local"

@dataclass
class AssignmentStmt(Statement):
    kind: AssignmentKind
    value: Expression

@dataclass
class ConditionalStmt(Statement):
    condition: Expression
    then: list[Statement]

@dataclass
class ExtraFunctionInvocation(Statement):
    name: str
    args: list[Expression]
