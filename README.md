# upbank2ynab

Import Up bank transactions to YNAB running in a docker container

- fetches transactions from Up Bank API, transforms to YNAB format and uploads to YNAB
- currently only supports Up transactions account
- stores last transaction date in a file to avoid duplicate transactions
- updates every 5 mins
- TODO: sends a healthcheck.io ping

## Requirements

- YNAB API key
- Up API key
- Not implemented - Optional: Healthchecks.io URL

## Setup

- build docker image: `docker build -t upbank2ynab .`
- run with docker compose: `docker-compose up -d`

## Usage