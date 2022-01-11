import sys

import click

from .parser import ShellParser
from . import translate_to_xonsh
@click.command()
@click.option('--validate', help="Only validate the inputs, do not output them")
@click.option(
    'extra_builtins', '--builtin', '-b',
    help="An extra builtin funciton, assumed to be provided by the environment", 
    multiple=True
)
@click.option(
    'cmd', '--cmd', '-c',
    help="Translate a single input command"
)
@click.option(
    'assume_runtime', '--assume-runtime/--no-assume-runtime', '-r', is_flag=True,
    help="Assume the runtime is already present (instead of assuming it's already present)"
)
@click.option(
    'assume_context', '--assume-context', '-c', is_flag=True,
)
@click.argument('input_file', required=False)
def zsh2xonsh(input_file: str, extra_builtins, cmd=None, validate=False, assume_runtime=False, assume_context=False):
    """Translates zsh to xonsh scripts"""
    if cmd is not None:
        text = cmd
    elif input_file is not None:
        with open(input_file, 'rt') as f:
            text = f.read()
    else:
        raise click.ClickException("Must specifiy either `--cmd` or an input file")
    try:
        output = translate_to_xonsh(text, extra_builtins=extra_builtins)
    except KeyboardInterrupt as e:
        import traceback
        print("Interrupted while translating", file=sys.stderr)
        print("Did the parser stall?", file=sys.stderr)
        print(traceback.format_exc(), file=sys.stderr)
        raise
    if validate:
        return
    indent = ""
    if not assume_runtime:
        print('from zsh2xonsh import runtime')
    if not assume_context:
        print("with runtime.init_context() as ctx:")
        indent = ' ' * 4
    for line in output.splitlines():
        print(indent + line)

if __name__ == "__main__":
    zsh2xonsh()
