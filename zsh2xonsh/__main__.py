import click

from .parser import ShellParser

@click.command()
@click.option('--validate', help="Only validate the inputs, do not output them")
@click.option(
    'extra_functions', '--builtin', '-b',
    help="An extra builtin funciton, assumed to be provided by the environment", 
    multiple=True
)
@click.option(
    'cmd', '--cmd', '-c',
    help="Translate a single input command"
)
@click.argument('input_file', required=False)
def zsh2xonsh(input_file: str, extra_functions, cmd=None, validate=False):
    """Translates zsh to xonsh scripts"""
    if cmd is not None:
        lines = cmd.splitlines()
    elif input_file is not None:
        with open(input_file, 'rt') as f:
            lines = f.readlines()
    else:
        raise click.ClickException("Must specifiy either `--cmd` or an input file")
    parser =ShellParser(lines, extra_functions=set(extra_functions))
    stmts = []
    while (stmt := parser.statement()) is not None:
        stmts.append(stmt)
    if validate:
        return
    for stmt in stmts:
        print(stmt.translate().rstrip('\n'))

if __name__ == "__main__":
    zsh2xonsh()
