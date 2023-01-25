"""An interface from Python runtime -> xonsh API

Used to avoid *directly* depending on xonsh's intenral API.

It also implements somewhat reasonable fallback code if
xonsh is not detected (useful for testing)
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from enum import Enum
from typing import Optional

if "xonsh" in sys.modules:
    import xonsh
    import xonsh.environ
    import xonsh.tools
else:
    if "pytest" not in sys.modules:
        print(
            "WARNING: Could not detect `xonsh` support (enabling fallback)",
            file=sys.stderr,
        )
    xonsh = None


class VarKind(Enum):
    STRING = str
    BOOLEAN = bool
    INTEGER = int
    PY_NONE = type(None)
    PATH = "EnvPath"

    def parse(self, text: str) -> TypedVar:
        if self == VarKind.STRING:
            value = text
        elif self == VarKind.BOOLEAN:
            if text in ("True", "true", "1"):
                value = True
            elif text in ("False", "false", "0"):
                value = False
            else:
                raise ValueError(f"Unexpected value for bool var: {text!r}")
        elif self == VarKind.INTEGER:
            value = int(text)
        elif self == VarKind.PY_NONE:
            if text == "":
                value = None
            else:
                raise ValueError(f"Expected empty string for `None` var: {text!r}")
        elif self == VarKind.PATH:
            raise NotImplementedError  # Paths are a special case
        else:
            raise AssertionError("Unexpected VarKind: " + str(self))
        return TypedVar(value, kind=self)

    def __str__(self):
        if isinstance(self.value, type):
            return self.value.__name__
        else:
            return str(self.value)

    @staticmethod
    def detect(value: object) -> Optional[VarKind]:
        try:
            return VarKind(type(value))
        except ValueError:
            try:
                return VarKind(type(value).__name__)
            except ValueError:
                return None


@dataclass
class TypedVar:
    value: object
    kind: Optional[VarKind]

    def __str__(self):
        return str(self.value)

    def __repr__(self):
        return repr(self.value)


def assign_env_var(target: str, value: str):
    """Assign the value of the specified environment variable to the specified (string) value.

    This may not behave as expected
    in the presense of typed environment variables.

    In particular, it will:
    1. Willfully discard existing type information.
    2. Make no effort to treat path variables specially ($PATH is special in xonsh)

    Example
    $FOO = 1
    thisModule.assign_env_var('FOO', '1')
    $FOO # Is now a string typed variable :(
    """
    if xonsh is not None:
        # NOTE: This preserves the type of the passed in value
        xonsh.environ.XSH.env[target] = value
    else:
        os.environ[target] = str(value) if value is not None else ""


def get_typed_env_var(target: str, *, allow_unknown_type=False) -> TypedVar:
    """Gets the typed value of the specified environment variable.

    Raises KeyError if the specified environment variable doesn't exist.

    Correctly falls back to os.getenv if xonsh is not present"""
    if xonsh is None:
        value = os.getenv(target)
        if value is not None:
            return TypedVar(value, kind=VarKind.STRING)
        else:
            raise KeyError(f"Undefined environment variable: {target}")
    # From now on, we should have xonsh present
    assert xonsh is not None, "Expected xonsh to be present"
    # NOTE: This properly respects type and it also throws KeyError
    #
    # Really we're just patching support
    value = xonsh.environ.XSH.env[target]
    detected_kind = VarKind.detect(value)
    if detected_kind is None and not allow_unknown_type:
        raise TypeError(f"Unknown type for var {target!r}: {type(value)!r}")
    return TypedVar(value, kind=detected_kind)


def get_correct_env() -> dict:
    """Get the correct values of the environment variables

    Works around issue #2"""
    if xonsh is not None:
        # WARNING: There are some variables in ${...} that are not in ${...}.detype()
        #
        # See xonsh/xonsh#4636
        return xonsh.environ.XSH.env.detype()
    else:
        return os.environ()
