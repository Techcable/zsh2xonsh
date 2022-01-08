# This is the environment configuration for my Arch Linux 2017 laptop
#
# Assuming that the `extend_path` function already exists, zsh2xonsh is able to translate this

export BROWSER="/usr/bin/firefox"

extend_path ~/.yarn/bin
extend_path ~/.cargo/bin
extend_path ~/go/bin

# My private bin ($HOME/bin) 
extend_path ~/bin
# Where pip puts its bin files
extend_path ~/.local/bin
# TODO: I really don't like hardcoding these
extend_path ~/.gem/ruby/2.5.0/bin
extend_path ~/.rustup/nightly-x86_64-unknown-linux-gnu/bin/

# NOTE: Prefix with 'py' to indicate we are in xonsh
# We really should be prefixing with 'xonsh', but 'py' is shorter
# It's not really ambiguous, since this is really the python-prompt (for all
# intents and purposes)
# I'm not going to confuse with the regular python interpreter (python3) cause i'll
# know its a shell
export XONSH_PREFIX="py"
export XONSH_PREFIX_COLOR="yellow"
