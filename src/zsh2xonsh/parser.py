"""A basic recursive decent parser for `zsh` code.

Please shoot me"""

import re
from enum import Enum
from typing import Callable, Optional, Union

from click import ClickException

from . import translate
from .ast import *


class TranslationError(RuntimeError):
    location: Optional[Location]
    msg: str

    def __init__(self, msg: str, location: Optional[Location]):
        super().__init__(msg)
        assert msg is not None and isinstance(msg, str), f"Unexpected msg: {msg!r}"
        assert location is None or isinstance(
            location, Location
        ), "Unexpected location: {location!r} w/ msg {msg!r}"
        self.location = location

    @property
    def kind(self) -> str:
        return "Translation error"

    def __repr__(self):
        return str(self)

    def __str__(self):
        msg = f"{self.kind}: {super().__str__()}"
        if self.location is not None:
            msg += f" @ {self.location}"
        return msg


class ExpressionContext(Enum):
    # Interpret unquoted values as command
    #
    # Example:
    # if foo; then echo "foo"; fi
    # Then `foo` is interpreted as a command
    COMMAND = "command"
    # Intepret unquoted values as a string
    #
    # Example:
    # local var=foo;
    # echo $var; # prints "foo"
    VALUE = "value"


class ShellParseError(TranslationError):
    @property
    def kind(self) -> str:
        return "Error parsing zsh subset (NYI?)"


WORD_PATTERN = re.compile(r"\w+")
WHITESPACE_PATTERN = re.compile(r"\s*")
# NOTE: We only allow what the translator considers safe
SHELL_LITERAL_PATTERN = translate.SAFE_LITERAL_PATTERN
STANDARD_BUILTINS = {"echo"}


class ShellParser:
    """A recursive decent parser for a limited subset of `zsh`.

    Please shoot me :)"""

    __slots__ = (
        "_current_line",
        "lines",
        "_lineno",
        "_offset",
        "dialect",
        "extra_builtins",
        "_stmt_dispatch",
        "_defined_functions",
    )
    lines: list[str]
    _current_line: Optional[str]  # None if EOF
    extra_builtins: set[str]
    # HACK: This should not be in the parser
    _defined_functions: set[str]
    dialect: str

    def __init__(
        self, lines: list[str], *, extra_builtins: set[str] = frozenset(), dialect="zsh"
    ):
        global _BUILTIN_STMT_DISPATCH
        if dialect != "zsh":
            raise NotImplementedError(f"Unsupported dialect: {dialect}")
        assert isinstance(extra_builtins, (set, frozenset))
        self._current_line = lines[0] if lines else None
        self.lines = lines
        self.dialect = dialect
        self.extra_builtins = extra_builtins
        dispatch = _BUILTIN_STMT_DISPATCH.copy()
        # In theory we could hoist this out of here, but it's not really worth it
        for bltn in STANDARD_BUILTINS:
            assert (
                WORD_PATTERN.fullmatch(bltn) is not None
            ), "Invalid builtin function: {bltn!r}"
            assert (
                bltn not in dispatch
            ), "The standard builtin function {bltn!r} conflicts with an existing builtin"
            dispatch[bltn] = ShellParser.function_invocation
        if extra_builtins:
            for extra in extra_builtins:
                assert (
                    WORD_PATTERN.fullmatch(extra) is not None
                ), "Invalid extra function: {extra!r}"
                assert (
                    extra not in dispatch
                ), 'The "extra" function {extra!r} conflicts with a builtin'
                dispatch[extra] = ShellParser.function_invocation
        self._defined_functions = set()
        self._lineno = 1
        self._offset = 0
        self._stmt_dispatch = dispatch

    @property
    def location(self) -> Location:
        return Location(line=self._lineno, offset=self._offset)

    @property
    def remaining_line(self) -> Optional[str]:
        try:
            return self._current_line[self._offset :]
        except TypeError:
            assert self._current_line is None, "Unexepected type: {self._current_line}"
            return None

    def take_while(
        self,
        pred: Union[set[str], Callable[[str], bool], re.Pattern],
        *,
        multiline=False,
    ) -> str:
        assert not multiline
        if isinstance(pred, re.Pattern):
            if self._current_line is None:
                return None
            m = pred.match(self._current_line, self._offset)
            if m is None:
                return ""
            start, end = m.span()
            assert end >= start
            assert start >= self._offset
            self._offset = end
            return self._current_line[start:end]
        elif callable(pred):
            remaining = self.remaining_line
            if remaining is None:
                return None
            idx = 0
            while idx < len(remaining):
                if pred(remaining[idx]):
                    idx += 1
                    continue
                else:
                    break
            self._offset += idx
            return remaining[:idx]
        elif isinstance(pred, set):
            return self.take_while(lambda c: c in pred)
        else:
            raise TypeError("Unsupported predicate type: {self.pred}")

    def next_line(self) -> Optional[str]:
        if self._current_line is None:
            return None
        lines = self.lines
        if self._lineno < len(lines):
            self._current_line = lines[self._lineno]
            self._lineno += 1
        else:
            if self._current_line is not None:
                self._lineno += 1
            self._current_line = None
        self._offset = 0
        return self._current_line

    def take_word(self) -> Optional[str]:
        return self.take_while(WORD_PATTERN)

    def peek_word(self) -> Optional[str]:
        old_offset = self._offset
        word = self.take_word()
        self._offset = old_offset
        return word

    def skip_whitespace(self) -> str:
        return self.take_while(WHITESPACE_PATTERN)

    def skip_whitespace_lines(self) -> bool:
        while True:
            if self._current_line is None:
                return None
            self.skip_whitespace()
            if not self.remaining_line or self.remaining_line.startswith("#"):
                self.next_line()
            else:
                break

    def statement(self) -> Optional[Statement]:
        stmt = self._statement()
        if self.remaining_line:
            self.skip_whitespace()
            if self.remaining_line.startswith(";"):
                self._offset += 1
        return stmt

    def _statement(self) -> Optional[Statement]:
        self.skip_whitespace_lines()
        start = self.location
        first_word = self.peek_word()
        if first_word is None:
            return None
        if not first_word:
            raise ShellParseError(
                f"Expecting a statement (but not a valid word)", self.location
            )
        try:
            return self._stmt_dispatch[first_word](self)
        except KeyError:
            pass  # Not a keyword, treat as a regular identifier..
        name = self.take_word()
        self.take_while(WHITESPACE_PATTERN)
        if self.remaining_line.startswith("="):
            self._offset += 1
            self.take_while(WHITESPACE_PATTERN)
            value = self.expression(required=True)
            end = self.location
            return AssignmentStmt(Span(start, end), None, name, value)
        else:
            raise ShellParseError(
                f"Unexpected char `{self.remaining_line[:1]}` after {name!r}",
                self.location,
            )

    def assignment_stmt(self) -> AssignmentStmt:
        start = self.location
        kind = AssignmentKind(self.take_word())
        self.take_while(WHITESPACE_PATTERN)
        target = self.take_word()
        self.take_while(WHITESPACE_PATTERN)
        if self.remaining_line.startswith("="):
            self._offset += 1
            value = self.expression(required=True)
        elif kind == AssignmentKind.EXPORT:
            value = None
        else:
            raise ShellParseError(f"Expected an `=`", self.location)
        end = self.location
        return AssignmentStmt(Span(start, end), kind, target, value)

    def expression(
        self,
        *,
        ctx: ExpressionContext = ExpressionContext.VALUE,
        inside_quotes: bool = True,
        required: bool = False,
    ) -> Expression:
        assert ctx in {ExpressionContext.VALUE, ExpressionContext.COMMAND}
        self.skip_whitespace()
        start = self.location
        remaining = self.remaining_line
        if not remaining:
            if required:
                raise ShellParseError("Expected an expression", start)
            else:
                return None
        if remaining.startswith("$"):
            self._offset += 1
            remaining = self.remaining_line
            if remaining.startswith("("):
                text = self.parse_balanced_parens()
                return SubcommandExpr(Span(start, self.location), text)
            else:
                raise ShellParseError("Raw $VAR is not supported", self.location)
        elif remaining.startswith("[["):
            test = self.parse_balanced(opening="[[", closing="]]")
            return TestCommandExpr(
                span=Span(start, self.location), text=f"[[ {test} ]]"
            )
        elif ctx == ExpressionContext.COMMAND:
            # Interpret remaining as a command
            #
            # TODO: Skip over ';' inside string :(
            text = self.take_while(lambda c: c != ";")
            return TestCommandExpr(span=Span(start, self.location), text=text)
        elif m := SHELL_LITERAL_PATTERN.match(remaining):
            assert m.span()[0] == 0
            self._offset += m.span()[1]
            assert self.location.offset == self._offset
            return LiteralExpr(
                Span(start, self.location),
                self._current_line[start.offset : self._offset],
            )
        elif remaining[0] in ('"', "'"):
            style = QuoteStyle(remaining[0])
            start = self.location
            s = self.parse_string(style)
            end = self.location
            return QuotedExpression(Span(start, end), s, style)
        elif remaining.startswith(";"):
            return (
                None  # Consider end of expressions (because this terminates statement)
            )
        else:
            raise ShellParseError("Unable to parse expression", self.location)

    def parse_string(self, style: QuoteStyle) -> str:
        """Parse a string.

        This does not interpret escape codes. It passes them through as-is."""
        start = self.location
        remaining = self.remaining_line
        quote = str(style)
        assert remaining.startswith(quote)
        idx = 1
        while True:
            next_quote = remaining.find(quote, idx)
            if next_quote < 0:
                raise ShellParseError(
                    "Unable to find closing quote `{quote}` (NOTE: Multi-line strings are unsupporteed)",
                    start,
                )
            elif remaining[next_quote - 1] == "\\" and (
                next_quote < 2 or remaining[next_quote - 2] != "\\"
            ):
                # It's an escaped quote
                idx = next_quote + 1
            else:
                assert next_quote < len(remaining)
                self._offset += next_quote + 1
                # NOTE: We don't want to include starting or ending quote
                return remaining[1:next_quote]

    def parse_balanced_parens(self, **kwargs):
        kwargs["opening"] = "("
        kwargs["closing"] = ")"
        if "multiline" not in kwargs:
            kwargs["multiline"] = True  # True by default (default is False)
        return self.parse_balanced(**kwargs)

    def parse_balanced(
        self,
        *,
        opening: str,
        closing: str,
        strip_outer: bool = True,
        multiline: bool = False,
    ) -> str:
        assert len(opening) >= 1
        assert len(closing) >= 1
        remaining = self.remaining_line
        assert remaining.startswith(
            opening
        ), f"Expected start {opening!r}, but got {remaining[:len(start) + 1]!r}"
        current = self._current_line
        start_loc = self.location
        idx = self._offset + 1
        level = 1

        def try_advance():
            nonlocal idx, current
            if not multiline or (current := self.next_line()) is None:
                raise ShellParseError(
                    f"Expected a matching closing `{closing}`", start_loc
                )
            else:
                self.next_line()
                current = self._current_line
                idx = 0

        end_loc = None
        while True:
            next_opening = current.find(opening, idx)
            next_closing = current.find(closing, idx)
            if next_opening < 0:
                # no opening
                if next_closing < 0:
                    # no opening and no closing
                    try_advance()
                    continue
                else:
                    # no opening, but a closing
                    level -= 1
                    idx = next_closing + len(closing)
            elif next_closing < 0:
                # no closing, but an opening
                level += 1
                idx += next_opening + len(opening)
            else:
                # Both an opening and a closing. Which comes first?
                if next_opening < next_closing:
                    # opening first
                    idx = next_opening + len(opening)
                    level += 1
                    continue
                else:
                    # closing first
                    assert next_opening > next_closing
                    level -= 1
                    idx = next_closing + len(closing)
            if level == 0:
                self._offset = idx
                end_loc = self.location
                break
        if multiline and start_loc.line != end_loc.line:
            assert start_loc.line < end_loc.line
            first_line = self.lines[start_loc.line - 1][start_loc.offset :]
            lines = [first_line]
            line = start_loc.line + 1
            while line < end_loc.line:
                lines.append(self.lines[line - 1])
            assert self.lines[end_loc.line - 1] == self._current_line
            res.append(self._current_line[: self._offset])
            text = "\n".join(res)
        else:
            assert start_loc.line == end_loc.line
            assert start_loc.offset < end_loc.offset
            assert start_loc.line == self._lineno
            text = self._current_line[start_loc.offset : end_loc.offset]
        assert text.startswith(opening), repr(text)
        assert text.endswith(closing), repr(text)
        if strip_outer:
            text = text[len(opening) : -len(closing)]
        return text

    def conditional_stmt(self) -> ConditionalStmt:
        start = self.location
        start_word = self.take_word()
        if start_word != "if":
            raise ShellParseError("Expected an `if`", self.location)
        condition = self.expression(ctx=ExpressionContext.COMMAND)
        self.skip_whitespace()
        if not self.remaining_line.startswith(";"):
            raise ShellParseError("Expected a semicolon", self.location)
        else:
            self._offset += 1
        self.skip_whitespace()
        if (word := self.peek_word()) != "then":
            raise ShellParseError("Expected `then`, but got `{word!r}`", self.location)
        self.take_word()
        then = []
        while True:
            self.skip_whitespace_lines()
            if self._current_line is None:
                return None
            word = self.peek_word()
            if word in ("else", "elif"):
                raise ShellParseError(
                    "Unsupported conditional operation `{word}`", self.location
                )
            elif word == "fi":
                self.take_word()
                break
            else:
                then.append(self.statement())
        end = self.location
        return ConditionalStmt(Span(start, end), condition=condition, then=then)

    def function_declaration(self) -> FunctionDeclaration:
        start = self.location
        start_word = self.take_word()
        if start_word != "function":
            raise ShellParseError("Expected a `function`", self.location)
        self.skip_whitespace()
        name = self.take_word()
        if not name:
            raise ShellParseError("Expected a name for the function", self.location)
        self.skip_whitespace()
        open_parens = self.take_while(re.compile(r"\(\s*\)"))
        if not open_parens:
            raise ShellParseError(
                f"Expected opening parens () for function declaration {name!r}",
                self.location,
            )
        self.skip_whitespace()
        if self.remaining_line.startswith("{"):
            self._offset += 1
        else:
            raise ShellParseError("Expected opening brace")
        body = []
        while True:
            self.skip_whitespace_lines()
            if self.remaining_line.startswith("}"):
                self._offset += 1
                end = self.location
                break
            else:
                stmt = self.statement()
                body.append(stmt)

        # TODO: This doesn't care about overriding or scoping or anything
        #
        # Ah well
        self._defined_functions.add(name)
        if name in self._stmt_dispatch:
            raise ShellParseError(
                "Defining {name!r} conflicts with existing builtin/statement", start
            )
        else:
            self._stmt_dispatch[name] = ShellParser.function_invocation
        return FunctionDeclaration(
            span=Span(start, end),
            name=name,
            body=body,
        )

    def function_invocation(self) -> FunctionInvocation:
        start = self.location
        name = self.take_word()
        if name in self.extra_builtins:
            kind = FunctionInvocationKind.EXTRA_BUILTIN
        elif name in STANDARD_BUILTINS:
            kind = FunctionInvocationKind.STANDARD_BUILTIN
        elif name in self._defined_functions:
            kind = FunctionInvocationKind.USER_DEFINED_FUNCTION
        else:
            raise AssertionError(f"Unknown type of invocation for {name!r} @ {start}")
        end = self.location
        args = []
        while self.remaining_line.strip():
            expr = self.expression()
            if expr is None:
                break
            args.append(expr)
            end = self.location
        return FunctionInvocation(
            span=Span(start, end), name=name, args=args, kind=kind
        )


_BUILTIN_STMT_DISPATCH = {
    "export": ShellParser.assignment_stmt,
    "local": ShellParser.assignment_stmt,
    "alias": ShellParser.assignment_stmt,  # treat alias as a special case of assignment
    "if": ShellParser.conditional_stmt,
    "function": ShellParser.function_declaration,
}
