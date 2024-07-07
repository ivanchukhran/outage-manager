# Outage Manager

This is a simple Telegram bot that helps you to check the status of your electricity outage.

## Installation

1. Clone the repository


``` shell
git clone git@github.com:ivanchukhran/outage-manager.git
cd outage-manager
```

2. Install dependencies

``` shell
poetry install
```

3. Add your Telegram bot token to the `.env` file

``` shell
API_TOKEN=YOUR_TOKEN
```

4. Run the bot

``` shell
poetry run python outage-manager/bot.py
```

## DOCKER support

1. Build the image

``` shell
docker build -t outage-manager .
```

2. Run the container

``` shell
docker run outage-manager
```

You can also specify the TZ environment variable to set the timezone

``` shell
docker run -e TZ=Europe/Kiev outage-manager
```

or via the Dockerfile

``` dockerfile
ENV TZ=Europe/Kiev
```

