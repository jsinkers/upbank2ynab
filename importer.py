from datetime import datetime, timedelta
import json
import os

from dotenv import load_dotenv
from upbankapi import Client as UpBankClient
from ynab_api import Configuration, ApiClient
from ynab_api.api.transactions_api import TransactionsApi
from ynab_api.model.save_transaction import SaveTransaction
from ynab_api.model.save_transactions_wrapper import SaveTransactionsWrapper

# Load environment variables from .env file
load_dotenv()

# Get API tokens and IDs from environment variables
UP_BANK_API_TOKEN = os.getenv('UP_BANK_API_TOKEN', "")
UP_BANK_ACCOUNT_ID = os.getenv('UP_BANK_ACCOUNT_ID', "")
YNAB_API_TOKEN = os.getenv('YNAB_API_TOKEN', "")
YNAB_BUDGET_ID = os.getenv('YNAB_BUDGET_ID', "")
YNAB_ACCOUNT_ID = os.getenv('YNAB_ACCOUNT_ID', "")

APP_STATE_FILE = 'app_state.json'

def save_app_state(app_state):
    with open(APP_STATE_FILE, 'w') as f:
        json.dump(app_state, f)

def load_app_state():
    if not os.path.exists(APP_STATE_FILE):
        return {}
    with open(APP_STATE_FILE, 'r') as f:
        return json.load(f)

def fetch_up_bank_transactions(client, since):
    print("Fetching transactions from Up Bank")
    up_spending_account = client.account(account_id=UP_BANK_ACCOUNT_ID)
    transactions = list(up_spending_account.transactions(since=since))
    print(transactions)
    return transactions

def transform_transactions(transactions):
    print("Transforming transactions")
    transaction_list = []
    for transaction in transactions:
        print(f"Input: {transaction}")
        transaction_data = {
            'date': transaction.created_at,
            'amount': transaction.amount_in_base_units * 10,  # YNAB uses milliunits
            'payee_name': transaction.description,
            'memo': transaction.raw_text,
            'cleared': 'cleared' if transaction.status == 'SETTLED' else 'uncleared'
        }
        transaction_list.append(transaction_data)
        print(f"Output: {transaction_data}")
    print("Transformation complete")
    return transaction_list

def import_to_ynab(api_instance, transactions):
    print("Importing transactions")
    ynab_transactions = []
    for transaction in transactions:
        ynab_transaction = SaveTransaction(
            account_id=YNAB_ACCOUNT_ID,
            date=transaction['date'].date(),
            amount=transaction['amount'],
            payee_name=transaction['payee_name'],
            memo=transaction['memo'],
            cleared=transaction['cleared']
        )
        ynab_transactions.append(ynab_transaction)
    
    #transactions_wrapper = [SaveTransactionWrapper(transaction=tx) for tx in ynab_transactions]
    transactions_wrapper = SaveTransactionsWrapper(transactions=ynab_transactions)
    api_instance.create_transaction(YNAB_BUDGET_ID, transactions_wrapper)

def main():
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
    app_state = load_app_state()
    # Determine last imported transaction date in YNAB
    last_transaction_dt = datetime.fromisoformat(app_state.get('last_transaction_dt'))
    print(f"Last transaction datetime: {last_transaction_dt}")

    # Fetch and transform transactions
    transactions = fetch_up_bank_transactions(up_client, last_transaction_dt)
    transformed_transactions = transform_transactions(transactions)
    
    # Import transactions into YNAB
    import_to_ynab(ynab_instance, transformed_transactions)

    # Save the new last transaction date
    if transactions:
        last_transaction_dt = max(t.created_at for t in transactions)
        # add 1s to the last transaction date to avoid importing the same transaction again
        last_transaction_dt += timedelta(seconds=1)
        app_state['last_transaction_dt'] = last_transaction_dt.isoformat()
        save_app_state(app_state)


if __name__ == '__main__':
    main()
