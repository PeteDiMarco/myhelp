# MyHelp Commandline Utility

This is a help utility for Bash. It tries to identify every name provided. 
MyHelp looks at man pages, info pages, aliases, files, shell variables,
devices, filesystems, running processes, and built-in shell commands.

### Prerequisites

* Python 3.6 or above
* Bash

#### Optional
* getent
* xdg-mime
* file
* info
* man
* which

### Installing

For a first time installation, simply run `./install.sh` from the source directory.
This will install 2 scripts into your local bin directory (either `~/bin` or `~/.local/bin`).
It will also create the file `~/.myhelprc` and the directory `~/.myhelp`. `~/.myhelprc`
will contain an alias called `myhelp` which is used to run the application. Be sure to add
`source ~/.myhelprc` to your `.bashrc` file.

The directory `~/.myhelp` contains a database of packages installed on the machine and
local to the user's account.

To install over an existing installation, use:
    `./install.sh -f`

You can customize the names of the alias, source directory, configuration directory,
and bin directory with these commandline options:

  -s, --src             Directory containing source files.
  -c, --config          Configuration directory.
  -t, --target          Directory to install files.
  -a, --alias           User's alias for myhelp.


### Uninstalling

Run `./uninstall.sh`.

## Description

### myhelp.sh


## Versioning

0.2

## Authors

* **Pete DiMarco** - *Initial work* - [PeteDiMarco](https://github.com/PeteDiMarco)

## License

This project is licensed under the Apache 2.0 License - see the [LICENSE](LICENSE) file
for details.

