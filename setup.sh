#!/usr/bin/bash

# Install poetry and dependencies
#

# Install poetry
curl -sSL https://install.python-poetry.org | python3 -

# Add poetry to path
export PATH=$PATH:$HOME/.local/bin

# Install dependencies
poetry install
