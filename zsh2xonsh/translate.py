"""Utilites for translation"""
from __future__ import annotations
import ast as pyast
import re

from dataclasses import dataclass, field

@dataclass
class Settings:
    """Be strict about preserving the types of all environment variables (not just PATH variables)"""
    strict_env_types = False
    """The set of other path like variables that do not end with `PATH`"""
    other_path_like_vars: set[str] = field(default_factory={'BASH_COMPLETIONS',}.copy)

    def is_path_like_var(self, name: str) -> bool:
        """Detect if the variable should be treated like a $PATH EnvList
        See xonsh documentation on environment variables: https://xon.sh/envvars.html

        This is automatically true for any variable that ends with 'PATH'.
        See here: https://xon.sh/envvars.html#w-path
        """
        return name.endswith("PATH") or name in self.other_path_like_vars

    @staticmethod
    def default() -> Settings:
        return Settings()

assert Settings.default().is_path_like_var("PATH")
assert not Settings.default().is_path_like_var("FOO")
assert Settings.default().is_path_like_var("BASH_COMPLETIONS")

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
