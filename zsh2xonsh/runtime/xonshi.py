"""An interface from Python runtime -> xonsh API

Used to avoid *directly* depending on xonsh's intenral API.

It also implements somewhat reasonable fallback code if
xonsh is not detected (useful for testing)
"""
import sys
import os

if 'xonsh' in sys.modules:
    import xonsh
    import xonsh.environ
elif 'pytest' not in sys.modules:
    print("WARNING: Could not detect `xonsh` support (enabling fallback)", file=sys.stderr)

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

