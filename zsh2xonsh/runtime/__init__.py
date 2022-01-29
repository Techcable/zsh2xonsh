"""The zsh2xonsh `runtime`. This is invoked by generated code...."""
from __future__ import annotations

from typing import Optional, Callable

import os.path
import collections.abc
from contextlib import contextmanager
from subprocess import run, CalledProcessError, PIPE, DEVNULL


from . import xonshi


class ZshError(RuntimeError):
    returncode: Optional[int]
    # NOTE: Can't use kw-only args for 3.8 compat :(
    def __init__(self, *args, returncode: Optional[int] = None):
        super().__init__(*args)
        self.returncode = returncode

class ZshSyntaxError(ZshError):
    pass


FAKE_ENV = {
    "SHELL": "/bin/zsh"
}

class ZshContext:
    __slots__ = "_locals", "parent", "_positional_vars"
    parent: Optional[ZshContext]
    _locals: dict[str, object] # A mapping from local variable names to values
    _positional_vars: list[str] # Note: These are seperate from locals because zsh handles $0 $1 $2 specially
    def __init__(self, *, parent: Optional[ZshContext] = None):
        self._locals = {}
        self.parent = parent
        self._positional_vars = []

    @contextmanager
    def begin_function(self, name: str, args: object) -> ZshContext:
        assert isinstance(name, str)
        ctx = ZshContext(parent=self)
        assert not ctx._positional_vars
        ctx._positional_vars.append(name) # $0
        ctx._positional_vars.extend(args)
        yield ctx
        ctx._locals.clear()

    def assign_local(self, name: str, value: object):
        assert isinstance(name, str)
        self._locals[name] = str(value) # Everything must be normalized to string for zsh :(
        return value

    def zsh_test(self, test: str) -> bool:
        try:
            self.zsh(f"[[ {test} ]]", check=True)
        except ZshSyntaxError:
            raise
        except ZshError as e:
            return False
        else:
            return True

    def zsh_impl_complex_alias(self, alias: str) -> Callable:
        """Handle a "complex" alias like `alias foo='echo .*'`

        The glob is expanded each time the alias is executed, so it gives different results
        in different directoreis.

        From the zsh docs:
        > Every eligible word in the shell input is checked to see if there is an alias defined for it.
        > If so, it is replaced by the text of the alias if it is in command position 

        Also

        > Alias expansion is done on the shell input before any other expansion except history expansion

        This delegates to zsh for the hard part of actual doing the glob expansion.

        Returns a callable function that actually implements the alias"""
        def impl_callaback(args):
            # So what about those extra args provided to xonsh alias callbacks?
            # Do they do something special to input/output?
            cmd = alias # let zsh do the expansion
            if args:
                cmd += " "
                cmd += ' '.join(quote_into_shell_string(arg) for arg in args)
            return self.zsh(cmd)
        return impl_callaback


    def expand_literal(self, s: str) -> str:
        # NOTE: It's up to the compiler to avoid unessicary calls to this function
        # In particular, it is only nessicary when the literal contains a `~`
        return os.path.expanduser(s)

    def zsh_expand_quote(self, quoted: str) -> str:
        # NOTE: It's up to the compiler/translator to avoid unessicary calls to `zsh_expand_quote`
        return self.zsh(f'echo "{quoted}"')

    def assign_path_var(self, target, new_path, var="PATH"):
        """
        This function is nessicary because xonsh's $PATH is a list, while in the shell it's a string

        xonsh's approach is obviously better, but it makes assigning things more difficult on our part ;)
        """
        assert isinstance(target, collections.abc.MutableSequence)
        old_path = self.zsh_expand_quote(f"${var}")
        # We don't support removal. Only addition at the beginning (prefix) or end (suffix)
        #
        # This is a poor man's diff
        if old_path not in new_path:
            raise ZshError(f"Changes between old and new ${var} are too complicated: {old_path!r} -> {new_path!r}")
        offset = new_path.find(old_path)
        prefix = new_path[:offset]
        suffix = new_path[offset+len(old_path):]
        if prefix:
            preifxed_parts = prefix.split(':')
            if preifxed_parts[-1] == "":
                preifxed_parts.pop()
        else:
            preifxed_parts = []
        for part in reversed(preifxed_parts):
            target.insert(0, part)
        if suffix:
            suffixed_parts = suffix.split(':')
            if suffixed_parts[0] == "":
                suffixed_parts.pop(0)
        else:
            suffixed_parts = []
        for part in suffixed_parts:
            target.append(part)


    def _check_syntax(self, cmd):
        try:
            run(['zsh', '--no-exec', '-c', cmd], check = True, stderr=PIPE, stdout=DEVNULL, encoding='utf8')
        except CalledProcessError as e:
            # Only reason this can fail is if syntax is invalid
            reason = e.stderr.strip()
            raise ZshSyntaxError("Invalid `zsh` command {cmd!r}: {reason}") from None

    def _resolved_locals(self) -> dict:
        if self.parent is not None:
            resolved = self.parent._resolved_locals()
        else:
            resolved = {}
        # Inner locals override outer locals
        resolved.update(self._locals)
        return resolved

    def zsh(self, cmd: str, *, inherit_env=True, check=False, pipe=True, trim_trailing_newline=True) -> str:
        self._check_syntax(cmd) # Verify its valid syntax
        # NOTE: Use xonsh's environment
        #
        # This avoids issue with `os.environ` caching
        env = xonshi.get_correct_env() if inherit_env else {}
        env.update(FAKE_ENV)
        # Locals override globals
        env.update(self._resolved_locals())
        try:
            # NOTE: Inherit stderr. This matches behavior of zsh's $(...)
            #
            # Per the zsh docs, $0 $1 $2 are specified after the literal `-c`
            # You can test this with `zsh -c 'echo $1' foo bar` -> bar
            s = run(['zsh', '-c', cmd, *self._positional_vars], env=env, check=True, stdout=PIPE if pipe else None, encoding='utf-8').stdout
            if trim_trailing_newline and s and s[-1] == '\n':
                s = s[:-1]
            return s
        except CalledProcessError as cause:
            if check:
                raise ZshError("Failed to execute {cmd!r}", returncode=cause.returncode) from cause
            else:
                # TODO: Is it a good idea to swallow errors like this?
                return None




@contextmanager
def init_context() -> ZshContext:
    yield ZshContext()



# TODO: This could use some work
# I do not understand the intracacies of single-quoted strings
#
# Could accidentally end up with a bizzare glob here ;)
_NAUGHTY_CHARS = {'\\', '\''}
def quote_into_shell_string(s):
    res = ['\'']
    for c in s:
        if c in _NAUGHTY_CHARS:
            res.extend(("\\", c))
        else:
            res.append(c)
    res.append('\'')
    return ''.join(res)





__all__ = ['init', 'ZshContext', 'ZshError']
