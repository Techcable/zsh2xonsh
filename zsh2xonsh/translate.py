"""Utilites for translation"""
import ast as pyast
import re

def python_literal(s: str) -> str:
    return pyast.unquote(pyast.Constant(s))

SAFE_QUOTED_STRING = re.compile(r"[\w\-\/]*")
def is_simple_quoted(s: str) -> bool:
    """Determines if the quoted string can be output directly without delegating to zsh for expansion

    This is the case for things like "foo" and "bar".

    It is *not* the case for anything involving globbing or variables.

    These require special logic best done in zsh"""
    return SAFE_QUOTED_STRING.fullmatch(s) is not None

# Things that we allow outside a quote without delegating to `zsh`
# NOTE: We do not include '*' or any whitespace, because I dont' wanna deal with glob expansion
#
# We do include beginning `~` because python has a fast way to deal with that
#
# TODO: Are there any literals we recognize that are not 'safe'?
SAFE_LITERAL_PATTERN = re.compile(r"[\w\~\/\\\.\-]+")
def is_simple_literal(s, *, smart=False):
    """Determines if the specified literal can be output directly without delegating to zsh for expansion

    This is the case for things like foo/bar and 12.

    It is *not* the case for anything involving globbing or variables.

    These require special logic best done in zsh.

    If the mode is `smart`, then this allows a leading `~` at the beginning of the string.
    Python can quickly (and sanely) emulate this using `os.path.expanduser`.
    This avoids the overhead of an extenral process call in those (common cases).
    """
    if not smart and s.startswith("~"):
        return False # Requires os.path.expanduser` expansion, which they are too dumb to do
    else:
        return SAFE_LITERAL_PATTERN.fullmatch(s) is not None

INTEGER_PATTERN = re.compile(r"[\d](\d|_\d)*")
def is_valid_integer(s: str) -> bool:
    return INTEGER_PATTERN.fullmatch(s) is not None

# Variables that are traditonally strings,
# that xonsh turns into lists. The primary example is $PATH
PATH_LIKE_VARS = frozenset(["PATH",])

def can_safely_be_split(text):
    """Detrmines if something can safely be split along spaces.

    Specifically how would we convert `alias foo="bar baz"` into ?

    The simple solution is to always split along spaces.

    This is incorrect for things like `alias foo='/usr/bin/egre*'`.
    zsh has to do glob expansion at runtime, which xonsh will (sanely) refuse to do.

    To workaround this edge-case, we could:
    1. Unconditionally delegate aliases entirely into zsh
       - This would be slow, especially if your alias is called in some sort of a loop
    2. Recognize that bar and baz are "simple" literals,
       that can be split entirely along their 

    We take the second option, calling out to `is_simple_literal` for each whitespace.
    Hopefully this should avoid .
    """
    # TODO: What if we have nested quotes `alias='foo "bar"`.
    # This is (technically) safe to expand without calling out to zsh
    return all(is_simple_literal(part) for part in text.split(' '))
