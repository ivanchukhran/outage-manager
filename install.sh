#!/bin/bash
#
# This script is used to install the necessary packages for the
# development environment.

# install miniconda
#
echo "Check if miniconda is installed"
if ! command -v conda &> /dev/null
then
    echo "Miniconda is not installed. Installing miniconda..."
    mkdir -p ~/miniconda3
    wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ~/miniconda3/miniconda.sh
    bash ~/miniconda3/miniconda.sh -b -u -p ~/miniconda3
    rm -rf ~/miniconda3/miniconda.sh
else
    echo "Miniconda is already installed"
fi

# create the conda environment
~/miniconda3/bin/conda init bash
source ~/.bashrc

PATH=~/miniconda3/bin:$PATH

conda activate base

echo "Creating the conda environment"
conda create -n outage-manager python=3.11.8 -y

echo "Activating the conda environment"
echo source activate outage-manager >> ~/.bashrc

PATH=~/miniconda3/envs/outage-manager/bin:$PATH

echo "Current python version"
python --version

# install the necessary packages
echo "Installing the necessary packages"
pip install poetry

echo "Install the dependencies"
poetry install
pip install -r requirements.txt

echo "Installing the playwright dependencies"
poetry run python3 -m playwright install-deps
echo "Installing the chromium browser"
poetry run python3 -m playwright install chromium

# echo "Running the application"
# poetry run python3 outage-manager/bot.py
