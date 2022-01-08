"""Utilites for translation"""
import ast as pyast
import re

def python_literal(s: str) -> str:
    return pyast.unquote(pyast.Constant(s))

SAFE_QUOTED_STRING = re.compile(r"[\w\-\/]*")
def is_simple_quoted(s: str) -> bool:
    return SAFE_QUOTED_STRING.fullmatch(s) is not None

INTEGER_PATTERN = re.compile(r"[\d](\d|_\d)*")
def is_valid_integer(s: str) -> bool:
    return INTEGER_PATTERN.fullmatch(s) is not None

# Variables that are traditonally strings,
# that xonsh turns into lists. The primary example is $PATH
PATH_LIKE_VARS = frozenset(["PATH",])