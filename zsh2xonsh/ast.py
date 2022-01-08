"""Basic AST for zsh code"""
from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from enum import Enum

from . import translate

@dataclass
class Location:
    line: int
    offset: int

@dataclass
class Span:
    start: Location
    end: Location

@dataclass
class Statement(metaclass=ABCMeta):
    span: Span

    @abstractmethod
    def translate(self) -> str:
        pass

@dataclass
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
        txt = self.inside_text
        if translate.is_simple_quoted(txt):
            return repr(txt)
        else:
            return f"runtime.zsh_expand_quote({txt!r})"


@dataclass
class SubcommandExpr(Expression):
    command: str

    def translate(self) -> str:
        return f"runtime.zsh({self.command!r})"

@dataclass
class LiteralExpr(Expression):
    text: str

    def translate(self) -> str:
        if self.text.startswith('~'):
            return f"runtime.expand_literal({self.text!r})"
        elif translate.is_valid_integer(self.text):
            return f"{int(self.text)}"
        else:
            return f"{self.text!r}"

@dataclass
class TestExpr(Expression):
    text: str

    def translate(self) -> str:
        return f"runtime.zsh_test({self.text!r})"

class AssignmentKind(Enum):
    EXPORT = "export"
    LOCAL = "local"

@dataclass
class AssignmentStmt(Statement):
    kind: AssignmentKind
    target: str
    value: Expression

    def translate(self) -> str:
        if self.kind == AssignmentKind.EXPORT:
            if self.target in translate.PATH_LIKE_VARS:
                return f"runtime.assign_path_var(${self.target},{self.value.translate()},var={self.target!r})"
            else:
                return f"${self.target}={self.value.translate()}"
        elif self.kind == AssignmentKind.LOCAL:
            return f"{self.target}={self.value.translate()}"
        else:
            raise AssertionError

@dataclass
class ConditionalStmt(Statement):
    condition: Expression
    then: list[Statement]

    def translate(self) -> str:
        return '\n'.join([
            f"if {self.condition.translate()}:",
            *((' ' * 4) + stmt.translate() for stmt in self.then)
        ])


@dataclass
class FunctionInvocation(Statement):
    name: str
    args: list[Expression]

    def translate(self) -> str:
        if len(self.args) <= 1:
            sep = ""
            prefix = ""
        else:
            sep = "\n"
            prefix = ' ' * 2
        return sep.join([
            f"{self.name}(",
            *(prefix + arg.translate() for arg in self.args),
            ")"
        ])



