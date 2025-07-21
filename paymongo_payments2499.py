# Trigger redeploy on Railway

from flask import Flask, request, redirect, jsonify
import requests
import os
import gspread
from datetime import datetime
import json

# Triggering redeploy on Railway

app = Flask(__name__)

# PayMongo Secret Key (set as environment variable for security)
PAYMONGO_SECRET_KEY = os.environ.get('PAYMONGO_SECRET_KEY')
# Google Sheets credentials file path (set as environment variable)
GOOGLE_SHEETS_CREDS = os.environ.get('GOOGLE_SHEETS_CREDS', 'pmcredentials.json')
# Google Sheets spreadsheet ID
SPREADSHEET_ID = os.environ.get('SPREADSHEET_ID')

# Thank you and error page URLs
THANK_YOU_URL = 'https://www.transmutation-method.com/thank-you'
ERROR_URL = 'https://www.transmutation-method.com/payment-error'

def write_pm_credentials():
    creds_json = os.environ.get('PM_CREDENTIALS_JSON')
    if creds_json:
        with open('pmcredentials.json', 'w') as f:
            f.write(creds_json)

write_pm_credentials()

@app.route('/pay')
def pay_direct():
    amount = 249900  # ₱2,499 in centavos
    url = 'https://api.paymongo.com/v1/checkout_sessions'
    headers = {
        'accept': 'application/json',
        'content-type': 'application/json',
        'authorization': f'Basic {PAYMONGO_SECRET_KEY}'
    }
    description = "Transmutation Method Checkout: Grab Our Program Today for only PHP2,499 (P500 OFF)! Once you complete payment, you will be led to the link to access our modules + community!"
    data = {
        "data": {
            "attributes": {
                "send_email_receipt": True,
                "show_description": True,
                "show_line_items": False,
                "line_items": [
                    {
                        "currency": "PHP",
                        "amount": amount,
                        "name": "Transmutation Method",
                        "quantity": 1,
                        "description": description
                    }
                ],
                "payment_method_types": [
                    "card", "gcash", "grab_pay", "paymaya", "atome"
                ],
                "description": description,
                "reference_number": None,
                "success_url": THANK_YOU_URL,
                "cancel_url": ERROR_URL
            }
        }
    }
    response = requests.post(url, json=data, headers=headers)
    if response.status_code in (200, 201):
        checkout_session = response.json()['data']
        checkout_url = checkout_session['attributes']['checkout_url']
        print("Redirecting to PayMongo checkout URL:", checkout_url)
        return redirect(checkout_url)
    else:
        print("PayMongo Checkout API error:", response.status_code, response.text)
        return redirect(ERROR_URL)

@app.route('/webhook', methods=['POST'])
def paymongo_webhook():
    write_pm_credentials()  # Ensure credentials file exists
    try:
        payload = request.json
        print("Webhook payload:", payload)
        data = payload.get('data') if isinstance(payload, dict) else None
        attributes = data.get('attributes') if isinstance(data, dict) else None
        print("Attributes:", attributes)
        event_type = attributes.get('type', '') if isinstance(attributes, dict) else ''
        payment_data = attributes.get('data') if isinstance(attributes, dict) else None
        print("Payment data:", payment_data)
        if event_type == 'payment.paid' and isinstance(payment_data, dict):
            log_payment_to_sheets(payment_data.get('attributes', {}))
    except Exception as e:
        print(f"Webhook error: {e}")
    return jsonify({'status': 'ok'})  # Always return 200

def log_payment_to_sheets(attributes):
    try:
        if not attributes:
            print("No payment attributes received.")
            return
        if not SPREADSHEET_ID:
            print("SPREADSHEET_ID environment variable is not set.")
            return
        client = gspread.service_account(filename=GOOGLE_SHEETS_CREDS)
        sheet = client.open_by_key(SPREADSHEET_ID).sheet1

        billing = attributes.get('billing', {})
        name = billing.get('name', '')
        email = billing.get('email', '')
        phone = billing.get('phone', '')
        amount = attributes.get('amount', 0) / 100
        status = attributes.get('status', '')
        paid_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        payment_method = attributes.get('source', {}).get('type', '')
        last4 = attributes.get('source', {}).get('last4', '')
        payment_id = attributes.get('id', '')
        description = attributes.get('description', '')
        reference_number = attributes.get('external_reference_number', '')
        created_at = attributes.get('created_at', '')
        statement_descriptor = attributes.get('statement_descriptor', '')

        sheet.append_row([
            name, email, phone, amount, status, paid_at, payment_method, last4,
            payment_id, description, reference_number, created_at, statement_descriptor
        ])
    except Exception as e:
        print(f"Failed to log payment: {e}")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
