#!/bin/bash

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
cram --shell=/bin/bash myhelp.t

