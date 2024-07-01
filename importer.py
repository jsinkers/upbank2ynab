from datetime import datetime, timedelta
import json
import logging
import os
import sys
import requests

from dotenv import load_dotenv
from upbankapi import Client as UpBankClient
from ynab_api import Configuration, ApiClient
from ynab_api.api.transactions_api import TransactionsApi
from ynab_api.model.save_transaction import SaveTransaction
from ynab_api.model.save_transactions_wrapper import SaveTransactionsWrapper

# Set up logging
logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables from .env file
load_dotenv()

# Common API tokens
UP_BANK_API_TOKEN = os.getenv('UP_BANK_API_TOKEN', "")
YNAB_API_TOKEN = os.getenv('YNAB_API_TOKEN', "")

# Healthchecks.io URL
HEALTHCHECKS_IO_URL = os.getenv('HEALTHCHECKS_IO_URL')

# Define account-specific configurations
ACCOUNT_CONFIGS = [
    {
        'UP_BANK_ACCOUNT_LABEL': os.getenv('UP_BANK_ACCOUNT_LABEL_1', ""),
        'UP_BANK_ACCOUNT_ID': os.getenv('UP_BANK_ACCOUNT_ID_1', ""),
        'YNAB_BUDGET_ID': os.getenv('YNAB_BUDGET_ID_1', ""),
        'YNAB_ACCOUNT_ID': os.getenv('YNAB_ACCOUNT_ID_1', ""),
        'APP_STATE_FILE': os.getenv('APP_STATE_FILE_1')
    },
    {
        'UP_BANK_ACCOUNT_LABEL': os.getenv('UP_BANK_ACCOUNT_LABEL_2', ""),
        'UP_BANK_ACCOUNT_ID': os.getenv('UP_BANK_ACCOUNT_ID_2', ""),
        'YNAB_BUDGET_ID': os.getenv('YNAB_BUDGET_ID_2', ""),
        'YNAB_ACCOUNT_ID': os.getenv('YNAB_ACCOUNT_ID_2', ""),
        'APP_STATE_FILE': os.getenv('APP_STATE_FILE_2')
    }
]

def notify_healthcheck(status):
    logging.info(f"Notifying Healthchecks.io with status: {status}")
    if HEALTHCHECKS_IO_URL:
        try:
            if status == 'start':
                response = requests.get(HEALTHCHECKS_IO_URL + '/start')
            elif status == 'success':
                response = requests.get(HEALTHCHECKS_IO_URL)
            elif status == 'failure':
                response = requests.get(HEALTHCHECKS_IO_URL + '/fail')
            response.raise_for_status()
            logging.info(f"Healthchecks.io notification successful: {status}")
        except Exception as e:
            logging.error(f"Failed to notify Healthchecks.io: {e}")

def save_app_state(app_state, app_state_file):
    with open(app_state_file, 'w') as f:
        json.dump(app_state, f)
    logging.info("App state saved")

def load_app_state(app_state_file):
    if not os.path.exists(app_state_file):
        logging.warning("App state file not found - using yesterday as last transaction date")
        last_transaction_dt = datetime.now() - timedelta(days=1)
        return {"last_transaction_dt": last_transaction_dt.isoformat()}
    with open(app_state_file, 'r') as f:
        logging.info("App state loaded")
        return json.load(f)

def fetch_up_bank_transactions(client, since, account_id):
    logging.info(f"Fetching transactions from Up Bank since {since}")
    up_spending_account = client.account(account_id=account_id)
    transactions = list(up_spending_account.transactions(since=since))
    logging.info(f"Transactions fetched: {transactions}")
    return transactions

def transform_transactions(transactions):
    logging.info("Transforming transactions")
    transaction_list = []
    for transaction in transactions:
        transaction_data = {
            'date': transaction.created_at,
            'amount': transaction.amount_in_base_units * 10,  # YNAB uses milliunits
            'payee_name': transaction.description,
            'memo': transaction.raw_text,
            'cleared': 'cleared' if transaction.status == 'SETTLED' else 'uncleared'
        }
        transaction_list.append(transaction_data)
    logging.info("Transformation complete")
    return transaction_list

def import_to_ynab(api_instance, transactions, budget_id, account_id):
    logging.info("Importing transactions to YNAB")
    ynab_transactions = []
    for transaction in transactions:
        ynab_transaction = SaveTransaction(
            account_id=account_id,
            date=transaction['date'].date(),
            amount=transaction['amount'],
            payee_name=transaction['payee_name'],
            memo=transaction['memo'],
            cleared=transaction['cleared']
        )
        ynab_transactions.append(ynab_transaction)
    
    transactions_wrapper = SaveTransactionsWrapper(transactions=ynab_transactions)
    api_instance.create_transaction(budget_id, transactions_wrapper)

def process_account(account_config):
    logging.info(f"Processing account: {account_config['UP_BANK_ACCOUNT_LABEL']}")

    # Initialize Up Bank client
    up_client = UpBankClient(token=UP_BANK_API_TOKEN)
    
    # Initialize YNAB client
    configuration = Configuration()
    configuration.api_key_prefix['bearer'] = 'Bearer'
    configuration.api_key['bearer'] = YNAB_API_TOKEN

    # Create an instance of the API class
    api_client = ApiClient(configuration)
    ynab_instance = TransactionsApi(api_client)
    
    # Load the app state
    app_state = load_app_state(account_config['APP_STATE_FILE'])
    # Determine last imported transaction date in YNAB
    last_transaction_dt = datetime.fromisoformat(app_state.get('last_transaction_dt'))
    logging.info(f"Last transaction datetime: {last_transaction_dt}")

    # Fetch and transform transactions
    transactions = fetch_up_bank_transactions(up_client, last_transaction_dt, account_config['UP_BANK_ACCOUNT_ID'])
    if not transactions:
        logging.info("No new transactions to import")
    else:
        transformed_transactions = transform_transactions(transactions)
    
        # Import transactions into YNAB
        import_to_ynab(ynab_instance, transformed_transactions, account_config['YNAB_BUDGET_ID'], account_config['YNAB_ACCOUNT_ID'])

        # Save the new last transaction date
        if transactions:
            last_transaction_dt = max(t.created_at for t in transactions)
            # add 1s to the last transaction date to avoid importing the same transaction again
            last_transaction_dt += timedelta(seconds=1)
            app_state['last_transaction_dt'] = last_transaction_dt.isoformat()
            save_app_state(app_state, account_config['APP_STATE_FILE'])

def main():
    notify_healthcheck('start')
    try:
        for account_config in ACCOUNT_CONFIGS:
            process_account(account_config)
        notify_healthcheck('success')
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        notify_healthcheck('failure')

if __name__ == '__main__':
    main()
