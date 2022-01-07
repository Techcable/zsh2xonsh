"""A basic recursive decent parser for `zsh` code.

Please shoot me"""

import re

from click import ClickException

from .ast import *

class TranslationError(ClickException):
    location: Optional[Location]
    msg: str

    def __init__(self, msg: str, location: Optional[Location]):
        super().__init__(msg)
        assert msg not is None and isinstance(msg, str), "Unexpected msg: {msg!r}"
        assert location is None or isinstance(location, Location), "Unexpected location: {location!r} w/ msg {msg!r}"

    @property
    def kind(self) -> str:
        return "Translation error"

    def __str__(self):
        msg = f"{self.kind}: {super().__str__()}"
        if self.location is not None:
            msg += " @ {self.location}"
        return msg


class ShellParseError(TranslationError):
    @property
    def kind(self) -> str:
        return "Error parsing zsh subset (NYI?)"

_WORD_PATTERN = re.compile(r"\w+")
_WHITESPACE_PATTERN = re.compile(r"\s*")
# Things that we allow outside a quote
# NOTE: We do not include '*' or any whitespace, because I dont' wanna deal with glob expansion
_SHELL_LITERAL_PATTERN = re.compile(r"[\w\~\/\\\.\-]+")
class ShellParser:
    """A recursive decent parser for a limited subset of `zsh`.

    Please shoot me :)"""
    __slots__ = "_current_line", "lines", "_lineno", "_offset", "dialect", "extra_functions", "_stmt_dispatch"
    lines: list[str]
    _current_line: Optional[str] # None if EOF
    extra_functions: set[str]
    _lineno: int = 1
    _offset: int = 0
    dialect: str
    def __init__(self, lines: list[str], *, extra_functions: set[str]=frozenset(), dialect="zsh"):
        global _BUILTIN_STMT_DISPATCH
        if dialect != "zsh":
            raise NotImplementedError(f"Unsupported dialect: {dialect}")
        assert isinstance(extra_functions, set)
        self._current_line = lines[0] if lines else None
        self.lines = lines
        self.dialect = dialect
        self.extra_functions = extra_functions
        dispatch = _BUILTIN_STMT_DISPATCH.copy()
        if extra_functions:
            for extra in extra_functions:
                assert _WORD_PATTERN.fullmatch(extra) is not None, "Invalid extra function: {extra!r}"
                assert extra not in dispatch, "The \"extra\" function {extra!r} conflicts with a builtin" 
                dispatch[extra] = ShellParser.extra_function
        self._stmt_dispatch = dispatch


    @property
    def location(self) -> Location:
        return Location(line=self._lineno, offset=self._offset)

    @property
    def remaining_line(self) -> Optional[str]:
        try:
            return self._current_line[self._offset:]
        except TypeError:
            assert self._current_line is None, "Unexepected type: {self._current_line}"
            return None

    def take_while(self, pred: Union[set[str], Callable[[str], bool], re.Pattern], *, multiline=False) -> str:
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
            self.offset = end
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
            self._current_line = None
        self._offset = 0
        return self._current_line

    def take_word(self) -> Optional[str]:
        global _WORD_PATTERN
        return self.take_while(_WORD_PATTERN)

    def peek_word(self) -> Optional[str]:
        old_offset = self._offset
        word = self.take_word()
        self._offset = old_offset
        return word


    def skip_whitspace(self) -> str:
        global _WHITESPACE_PATTERN
        return self.take_While(_WHITESPACE_PATTERN)

    def skip_whitespace_lines(self) -> bool:
        while True:
            if self._current_line is None:
                return None
            self.skip_whitespace()
            if not self.remaining_line or self.remaining_line.startswith('#'):
                self.next_line()
            else:
                break

    def statement(self) -> Optional[Statement]:
        self.skip_whitespace_lines()
        global _WORD_DISPATCH
        first_word = self.peek_word()
        try:
            return self._stmt_dispatch[first_word](self)
        except KeyError:
            raise ShellParseError("Unknown statement: {first_word!r}", self.location)

    def assignment_stmt(self) -> AssignmentStmt:
        start = self.location
        kind = AssignmentKind(self.take_word())
        self.take_while(WHITESPACE_PATTERN)
        if not self.remaining_line.startswith("="):
            raise ShellParseError("Unknown statement: {first_word!r}", self.location)
        self._offset += 1
        value = self.expression(required=True)
        end = self.location
        return AssignmentStatement(Span(start, end), kind, value)

    def expression(self, *, inside_quotes: bool=True, required: bool = False) -> Expression:
        self.skip_whitespace()
        start = self.location
        remaining = self.remaining_line
        if not remaining:
            if required:
                raise ShellParseError("Expected an expression", start)
        if remaining.starts_with("$"):
            self._offset += 1
            if not remaining.startswith("("):
                raise ShellParseException("Expected an open paren for $(...) substitution", self.location)
            text = self.parse_balanced_parens(strip_parens)
            return SubcommandExpr(
                Span(start, self.location),
                text
            )
        elif (m := _SHELL_LITERAL_PATTERN.match(remaining)):
            assert m.span[0] == 0
            self._offset += m.span[1]
            assert self.location.offset == self._offset
            return LiteralExpr(Span(start, self.location), self._current_line[start.offset:self._offset])
        elif remaining.startswith("[["):
            test = self.parse_balanced('[[', ']]')
            if end < 0:
                raise ShellParseError("Unable to find closing `]]`", start)
            self._offset += end
            return
        elif remaining.startswith('"'):
            start = self.location
            s = self.parse_string()
            end = self.location
            return QuotedExpression(Span(start, end), s)
        else:
            raise ShellParseError("Unable to parse expression", self.location)

    def parse_string(self) -> str:
        """Parse a string.

        This does not interpret escape codes. It passes them through as-is."""
        start = self.location
        remaining = self.remaining_line
        assert remaining.startswith('"')
        idx = 1
        while True:
            next_quote = remaining.find('"', idx)
            if next_quote < 0:
                raise ShellParseError("Unable to find closing quote `\"` (NOTE: Multi-line strings are unsupporteed)", start)
            elif remaining[next_quote - 1] == '\\' && (next_quote < 2 or remaining[next_quote - 2] != '\\'):
                # It's an escaped quote
                idx = next_quote + 1
            else:
                assert next_quote < len(remaining)
                self._offset += next_quote
                return remaining[:next_quote]

    def parse_balanced_parens(self, **kwargs):
        kwargs['opening'] = '('
        kwargs['closing'] = ')'
        if 'multiline' not in kwargs:
            kwargs['multiline'] = True # True by default (default is False)
        return self.parse_balanced(**kwargs)


    def parse_balanced(self, *, opening: str, closing: str, strip_outer: bool = True, multiline: bool = False) -> str:
        assert len(opening) >= 1
        assert len(closing) >= 1
        remaining = self.remaining_line
        assert remaining.startswith(start), f"Expected start {opening!r}, but got {remaining[:len(start) + 1]!r}"
        current = self._current_line
        start_loc = self.location
        idx = self._offset
        level = 1
        def try_advance():
            nonlocal idx, current 
            if not multiline or (current := self.next_line()) is None:
                raise ShellParseError(f"Expected a matching closing `{closing}`", start_loc)
            else:
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
            elif next_closing < 0:
                # no closing, but an opening
                level += 1
            else:
                # Both an opening and a closing. Which comes first?
                if next_opening < next_closing:
                    # opening, then closing. They effectively cancel
                    idx = next_closing + 1
                    continue
                else:
                    assert next_opening > next_closing
                    level -= 1
            if level == 0:
                # We found our closing
                idx = next_closing + 1
                self._offset = idx
                end_loc = self.location
                break
        if multiline and start_loc.line != end_loc.line:
            assert start_loc.line < end_loc.line
            first_line = self.lines[start_loc.line - 1][start_loc.offset:]
            lines = [first_line]
            line = start_loc.line + 1
            while line < end_loc.line:
                lines.append(self.lines[line - 1])
            assert self.lines[end_loc.line - 1] == self._current_line
            res.append(self._current_line[:self._offset])
            text = '\n'.join(res)
        else:
            assert start_loc.line == end_loc.line
            assert start_loc.offset < end_loc.offset
            assert start_loc.line == self._lineno
            text = self._current_line[start_loc._offset:self.end_loc.offset]
        assert text.startswith(opening), repr(text)
        assert text.endswith(opening), repr(text)
        if strip_outer:
            text = text[len(opening):-len(closing)]
        return text

    def conditional_stmt(self) -> ConditionalStmt:
        start = self.location 
        start_word = self.take_word()
        if start_word != "if":
            raise ShellParseError()
        condition = self.expression();
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
                raise ShellParseError("Unsupported conditional operation `{word}`", self.location)
            elif word == "fi":
                self.take_word()
                break
            else:
                body.append(self.statement())
        end = self.location
        raise ConditionalStmt(Span(start, end), condition=condition, then=then)

    def function_invocation(self) -> Self
        raise NotImplementedError

_BUILTIN_STMT_DISPATCH = {
    "export": ShellParser.assignment_stmt,
    "local": ShellParser.assignment_stmt,
    "if": ShellParser.conditinal_stmt,
}
