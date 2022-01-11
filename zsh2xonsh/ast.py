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
            return f"ctx.zsh_expand_quote({txt!r})"

@dataclass
class SubcommandExpr(Expression):
    command: str

    def translate(self) -> str:
        return f"ctx.zsh({self.command!r})"

@dataclass
class LiteralExpr(Expression):
    text: str

    def translate(self) -> str:
        if self.text.startswith('~'):
            return f"ctx.expand_literal({self.text!r})"
        elif translate.is_valid_integer(self.text):
            return f"{int(self.text)}"
        else:
            return f"{self.text!r}"

@dataclass
class TestExpr(Expression):
    text: str

    def translate(self) -> str:
        return f"ctx.zsh_test({self.text!r})"

class AssignmentKind(Enum):
    EXPORT = "export"
    LOCAL = "local"
    ALIAS = "alias"

@dataclass
class AssignmentStmt(Statement):
    kind: AssignmentKind
    target: str
    value: Expression

    def translate(self) -> str:
        if self.kind == AssignmentKind.EXPORT:
            if self.target in translate.PATH_LIKE_VARS:
                return f"ctx.assign_path_var(${self.target},{self.value.translate()},var={self.target!r})"
            else:
                return f"${self.target}={self.value.translate()}"
        elif self.kind == AssignmentKind.LOCAL:
            return f"{self.target}=ctx.assign_local({self.target!r}, {self.value.translate()})"
        elif self.kind == AssignmentKind.ALIAS:
            alias_impl = None
            if isinstance(self.value, LiteralExpr):
                # TODO: Pre-expands `~` ahead of time, when it really should be done at invocation time
                alias_impl = f'[{self.value.translate()}]'
            elif isinstance(self.value, QuotedExpression):
                if translate.can_safely_be_split(self.value.inside_text):
                    alias_impl = '[' + ', '.join(map(repr, self.value.inside_text.split(' '))) + ']'
                else:
                    # TODO: This won't have acess to other aliases
                    alias_impl = f"ctx.zsh_impl_complex_alias({self.value.inside_text!r})"
            else:
                raise ShellParseError("Don't know how to translate alias target", self.value.span.start)
            if not translate.is_simple_quoted(self.target):
                raise ShellParseError("Alias target too complex", self.span.start)
            return f"aliases[{self.target!r}]={alias_impl}"
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



