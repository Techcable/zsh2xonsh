"""An interface from Python runtime -> xonsh API

Used to avoid *directly* depending on xonsh's intenral API
"""
import sys
if 'xonsh' not in sys.modules:
    raise RuntimeError("xonsh not already loaded")

import xonsh
import xonsh.environ


def get_correct_env() -> dict:
    """Get the correct values of the environment variables

    Works around issue #2"""
    # WARNING: There are some variables in ${...} that are not in ${...}.detype()
    #
    # See xonsh/xonsh#4636
    return xonsh.environ.XSH.env.detype()


