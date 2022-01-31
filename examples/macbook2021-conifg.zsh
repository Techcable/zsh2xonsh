# This is the environment configuration for my Macbook Pro
#
# Obviously a bit more difficult than the old exampele (which was just exports)
#
# Things to note:
# 1. the if statement is translated into a python if, BUT the actual test `[[ -d ... ]]` is *performed by zsh*
#      - this means the if statement (test) is *evaluated as a zsh builtin*, not translated :)
#      - Yes. It's slower, but it has flawless compatibility
# 2. the subprocess invocation `$()` is not performed directly in xonsh, instead we use python subprocesses
#
# basically any time you see anything beyond a simple literal string
# it's actually zsh doing all the hard work :)
#
# all the globbing and bizare quoting rules are handled 100% the way zsh would,
# because it's actually zsh doing the expansion :)
#
# The exception to this is control flow constructs like `if`s and `function`s
# In order to proerly analyse them (and collect exports and aliases) we have to translate them
# into Python.


# NOTE: You could provide this function as an "extra builtin",
# or you could implement it yourself here
#
# Either way will work correctly
function extend_path() {
    export PATH="$PATH:$1"
}

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

# Some homebrew things are "keg-only" meaning they are not on the path by default
#
# Usually these are alternative versions of the main package.
# Particular examples are lua@5.3 and python@3.10
#
# We want these on the path, but we want them at the end (lower precedence)
# so they don't conflict with existing versions
#
# Use the extend_path builtin to add it to the end (but only if the keg exists)
function detect_keg() {
    local keg_prefix="/opt/homebrew/opt";
    if [[ -d "${keg_prefix}/$1/bin" ]]; then
        # echo "Detected keg $1";
        extend_path "${keg_prefix}/$1/bin"
    fi
}
detect_keg "python@3.10"
detect_keg "lua@5.3"

# Mac has no LDD command
#
# See here: https://discussions.apple.com/thread/309193 for suggestion
# Also "Rosetta stone for Unixes"
alias ldd="echo 'Using otool -L' && otool -L"

# NOTE: Prefix with 'py' to indicate we are in xonsh
# We really should be prefixing with 'xonsh', but 'py' is shorter
# It's not really ambiguous, since this is really the python-prompt (for all
# intents and purposes)
# I'm not going to confuse with the regular python interpreter (python3) cause i'll
# know its a shell
export XONSH_PREFIX="py"
export XONSH_PREFIX_COLOR="yellow"
