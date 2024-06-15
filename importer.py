import os
from upbankapi import Client as UpBankClient
import ynab_api
from ynab_api.api.transactions_api import TransactionsApi, TransactionsImportResponse
from ynab_api.model.transaction_detail import TransactionDetail

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get API tokens and IDs from environment variables
UP_BANK_API_TOKEN = os.getenv('UP_BANK_API_TOKEN', "")
YNAB_API_TOKEN = os.getenv('YNAB_API_TOKEN', "")
YNAB_BUDGET_ID = os.getenv('YNAB_BUDGET_ID', "")
YNAB_ACCOUNT_ID = os.getenv('YNAB_ACCOUNT_ID', "")

def fetch_up_bank_transactions(client):
    print("Fetching transactions from Up Bank")
    transactions = client.transactions.list()
    print(transactions)
    return transactions

def transform_transactions(transactions):
    print("Transforming transactions")
    transaction_list = []
    for transaction in transactions:
        print(f"Input: {transaction}")
        transaction_data = {
            'date': transaction.attributes.created_at[:10],
            'amount': int(float(transaction.attributes.amount.value) * 1000),  # YNAB uses milliunits
            'payee_name': transaction.attributes.description,
            'memo': transaction.attributes.raw_text,
            'cleared': 'cleared' if transaction.attributes.status == 'SETTLED' else 'uncleared'
        }
        transaction_list.append(transaction_data)
        print(f"Output: {transaction_data}")
    print("Transformation complete")
    return transaction_list

def import_to_ynab(api_instance, transactions):
    print("Importing transactions")
    for transaction in transactions:
        print(f"Transaction: {transaction}")
        ynab_transaction = TransactionDetail(
            account_id=YNAB_ACCOUNT_ID,
            date=transaction['date'],
            amount=transaction['amount'],
            payee_name=transaction['payee_name'],
            memo=transaction['memo'],
            cleared=transaction['cleared']
        )
        tx_import_response = api_instance.create_transaction(YNAB_BUDGET_ID, {"transaction": ynab_transaction})
        print(tx_import_response)

def main():
    # Initialize Up Bank client
    up_client = UpBankClient(token=UP_BANK_API_TOKEN)
    
    # Initialize YNAB client
    configuration = ynab_api.Configuration()
    configuration.api_key['bearer'] = YNAB_API_TOKEN
    # Create an instance of the API class
    api_client = ynab_api.ApiClient(configuration)
    ynab_instance = TransactionsApi(api_client)
    
    # Fetch and transform transactions
    transactions = fetch_up_bank_transactions(up_client)
    transformed_transactions = transform_transactions(transactions)
    
    # Import transactions into YNAB
    import_to_ynab(ynab_instance, transformed_transactions)

if __name__ == '__main__':
    main()
