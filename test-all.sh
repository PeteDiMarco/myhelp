#!/bin/bash

if which cram3 >/dev/null 2>&1 ; then
    CRAM=$(which cram3)
elif which cram >/dev/null 2>&1 ; then
    CRAM=$(which cram)
else
    echo "Please install Python's cram module."
    exit 1
fi

set -e

# Clean up test directory
find tests/tmp/ -type f -! -name '.git*' | xargs rm -f

# Install in test directory
./install.sh -Tfc tests/tmp -t tests/tmp
source tests/tmp/.myhelprc

# Run unit tests
python3 -m pytest

# Run system tests
cd tests
"${CRAM}" --shell=/bin/bash myhelp.t

