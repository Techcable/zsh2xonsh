"""The zsh2xonsh `runtime`. This is invoked by generated code...."""
from typing import Optional

import os.path
import collections.abc
from subprocess import run, CalledProcessError, PIPE, DEVNULL

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

def zsh_test(test: str) -> bool:
    try:
        zsh(f"[[ {test} ]]")
    except ZshSyntaxError:
        raise
    except ZshError as e:
        return False
    else:
        return True

def expand_literal(s: str) -> str:
    # NOTE: It's up to the compiler to avoid unessicary calls to this function
    # In particular, it is only nessicary when the literal contains a `~`
    return os.path.expanduser(s)

def zsh_expand_quote(quoted: str) -> str:
    # NOTE: It's up to the compiler/translator to avoid unessicary calls to `zsh_expand_quote`
    return zsh(f'echo "{quoted}"')


def assign_path_var(target, new_path, var="PATH"):
    """
    This function is nessicary because xonsh's $PATH is a list, while in the shell it's a string

    xonsh's approach is obviously better, but it makes assigning things more difficult on our part ;)
    """
    assert isinstance(target, collections.abc.MutableSequence)
    old_path = zsh_expand_quote(f"${var}")
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





def _check_syntax(cmd):
    try:
        run(['zsh', '--no-exec', '-c', cmd], check = True, stderr=PIPE, stdout=DEVNULL, encoding='utf8')
    except CalledProcessError as e:
        # Only reason this can fail is if 
        reason = e.stderr.strip()
        raise ZshSyntaxError("Invalid `zsh` command {cmd!r}: {reason}") from None

def zsh(cmd: str, *, inherit_env=True, check=False, trim_trailing_newline=True) -> str:
    _check_syntax(cmd) # Verify its valid syntax
    env = dict(os.environ) if inherit_env else {}
    env.update(FAKE_ENV)
    try:
        # NOTE: Inherit stderr. This matches behavior of zsh's $(...)
        s = run(['zsh', '-c', cmd], check=True, stdout=PIPE, encoding='utf-8').stdout
        if trim_trailing_newline and s[-1] == '\n':
            s = s[:-1]
        return s
    except CalledProcessError as cause:
        if check:
            raise ZshError("Failed to execute {cmd!r}", returncode=cause.returncode) from cause
        else:
            return None


__all__ = ['zsh', 'zsh_test', 'zsh_expand_quote']
