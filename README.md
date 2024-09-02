# MyHelp Command Line Utility

MyHelp is a help utility for Bash. It tries to identify every name provided. 
MyHelp looks at man pages, info pages, aliases, files, shell variables,
devices, filesystems, running processes, and built-in shell commands.

### Prerequisites

* Python 3.8 or above
* Bash
* which

#### Optional
* getent
* df
* xdg-mime
* file
* info
* man

### Installing

For a first time installation, simply run `./install.sh` from the source directory.
This will install 2 scripts into your local bin directory (either `~/bin` or `~/.local/bin`).
It will also create the file `~/.myhelprc` and the directory `~/.myhelp`. `~/.myhelprc`
will contain an alias (called `myhelp` by default) which is used to run the application.

Be sure to add `source ~/.myhelprc` to your `.bashrc` file, like this:

    if [ -f ~/.myhelprc ]; then
        source ~/.myhelprc
    fi

You will also need to run `source ~/.myhelprc` in any shell that was opened before
installation.

The directory `~/.myhelp` contains a database of the names of the packages installed on the machine.

To install over an existing installation, use:
    `./install.sh -f`

You can customize the names of the alias, source directory, configuration directory,
and bin directory with these commandline options:

    -s, --src     # Directory containing source files.  
    -c, --config  # Configuration directory.  
    -t, --target  # Directory to install files.  
    -a, --alias   # User's alias for MyHelp.  

### Configuring

MyHelp uses 2 configuration files. `.myhelprc` contains shell variables and the alias
used to call the application. `packages.yaml` contains the commands needed to read and
parse the names of the various packages installed on the computer.

#### .myhelprc

    export MYHELP_DIR="${HOME}/.myhelp"
    export MYHELP_PKG_DB="${MYHELP_DIR}/packages.db"
    export MYHELP_PKG_YAML="${MYHELP_DIR}/packages.yaml"
    export MYHELP_BIN_DIR="${HOME}/bin"
    export MYHELP_REFRESH=0       # 0=Only reload with '-r', 1=Reload package database on every call.
    export MYHELP_ALIAS_NAME=myhelp
    export MYHELP_PYTHON="python"
    export MYHELP_PYTHONPATH="<SOURCE_DIRECTORY>"
    export MYHELP_VENV_BIN="<SOURCE_DIRECTORY>/.venv/bin"
    alias myhelp='source myhelp.sh'


#### packages.yaml

`version: 1`	# *Should always equal 1.* <br/>
`packages:` <br/>
&nbsp;&nbsp; *package-manager-name*: <br/>
&nbsp;&nbsp;&nbsp;&nbsp; `description:` "String describing the type of package." <br/>
&nbsp;&nbsp;&nbsp;&nbsp; `command:` "Shell command returning the name of each package, 1 per line."

To add support for another package manager, add the name of the package manager executable (indented)
followed by a colon. On the next line, provide a `description:` of the package type in quotes. The third line
should contain the shell `command:` needed to extract the names of all the packages handled by the package manager.
The shell command should return one name per line.

MyHelp will use `which` to confirm that it has access to the package manager executable. If it does, it will execute
the command. MyHelp checks the return code of the last command in the pipeline to determine if the command was
successful. If the return code is not 0, it will assume that the command has failed. Please note:
1.  MyHelp will not detect errors that occur earlier in the command pipeline unless you add `set -o pipefail;` to
the beginning of your command.
2.  Returning a non-zero value does not always mean that an actual error has occurred. E.g.: `grep` returns 1 if
it's unable to find its pattern in the input stream.

##### Example

    packages:
      pip:
        description: 'Python package'
        command: "pip list 2>/dev/null | tail +3 | sed -e 's/  .*$//'"

The Python package manager `pip` is called with the `list` command. Output to standard error is ignored. The first
2 lines of output are ignored because they contain header information. Finally, all the text after the first 2 spaces
is stripped away (this is the package's version information).

### Uninstalling

Run `./uninstall.sh`. Use `uninstall.sh -f` to delete the directory `~/.myhelp`.

## Description

MyHelp is composed of 2 scripts. The first script is called `myhelp.sh`. `myhelp.sh`
must be run with `source` from the shell in order for MyHelp to read the current shell's
aliases and settings. `myhelp.sh` then calls `myhelp.py`.

### Help

    usage: myhelp [-h] [-D] [-r] [-p PATTERN] [-s] [-i] [NAME [NAME ...]]
    
    Identifies the names provided. Tries every test imaginable. Looks for:
    man pages, info pages, executables in PATH, aliases, shell variables, running
    processes, shell functions, built-in shell commands, packages, filesystems,
    and files relative to the current working directory.
    
    positional arguments:
      NAME                  Object to identify.
    
    optional arguments:
      -h, --help            show this help message and exit
      -D, --DEBUG           Enable debugging mode.
      -r, --refresh         Refresh package cache.
      -p PATTERN, --pattern PATTERN
                            Search for glob pattern. The pattern should be wrapped
                            in quotes.
      -s, --standalone      Don't read shell builtins.
      -i, --interactive     Show spinner when refreshing package cache.
    
    Pattern searches use "globs". Pattern searches cannot be performed with the
    following commands:
        getent group, getent hosts, getent passwd, getent services, info, man,
        which, xdg-mime

## Versioning

0.5

## Authors

* **Pete DiMarco** - *Initial work* - [PeteDiMarco](https://github.com/PeteDiMarco)

## License

This project is licensed under the Apache 2.0 License - see the [LICENSE](LICENSE) file
for details.

