Cram test file for MyHelp.

Check .myhelprc:
  $ cd "${TESTDIR}"
  $ cat tmp/.myhelprc
  export MYHELP_DIR=* (glob)
  export MYHELP_PKG_DB=*packages.db (glob)
  export MYHELP_PKG_YAML=*packages.yaml (glob)
  export MYHELP_BIN_DIR=* (glob)
  export MYHELP_REFRESH=[01] (re)
  export MYHELP_ALIAS_NAME=* (glob)
  alias *='source myhelp.sh' (glob)

Check other installation files:
  $ source tmp/.myhelprc
  $ [ -d "${MYHELP_DIR}" ]
  $ [ -f "${MYHELP_PKG_DB}" ]
  $ [ -f "${MYHELP_PKG_YAML}" ]
  $ [ -d "${MYHELP_BIN_DIR}" ]
  $ [ -f "${MYHELP_BIN_DIR}/myhelp.sh" ]
  $ [ -f "${MYHELP_BIN_DIR}/myhelp.py" ]

Check help:
  $ . "${MYHELP_BIN_DIR}"/myhelp.sh -T "${MYHELP_BIN_DIR}" -h
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
  $ . "${MYHELP_BIN_DIR}"/myhelp.sh -T "${MYHELP_BIN_DIR}" myhelp.t | grep -f "${TMPIN}" | wc -l >"${TMPOUT}"
  $ read MYHELP_X <"${TMPOUT}"
  $ [ "${MYHELP_X}" -ge 3 ]

Examine ls
  $ cat >"${TMPIN}" <<HEREDOC
  > ls has an info page\.
  > ls has a man page\.
  > ls is the command .*
  > HEREDOC
  $ . "${MYHELP_BIN_DIR}"/myhelp.sh -T "${MYHELP_BIN_DIR}" ls | grep -f "${TMPIN}" | wc -l >"${TMPOUT}"
  $ read MYHELP_X <"${TMPOUT}"
  $ [ "${MYHELP_X}" -ge 3 ]

Examine alias
  $ alias MYHELP_SPLUNGE='whatever'
  $ . "${MYHELP_BIN_DIR}"/myhelp.sh -T "${MYHELP_BIN_DIR}" MYHELP_SPLUNGE | grep "MYHELP_SPLUNGE is aliased to 'whatever'\."
  MYHELP_SPLUNGE is aliased to 'whatever'.

Examine python
  $ cat >"${TMPIN}" <<HEREDOC
  > There .* process* called python\.
  > python is a .* package\.
  > python has a man page\.
  > python is the command .*python\.
  > python is .*python\.
  > HEREDOC
  $ . "${MYHELP_BIN_DIR}"/myhelp.sh -T "${MYHELP_BIN_DIR}" python | grep -f "${TMPIN}" | wc -l  >"${TMPOUT}"
  $ read MYHELP_X <"${TMPOUT}"
  $ [ "${MYHELP_X}" -ge 1 ]

Horrible filename:
  $ tempfilex="S(q\"['u*d l\*y="
  $ echo "splunge" > "${tempfilex}"
  $ cat >"${TMPIN}" <<HEREDOC
  > WARNING: Treating "*" in "S(q"['u*d l\*y=" as a literal character, not a glob.
  > S(q"['u*d l\*y= is an ASCII text file.
  > S(q"['u*d l\*y= has the MIME type text/plain.
  > HEREDOC
  $ . "${MYHELP_BIN_DIR}"/myhelp.sh -T "${MYHELP_BIN_DIR}" "${tempfilex}" | grep -Ff "${TMPIN}" | wc -l  >"${TMPOUT}"
  $ read MYHELP_X <"${TMPOUT}"
  $ [ "${MYHELP_X}" -ge 3 ]

Horrible name pattern search:
  $ . "${MYHELP_BIN_DIR}"/myhelp.sh -T "${MYHELP_BIN_DIR}" -p "${tempfilex}" | grep -Ff "${TMPIN}" | wc -l  >"${TMPOUT}"
  $ read MYHELP_X <"${TMPOUT}"
  $ [ "${MYHELP_X}" -ge 1 ]
  $ rm -f "${tempfilex}"

