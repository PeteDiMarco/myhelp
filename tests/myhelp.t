Cram test file for MyHelp.

Check .myhelprc:
  $ cat ~/.myhelprc
  export MYHELP_DIR=.* (re)
  export MYHELP_PKG_DB=.*packages.db (re)
  export MYHELP_PKG_YAML=.*packages.yaml (re)
  export MYHELP_BIN_DIR=.* (re)
  export MYHELP_REFRESH=[01] (re)
  export MYHELP_ALIAS_NAME=.* (re)
  alias .*='source myhelp\.sh' (re)

Check other installation files:
  $ source ~/.myhelprc
  $ [ -d "${MYHELP_DIR}" ]
  $ [ -f "${MYHELP_PKG_DB}" ]
  $ [ -f "${MYHELP_PKG_YAML}" ]
  $ [ -d "${MYHELP_BIN_DIR}" ]
  $ [ -f "${MYHELP_BIN_DIR}/myhelp.sh" ]
  $ [ -f "${MYHELP_BIN_DIR}/myhelp.py" ]

Check help:
  $ cd "${TESTDIR}"
  $ . ../myhelp.sh -T .. -h
  usage: * [-h] [-D] [-r] [-p PATTERN] [-s] [-i] [NAME [NAME ...]] (glob)
  
  Identifies the names provided.  Tries every test imaginable.  Looks for:
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
      * (glob)
      * (glob)

Test specific searches:
Examine myhelp.t
  $ TMPIN=$(tempfile)
  $ TMPOUT=$(tempfile)
  $ cat >"${TMPIN}" <<HEREDOC
  > myhelp\.t is an ASCII text file\.
  > myhelp\.t has the MIME type .*
  > myhelp\.t is on filesystem .*
  > HEREDOC
  $ . ../myhelp.sh -T .. myhelp.t | grep -f "${TMPIN}" | wc -l
  3

Examine ls
  $ cat >"${TMPIN}" <<HEREDOC
  > ls has an info page\.
  > ls has a man page\.
  > ls is the command .*
  > HEREDOC
  $ . ../myhelp.sh -T .. ls | grep -f "${TMPIN}" | wc -l
  3

Examine alias
  $ alias MYHELP_SPLUNGE='whatever'
  $ . ../myhelp.sh -T .. MYHELP_SPLUNGE | grep "MYHELP_SPLUNGE is aliased to 'whatever'\."
  MYHELP_SPLUNGE is aliased to 'whatever'.

Examine python
  $ cat >"${TMPIN}" <<HEREDOC
  > There .* process* called python\.
  > python is a .* package\.
  > python has a man page\.
  > python is the command .*python\.
  > python is .*python\.
  > HEREDOC
  $ . ../myhelp.sh -T .. python | grep -f "${TMPIN}" | wc -l  >"${TMPOUT}"
  $ read MYHELP_X <"${TMPOUT}"
  $ [ "${MYHELP_X}" -ge 5 ]

