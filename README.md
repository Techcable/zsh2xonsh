zsh2xonsh
=========
Have you heard of [xonsh](https://xon.sh/)? It's a Python-powered shell.

You can do amazing things like this:
````xonsh
# Interpolate python -> shell
echo @(i for i in range(42))

# Intepolate shell -> python
for filename in `.*`:
    print(filename)
    du -sh @(filename)

# Execute regular shell commands too
cat /etc/passwd | grep root
````

As you can immagine, this awesomeness is not POSIX-compliant :(

This makes it difficult to setup your `$PATH` and do things like `eval $(brew shellenv)`

This package exists to translate traditional `zsh` scripts into `xonsh` code.

## How it works
This is not (really) a compiler.

Compatibility is achived by delegating most of the work to zsh.


As such, the translated shell expressions are *100% compatible* because it's actually `zsh` doing all the work :)

## Compatibility (and how it works)
The goal is 100% compatibility for a *subset* of shell. 


This is achieved because it is not (really) a compiler,
it delegates most of the work to zsh.

That is, `export FOO="$(echo bar)"` in a shell script becomes (essentially)  `$FOO=$(zsh -c 'echo bar')` in xonsh.

We have `zsh` handle all the globbing/quoting/bizzare POSIX quirks.

If we encounter an unsupported feature (like a `for` loop),
throw a descriptive error instead of trying a half-baked solution. 

This is the most important feature. If something can't be supported 100%, then it will throw a descriptive error. Anything else is a bug :)

### Features
The included shell features include:

1. Quoted `"$VAR glob/*"` (zsh does expansion here)
2. Unquoted literals `12`, `foo` `~/foo` (mostly translated directly)
3. Command substituins "$(cat file.txt | grep bar)" 
   - zsh does all the work here
   - Supports both quoted and unquoted forms
3. If/then statements
   - Conditionals are executed by zsh (so `[[ -d "foo" ]]` works perfectly)
   - Translated into python if (so body will not run unless conditional passes)
4. Exporting variables `export FOO=$BAR`
   - Translates `$PATH` correctly (xonsh thinks it's a list, zsh thinks it's a string)
   - This is where the subprocess approach doesn't work blindly, `export` in subprocess 
      - We support it cleanly by doing the left-hand assignment xonsh, and the right-hand expression in `zsh` :)


Either behavior is 100% compatible, or you get a descripitve error. Anything else is a bug :)


## Motiviation
First of all, I need support for `eval $(brew shellenv)` .

Second of all, I still use `zsh` as my backup shell.

This means I need to setup `$PATH` and other enviornment variables for both of these shells.

The natural way to set these up is by using shell scripts.
I have a seperate one for each of my different machines (server, macbook, old lapotop, etc)

For each of these (tiny) shell scripts, `zsh2xonsh` works very well :)

So in addition to properly translating `$(brew shellenv)`,
it also needs to translate basic shell "environement files".
