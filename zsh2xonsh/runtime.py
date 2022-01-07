"""The zsh2xonsh `runtime`. This is invoked by generated code...."""

import os.path
from subprocess import run, CalledProcessError, PIPE, DEVNULL

class ZshError(RuntimeError):
    returncode: Optional[int]
    def __init__(self, *args, *, returncode: Optional[int] = None)
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

def _check_syntax(cmd):
    try:
        run(['zsh', '--no-exec', '-c', cmd], check = True, stderr=PIPE, stdout=DEVNULL, encoding='utf8')
    except CalledProcessError as e:
        # Only reason this can fail is if 
        reason = e.stderr.strip()
        raise ZshSyntaxError("Invalid `zsh` command {cmd!r}: {reason}") from None

def zsh(cmd: str, *, inherit_env=True, check=False) -> str:
    _check_syntax(cmd) # Verify its valid syntax
    env = dict(os.environ) if inherit_env else {}
    env.update(FAKE_ENV)
    try:
        # NOTE: Inherit stderr. This matches behavior of zsh's $(...)
        return run(['zsh', '-c', cmd], check=True, stdout=PIPE)
    except CalledProcessError as cause:
        if check:
            raise ZshError("Failed to execute {cmd!r}", returncode=cause.returncode) from cause
        else:
            return None


__all__ = ['zsh', 'zsh_test', 'zsh_expand_quote']