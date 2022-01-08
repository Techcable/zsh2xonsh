"""Translates a limited subset of zsh to xonsh

The main feature of this module (as compared to other compatibility layers)
is that it throws a `NotImplementedError` when it doesn't understand something.

That is, if anything outside the limited subset is used, then an unambiguous error is thrown.

It is written in traditional python, with 'click' as its only dependency.

Supported shell subset:
1. export FOO=BAR
2. Basic command substutions "$()"
3. local foo=<value>
4. if [[ condition ]]; then

Others may be added in the future. This is sufficent to handle my "environment files".

The supported shell dialect is zsh (which is why its called zsh2xonsh).

Generated files depend on an exteremly lightweight runtime (present in the `runtime` file).

It is also pure-python.
"""

def translate_to_xonsh(zsh: str, *, extra_builtins: set[str] = frozenset()) -> str:
    """Translate the specified zsh code to xonsh

    If a parse error occurs (or an unsuppored feature is encountered),
    throws a zsh2xonsh.parser.TranslationError

    Accepts `extra_builtins` as the set of extra builtin functions
    (assumed to be provided to the code).
    """
    from .parser import ShellParser
    parser = ShellParser(zsh.splitlines(), extra_builtins=frozenset(extra_builtins))
    stmts = []
    while (stmt := parser.statement()) is not None:
        stmts.append(stmt)
    return '\n'.join([stmt.translate() for stmt in stmts])

def translate_to_xonsh_and_eval(zsh: str, *, extra_builtins: dict[str, object] = None):
    """Translate the specified zsh code to xonsh,
    then translate it.

    This is essentially a nice wrapper around the xonsh builtin `evalx`,
    running `evalx(translate_to_xonsh(zsh))`

    The extra_builtins allows the zsh code acess to an extra set of builtin functions.
    """
    if extra_builtins is None:
        extra_builtins = {}
    assert "runtime" not in extra_builtins, "runtime is already provided"
    from . import runtime
    local = {'runtime': runtime, **extra_builtins}
    try:
        from xonsh.built_ins import builtins
        evlax= builtins.evalx
    except ImportError:
        raise RuntimeError("Unable to import xonsh builtins. Do you have it installed?")
    translated = translate_to_xonsh(zsh, extra_builtins=set(extra_builtins.keys()))
    execx(translated, mode='exec', locs=local)
