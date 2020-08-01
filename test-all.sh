#!/bin/bash

set -e

rm -f tests/tmp/*
./install.sh -Tfc tests/tmp -t tests/tmp

python3 -m pytest

cd tests
cram --shell=/bin/bash myhelp.t

