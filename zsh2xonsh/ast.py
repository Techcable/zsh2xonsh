"""Basic AST for zsh code"""
import itertools
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
    def translate(self, settings: translate.Settings) -> str:
        pass

@dataclass
class Expression(metaclass=ABCMeta):
    span: Span

    @abstractmethod
    def translate(self, settings: translate.Settings) -> str:
        pass

@dataclass
class ExprStmt(Statement):
    expr: Expression

    def translate(self, settings: translate.Settings) -> str:
        return self.expr.translate(settings)

@dataclass
class QuotedExpression(Expression):
    # The text on the inside, without being interpreted
    inside_text: str

    def translate(self, settings: translate.Settings) -> str:
        txt = self.inside_text
        if translate.is_simple_quoted(txt):
            return repr(txt)
        else:
            return f"ctx.zsh_expand_quote({txt!r})"

@dataclass
class SubcommandExpr(Expression):
    command: str

    def translate(self, settings: translate.Settings) -> str:
        return f"ctx.zsh({self.command!r})"

@dataclass
class LiteralExpr(Expression):
    text: str

    def translate(self, settings: translate.Settings) -> str:
        if self.text.startswith('~'):
            return f"ctx.expand_literal({self.text!r})"
        elif translate.is_valid_integer(self.text):
            return f"{int(self.text)}"
        else:
            return f"{self.text!r}"

@dataclass
class TestExpr(Expression):
    text: str

    def translate(self, settings: translate.Settings) -> str:
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

    def translate(self, settings: translate.Settings) -> str:
        if self.kind == AssignmentKind.EXPORT:
            if settings.is_path_like_var(self.target) or settings.strict_env_types:
                return f"ctx.assign_typed_var({self.target!r},{self.value.translate(settings)})"
            else:
                return f"${self.target}={self.value.translate(settings)}"
        elif self.kind == AssignmentKind.LOCAL:
            return f"{self.target}=ctx.assign_local({self.target!r}, {self.value.translate(settings)})"
        elif self.kind == AssignmentKind.ALIAS:
            alias_impl = None
            if isinstance(self.value, LiteralExpr):
                # TODO: Pre-expands `~` ahead of time, when it really should be done at invocation time
                alias_impl = f'[{self.value.translate(settings)}]'
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

    def translate(self, settings: translate.Settings) -> str:
        return '\n'.join([
            f"if {self.condition.translate(settings)}:",
            *((' ' * 4) + stmt.translate(settings) for stmt in self.then)
        ])


@dataclass
class FunctionDeclaration(Statement):
    name: str
    body: list[Statement]

    def translate(self, settings: translate.Settings) -> str:
        # This is the most complex of them all
        # This translates into a python function that accepts variable positional arguments
        #
        # Each arg is unpacked into a local $1 $2 $3 accessible from inside the function
        indent = ' ' * 4
        # TODO: This could probably be implemented with some sort of decorator
        header = [
            f"def {self.name}(*args, parent_ctx):",
            f"{indent}with parent_ctx.begin_function({self.name!r}, args) as ctx:"
        ]
        body = [
            # NOTE: This is effectively `flatten`. Used because stmt.translate() might itself be multiline
            *itertools.chain.from_iterable((stmt.translate(settings).splitlines() for stmt in self.body))
        ]
        return '\n'.join([*header, *((indent * 2) + b for b in body)])

class FunctionInvocationKind(Enum):
    EXTRA_BUILTIN = "extra"
    STANDARD_BUILTIN = "std"
    USER_DEFINED_FUNCTION = "user-func"

_STANDARD_BUILTIN_MAP = {
    "echo": "print"
}

@dataclass
class FunctionInvocation(Statement):
    name: str
    args: list[Expression]
    kind: FunctionInvocationKind

    def translate(self, settings: translate.Settings) -> str:
        def format_call(name, args, **kwargs):
            if len(args) <= 1:
                sep = ""
                prefix = ""
            else:
                sep = "\n"
                prefix = ' ' * 2
            return sep.join([
                f"{name}(",
                *(f"{prefix}{arg}," for arg in args),
                *(f"{prefix}{key}={value}," for key, value in kwargs.items()),
                ")"
            ])
        args = []
        kwargs = {}
        if self.kind == FunctionInvocationKind.EXTRA_BUILTIN:
            actual_name = self.name
        elif self.kind == FunctionInvocationKind.STANDARD_BUILTIN:
            try:
                actual_name = _STANDARD_BUILTIN_MAP[self.name]
            except KeyError:
                raise ZshError(f"Not yet implemented: Builtin {self.name}") from None
        elif self.kind == FunctionInvocationKind.USER_DEFINED_FUNCTION:
            actual_name = self.name
            kwargs['parent_ctx'] = 'ctx'
        else:
            raise AssertionError
        args.extend((arg.translate(settings) for arg in self.args))
        return format_call(
            actual_name, args, **kwargs
        )
