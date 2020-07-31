#!/bin/bash

set -e
python3 -m pytest
cd tests
cram --shell=/bin/bash myhelp.t

