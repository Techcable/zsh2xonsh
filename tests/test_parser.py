from zsh2xonsh.parser import ShellParser

def test_parse_balanced_parens():
    parser = ShellParser(['''(a b (c d e)) foo'''])
    assert parser.parse_balanced_parens() == 'a b (c d e)'
    parser = ShellParser(['$(import sys; print(".".join(map(str, sys.version_info[:2])))) foo'])
    assert parser.take_while({'$',}) == '$'
    assert parser.parse_balanced_parens() == 'import sys; print(".".join(map(str, sys.version_info[:2])))'
