# Trigger redeploy on Railway

from flask import Flask, render_template_string, request, redirect, url_for, jsonify
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

# HTML payment form template
PAYMENT_FORM_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>Transmutation Method - Payment</title>
    <link href="https://fonts.googleapis.com/css?family=Inter:400,500,700&display=swap" rel="stylesheet">
    <style>
        body {
            font-family: 'Inter', Arial, sans-serif;
            background: #f7f9fa;
            margin: 0;
            padding: 0;
        }
        .header {
            padding: 32px 0 0 0;
            text-align: center;
        }
        .header .sub {
            color: #8b949e;
            font-size: 15px;
            margin-bottom: 4px;
        }
        .header .biz {
            font-size: 20px;
            font-weight: 500;
            color: #222;
        }
        .main-container {
            display: flex;
            justify-content: center;
            align-items: flex-start;
            margin: 40px 0;
        }
        .card {
            background: #fff;
            border-radius: 12px;
            box-shadow: 0 2px 16px rgba(0,0,0,0.06);
            display: flex;
            min-width: 700px;
            max-width: 900px;
            width: 90vw;
            overflow: hidden;
        }
        .left-panel {
            flex: 1.1;
            padding: 40px 32px 40px 40px;
            border-right: 1px solid #f0f1f3;
            background: #f9fafb;
        }
        .right-panel {
            flex: 1;
            padding: 40px 40px 40px 32px;
        }
        .pay-amount-label {
            color: #8b949e;
            font-size: 16px;
            font-weight: 500;
        }
        .pay-amount {
            color: #1db954;
            font-size: 32px;
            font-weight: 700;
            margin: 8px 0 0 0;
        }
        .pay-for-label {
            color: #8b949e;
            font-size: 15px;
            margin-top: 32px;
        }
        .pay-for {
            color: #222;
            font-size: 16px;
            margin-top: 4px;
        }
        .total-row {
            margin-top: 40px;
            display: flex;
            justify-content: flex-end;
            align-items: center;
            border-top: 1px dashed #e0e0e0;
            padding-top: 18px;
        }
        .total-label {
            color: #8b949e;
            font-size: 16px;
            margin-right: 16px;
        }
        .total-amount {
            color: #222;
            font-size: 24px;
            font-weight: 700;
        }
        .form-title {
            font-size: 18px;
            font-weight: 600;
            color: #222;
            margin-bottom: 24px;
        }
        label {
            display: block;
            margin-bottom: 6px;
            font-size: 15px;
            color: #8b949e;
            font-weight: 500;
        }
        input[type="text"], input[type="email"] {
            width: 100%;
            padding: 14px 12px;
            border: 1.5px solid #e0e0e0;
            border-radius: 7px;
            font-size: 16px;
            margin-bottom: 18px;
            background: #f9fafb;
            color: #222;
            transition: border 0.2s;
        }
        input[type="text"]:focus, input[type="email"]:focus {
            border: 1.5px solid #1db954;
            outline: none;
        }
        button {
            width: 100%;
            padding: 15px;
            background-color: #1db954;
            color: white;
            border: none;
            border-radius: 7px;
            font-size: 18px;
            font-weight: 600;
            cursor: pointer;
            transition: background-color 0.2s;
            margin-top: 10px;
        }
        button:hover {
            background-color: #169c43;
        }
        @media (max-width: 900px) {
            .main-container { margin: 10px 0; }
            .card { flex-direction: column; min-width: unset; }
            .left-panel, .right-panel { padding: 32px 16px; }
            .left-panel { border-right: none; border-bottom: 1px solid #f0f1f3; }
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="sub">You are paying</div>
        <div class="biz">Miguel Ybanez Digital Marketing Services</div>
    </div>
    <div class="main-container">
        <div class="card">
            <div class="left-panel">
                <div class="pay-amount-label">Payment amount</div>
                <div class="pay-amount">₱1,499.00</div>
                <div class="pay-for-label">Payment for</div>
                <div class="pay-for" id="pay-for-summary">&mdash;</div>
                <div class="total-row">
                    <div class="total-label">Total:</div>
                    <div class="total-amount">₱1,499.00</div>
                </div>
            </div>
            <div class="right-panel">
                <div class="form-title">Enter your details</div>
                <form action="/create_payment" method="post" id="payment-form">
                    <label for="name">Full Name</label>
                    <input type="text" name="name" id="name" required placeholder="Enter your full name">
                    <label for="email">Email Address</label>
                    <input type="email" name="email" id="email" required placeholder="Enter your email address">
                    <button type="submit">Pay ₱1,499</button>
                </form>
            </div>
        </div>
    </div>
    <script>
        // Update the left panel summary with the entered name/email
        const nameInput = document.getElementById('name');
        const emailInput = document.getElementById('email');
        const payForSummary = document.getElementById('pay-for-summary');
        function updateSummary() {
            const name = nameInput.value.trim();
            const email = emailInput.value.trim();
            if (name && email) {
                payForSummary.textContent = `Payment by ${name} (${email})`;
            } else {
                payForSummary.textContent = '—';
            }
        }
        nameInput.addEventListener('input', updateSummary);
        emailInput.addEventListener('input', updateSummary);
    </script>
</body>
</html>
'''

def write_pm_credentials():
    creds_json = os.environ.get('PM_CREDENTIALS_JSON')
    if creds_json:
        with open('pmcredentials.json', 'w') as f:
            f.write(creds_json)

write_pm_credentials()

@app.route('/')
def payment_form():
    return render_template_string(PAYMENT_FORM_HTML)

@app.route('/create_payment', methods=['POST'])
def create_payment():
    name = request.form['name']
    email = request.form['email']
    amount = 149900  # Fixed amount in centavos

    # Create a checkout session with PayMongo
    url = 'https://api.paymongo.com/v1/checkout_sessions'
    headers = {
        'accept': 'application/json',
        'content-type': 'application/json',
        'authorization': f'Basic {PAYMONGO_SECRET_KEY}'
    }
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
                        "name": f"Payment by {name}",
                        "quantity": 1,
                        "description": f"Payment by {name} ({email})"
                    }
                ],
                "payment_method_types": ["card", "gcash", "grab_pay", "paymaya"],
                "description": f"Payment by {name} ({email})",
                "reference_number": None,
                "metadata": {
                    "name": name,
                    "email": email
                },
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

@app.route('/pay')
def pay_direct():
    amount = 149900  # ₱1,499 in centavos
    url = 'https://api.paymongo.com/v1/checkout_sessions'
    headers = {
        'accept': 'application/json',
        'content-type': 'application/json',
        'authorization': f'Basic {PAYMONGO_SECRET_KEY}'
    }
    description = "Transmutation Method Checkout: Grab Our Program Today for only PHP1,499 (50% OFF)! Once you complete payment, you will be led to the link to access our modules + community! Program Today At Pre-Launch Price of only PHP1,499 (50% OFF)! Once you complete payment, you will be led to the link to access our modules + community!"
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
    app.run(host='0.0.0.0', port=5000)
