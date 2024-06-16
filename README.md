# upbank2ynab

Import Up bank transactions to YNAB running in a docker container

- fetches transactions from Up Bank API, transforms to YNAB format and uploads to YNAB
- currently only supports Up transactions account
- stores last transaction date in a file to avoid duplicate transactions
- updates every 5 mins
- __TODO:__ send a healthcheck.io ping

## Requirements

- YNAB API key
- Up API key
- (Not implemented) Optional: Healthchecks.io URL

## Setup

- Clone the repo `git clone https://github.com/jsinkers/upbank2ynab.git`
- Create environment variable file from template `cp .env.example .env`
- Populate `.env` with your YNAB and Up API keys
  - Identify the Up transactions account ID (see `https://developer.up.com.au/#accounts`, account type is `TRANSACTIONAL`)
  - Identify the YNAB budget ID and account ID from the URL when viewing the account in the browser
- Build docker image: `docker build -t upbank2ynab .`
- Run with docker compose: `docker-compose up -d`

## Usage