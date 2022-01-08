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
    'include_runtime', '--runtime/--no-runtime', '-r', is_flag=True,
    help="Include the runtime as an import (instead of assuming it's already imported)"
)
@click.argument('input_file', required=False)
def zsh2xonsh(input_file: str, extra_builtins, cmd=None, validate=False, include_runtime=True):
    """Translates zsh to xonsh scripts"""
    if cmd is not None:
        text = cmd
    elif input_file is not None:
        with open(input_file, 'rt') as f:
            text = f.read()
    else:
        raise click.ClickException("Must specifiy either `--cmd` or an input file")
    output = translate_to_xonsh(text, extra_builtins=extra_builtins)
    if validate:
        return
    if include_runtime:
        print('from zsh2xonsh import runtime')
    for line in output.splitlines():
        print(line)

if __name__ == "__main__":
    zsh2xonsh()
