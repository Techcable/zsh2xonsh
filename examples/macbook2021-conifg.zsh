# This is the environment configuration for my Macbook Pro
#
# Obviously a bit more difficult than the old exampele (which was just exports)
#
# Things to note:
# 1. the if statement is translated into a python if, BUT the actual test `[[ -d ... ]]` is *performed by zsh*
#      - this means the if statement (test) is *evaluated as a zsh builtin*, not translated :)
#      - Yes. It's slower, but it has flawless compatibility
# 2. the subprocess invocation `$()` is not performed directly, instead 
#
# basically any time you see anything beyond a simple literal string
# it's actually zsh doing all the hard work :)
#
# all the globbing and bizare quoting rules are handled 100% the way zsh would,
# because it's actually zsh doing the expansion :)



# Automatically uses the default browser
export BROWSER="/usr/bin/open"

local preferred_java_version=17
local preferred_java_home=$(fd "jdk-${prefered_java_version}.*\.jdk" /Library/Java/JavaVirtualMachines --maxdepth 1)
if [[ -d "$preferred_java_home/Contents/Home" ]]; then
    export JAVA_HOME="${preferred_java_home}/Contents/Home";
fi

extend_path ~/.cargo/bin
# My private bin ($HOME/bin) 
extend_path ~/bin
# TODO: I really don't like hardcoding these
extend_path ~/.rustup/toolchains/nightly-aarch64-apple-darwin/bin

# NOTE: Prefix with 'py' to indicate we are in xonsh
# We really should be prefixing with 'xonsh', but 'py' is shorter
# It's not really ambiguous, since this is really the python-prompt (for all
# intents and purposes)
# I'm not going to confuse with the regular python interpreter (python3) cause i'll
# know its a shell
export XONSH_PREFIX="py"
export XONSH_PREFIX_COLOR="yellow"
