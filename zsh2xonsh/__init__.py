"""Translates a limited subset of zsh to xonsh

The main feature of this module (as compared to other compatibility layers)
is that it throws a `NotImplementedError` when it doesn't understand something.

That is, if anything outside the limited subset is used, then an unambiguous error is thrown.

It is written in traditional python, with 'click' as its only dependency.

Supported shell subset:
1. export FOO=BAR
2. Basic command substutions "$()"
3. local foo=<value>
4. if [[ condition ]]; then

Others may be added in the future. This is sufficent to handle my "environment files".

The supported shell dialect is zsh (which is why its called zsh2xonsh).

Generated files depend on an exteremly lightweight runtime (present in the `runtime` file).

It is also pure-python.
"""

