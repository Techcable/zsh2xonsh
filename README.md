zsh2xonsh
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

If we encounter an unsupported feature (like a `for` loop), we
throw a descriptive error instead of doing something potenitally incorrect.

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
   - Local variables (local var=x) are supported too :)

All of these behaviors are 100% compatible with their zsh equivalents.
If you try anything else (or encounter an unsupported corner case), then you will get a descripitive error :)

## Installation & Usage
This is a pypi package, install it with `pip install zsh2xonsh`.

Then, you can use the CLI (`python -m zsh2xonsh`) or call the module from your `.xonshrc`.

## Motiviation
First of all, I need support for `eval $(brew shellenv)` .

Second of all, I still use `zsh` as my backup shell.

This means I need to setup `$PATH` and other enviornment variables for both of these shells.

The natural way to set these up is by using shell scripts.
I have a seperate one for each of my different machines (server, macbook, old lapotop, etc)

For each of these (tiny) shell scripts, `zsh2xonsh` works very well :)

So in addition to properly translating `$(brew shellenv)`,
it also needs to translate basic shell "environement files".