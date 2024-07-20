#!/usr/bin/bash
#
# This script is used to install the necessary packages for the
# development environment.

echo "Check if poetry is installed"
if ! command -v poetry &> /dev/null
then
    echo "Poetry is not installed. Installing poetry..."
    curl -sSL https://install.python-poetry.org | python3 -
else
    echo "Poetry is already installed"
fi

echo "Install the dependencies"
poetry install

echo "Installing the playwright browser"
poetry run python3 -m playwright install chromium

echo "Running the application"
poetry run python3 outage-manager/bot.py
