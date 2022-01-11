zsh2xonsh ![pypy](https://img.shields.io/pypi/v/zsh2xonsh) ![powered-by-xonsh](https://img.shields.io/badge/powered%20by-xonsh-brightgreen)
=========
Have you heard of [xonsh](https://xon.sh/)? It's a Python-powered shell.

You can do amazing things like this:
````xonsh
# Interpolate python -> shell
echo @(i for i in range(42))

# Interpolate shell -> python
for filename in `.*`:
    print(filename)
    du -sh @(filename)

# Execute regular shell commands too
cat /etc/passwd | grep root
````

As you can immagine, this awesomeness is not POSIX-compliant :(

This makes it difficult to setup your `$PATH` and do things like `eval $(brew shellenv)`

This package exists to translate traditional `zsh` scripts into `xonsh` code.

## Compatibility (and how it works)
The goal is 100% compatibility for a *subset* of shell. 

Compatibility is achived by delegating most of the work to zsh.

That is, `export FOO="$(echo bar)"` in a shell script becomes (essentially)  `$FOO=$(zsh -c 'echo bar')` in xonsh.

We have `zsh` handle all the globbing/quoting/bizzare POSIX quirks.

In the face of ambiguity, or if we encounter an unsupported feature (like a `for` loop), then we fail-fast.

This is the most important feature. If something can't be supported 100%, then it will throw a descriptive error. Anything else is a bug :)

### Features
The included shell features include:

1. Quoted expressions `"$VAR glob/*"` (zsh does expansion here)
2. Unquoted literals `12`, `foo` `~/foo` (mostly translated directly)
3. Command substitutions "$(cat file.txt | grep bar)" 
   - zsh does all the work here
   - Supports both quoted and unquoted forms
3. If/then statements
   - Conditionals are executed by zsh (so `[[ -d "foo" ]]` works perfectly)
   - Translated into python if (so body will not run unless conditional passes)
4. Exporting variables `export FOO=$BAR`
   - Translates `$PATH` correctly (xonsh thinks it's a list, zsh thinks it's a string)
   - This is where the subprocess approach doesn't work blindly....
      - We support it cleanly by doing the left-hand assignment xonsh, and the right-hand expression in `zsh` :)
   - Local variables (local var=x) are supported too (with the proper scoping)
5. Support `alias foo="bar"`
   - This even supports globbing in the alias, so `alias lsdot="echo .*"` would glob in the same way that zsh does (experimental)
6. Basic support for function declarations (and having positional arguments)
   - Local variables are scoped properly inside the function :)
7. Support for 'echo' builtin as a python 'print'

You can also add "external builtins", which are extra commands that the script can invoke. In my own files, I use this to add an `extend_path` command (even though zsh2xonsh properly translates $PATH variables already, it's still a nice utility)

My [macbook config](./examples/macbook2021-config.zsh) is a good example of the full power of the translator. It supports function declarations, if/then statements and conditionals (all in an attempt to cleanup homebrew cludges lol).

All of these behaviors should be 100% compatible with their zsh equivalents.
If you try anything else (or encounter an unsupported corner case), then you will get a descripitive error :)

## Installation & Usage
This is a pypi package, install it with `pip install zsh2xonsh`.

The API is simple, run `translate_to_xonsh(str) -> str` to translate from `zsh` -> `xonsh` code.
This does not require xonsh at runtime, and can be done ahead of time. 

If you want to evaluate the code immediately after translating it (for example in a `.xonshrc`), you can use
. This requires xonsh at runtime (obviously) and uses the `evalx` builtin.

Additionally you can use the CLI (`python -m zsh2xonsh`), which accepts an import.

If you want to provide extra utility functions to your code, you can define `extra_builtins`.

### Example
In my `.xonshrc`, I dynamically translate and evaluate the output of `brew shellenv`:
````xonsh
zsh2xonsh.translate_to_xonsh_and_eval($(/opt/homebrew/bin/brew shellenv))
````

Likewise, I do the same with my machine-specific `.config.zsh` files (in the example directory).

## Motiviation
First of all, I need support for `eval $(brew shellenv)` .

Second of all, I still use `zsh` as my backup shell (by the use of my [wrap-shell](https://github.com/Techcable/wrap-shell) utility).

This means I need to setup `$PATH` and other enviornment variables for both of these shells, indepenently of each other.

The natural way to set these up is by using shell scripts.
I have a seperate one for each of my different machines (server, macbook, old lapotop, etc)

For each of these (tiny) shell scripts, `zsh2xonsh` works very well :)

So in addition to properly translating `$(brew shellenv)`,
it also needs to translate these basic shell "environement files".

Turns out, dealing with platform specific quirks can get pretty intense and requires things like function definitions and if/then statements.
In order to properly support `export`s, control flow has to be emulated in Python (can't just delegate to zsh).