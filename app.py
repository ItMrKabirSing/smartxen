from flask import Flask, request, jsonify, render_template
import re
import random
import requests

app = Flask(__name__)

def is_amex_bin(bin_str):
    clean_bin = bin_str.replace('x', '').replace('X', '')
    if len(clean_bin) >= 2:
        return clean_bin[:2] in ['34', '37']
    return False

def luhn_algorithm(card_number):
    def digits_of(n):
        return [int(d) for d in str(n)]
    digits = digits_of(card_number)
    odd_digits = digits[-1::-2]
    even_digits = digits[-2::-2]
    checksum = sum(odd_digits)
    for d in even_digits:
        checksum += sum(digits_of(d * 2))
    return checksum % 10 == 0

def calculate_luhn_check_digit(card_number):
    def digits_of(n):
        return [int(d) for d in str(n)]
    digits = digits_of(card_number)
    odd_digits = digits[-1::-2]
    even_digits = digits[-2::-2]
    checksum = sum(odd_digits)
    for d in even_digits:
        checksum += sum(digits_of(d * 2))
    return (10 - (checksum % 10)) % 10

def generate_credit_card(bin, amount, month=None, year=None, cvv=None):
    cards = []
    is_amex = is_amex_bin(bin)
    target_length = 14 if is_amex else 15
    cvv_length = 4 if is_amex else 3
    for _ in range(amount):
        while True:
            card_body = ''.join([str(random.randint(0, 9)) if char.lower() == 'x' else char for char in bin])
            remaining_digits = target_length - len(card_body)
            card_body += ''.join([str(random.randint(0, 9)) for _ in range(remaining_digits)])
            check_digit = calculate_luhn_check_digit(card_body)
            card_number = card_body + str(check_digit)
            if luhn_algorithm(card_number):
                card_month = month or f"{random.randint(1, 12):02}"
                card_year = year or random.randint(2025, 2035)
                card_cvv = cvv or ''.join([str(random.randint(0, 9)) for _ in range(cvv_length)])
                cards.append(f"{card_number}|{card_month}|{card_year}|{card_cvv}")
                break
    return cards

def generate_custom_cards(bin, amount, month=None, year=None, cvv=None):
    cards = []
    is_amex = is_amex_bin(bin)
    target_length = 14 if is_amex else 15
    cvv_length = 4 if is_amex else 3
    for _ in range(amount):
        while True:
            card_body = bin.replace('x', '').replace('X', '')
            remaining_digits = target_length - len(card_body)
            card_body += ''.join([str(random.randint(0, 9)) for _ in range(remaining_digits)])
            check_digit = calculate_luhn_check_digit(card_body)
            card_number = card_body + str(check_digit)
            if luhn_algorithm(card_number):
                card_month = month or f"{random.randint(1, 12):02}"
                card_year = year or random.randint(2025, 2035)
                card_cvv = cvv or ''.join([str(random.randint(0, 9)) for _ in range(cvv_length)])
                cards.append(f"{card_number}|{card_month}|{card_year}|{card_cvv}")
                break
    return cards

def get_bin_info(bin):
    clean_bin = bin.replace('x', '').replace('X', '')[:6]
    try:
        response = requests.get(
            f'https://data.handyapi.com/bin/{clean_bin}',
            headers={'x-api-key': 'HAS-0YSb780tq6PMVx7s6jmpQU'}
        )
        if response.status_code == 200:
            data = response.json()
            if data.get('Status') == 'SUCCESS':
                bank = data.get('Issuer', 'Unknown Bank')
                country = data.get('Country', {}).get('Name', 'Unknown Country')
                country_flag = '🇺🇳' if country == 'Unknown Country' else '🇺🇸' if country == 'United States' else data.get('Country', {}).get('A2', 'UN').lower()
                scheme = data.get('Scheme', 'Unknown Scheme')
                card_type = data.get('Type', 'Unknown Type')
                bin_info = f"{scheme} - {card_type}"
                return {
                    'Bank': bank,
                    'Country': f"{country} {country_flag}",
                    'BIN Info': bin_info
                }
        return {
            'Bank': 'Unknown Bank',
            'Country': 'Unknown Country 🇺🇳',
            'BIN Info': 'Unknown Scheme - Unknown Type'
        }
    except requests.RequestException:
        return {
            'Bank': 'Unknown Bank',
            'Country': 'Unknown Country 🇺🇳',
            'BIN Info': 'Unknown Scheme - Unknown Type'
        }

def parse_input(user_input):
    bin = None
    month = None
    year = None
    cvv = None
    amount = 10
    match = re.match(
        r"^([0-9xX]{6,16})"
        r"(?:[|:/](\d{2}))?"
        r"(?:[|:/](\d{2,4}))?"
        r"(?:[|:/]([0-9]{3,4}|xxx|rnd)?)?"
        r"(?:\s+(\d{1,7}))?$",
        user_input.strip(), re.IGNORECASE
    )
    if match:
        bin, month, year, cvv, amount = match.groups()
        if bin:
            has_x = 'x' in bin.lower()
            bin_length = len(bin)
            clean_length = len(bin.replace('x','').replace('X',''))
            if clean_length < 6:
                return None, None, None, None, None
            if has_x and bin_length > 16:
                return None, None, None, None, None
            if not has_x and (bin_length < 6 or bin_length > 15):
                return None, None, None, None, None
        if cvv and cvv.lower() not in ['xxx', 'rnd']:
            is_amex = is_amex_bin(bin) if bin else False
            expected_cvv_length = 4 if is_amex else 3
            if len(cvv) != expected_cvv_length:
                return None, None, None, None, None
        if cvv and cvv.lower() in ['xxx', 'rnd'] or cvv is None:
            cvv = None
        if year and len(year) == 2:
            year = f"20{year}"
        amount = int(amount) if amount else 10
    return bin, month, year, cvv, amount

@app.route('/', methods=['GET'])
def status():
    return render_template('status.html')

@app.route('/gen', methods=['GET'])
def generate_cards():
    bin = request.args.get('bin')
    amount = request.args.get('amount', default=10, type=int)
    CC_GEN_LIMIT = 2000

    if not bin:
        return jsonify({
            "status": "error",
            "message": "BIN parameter is required",
            "api_owner": "@ISmartCoder",
            "api_updates": "t.me/TheSmartDev"
        }), 400

    bin, month, year, cvv, amount = parse_input(f"{bin} {amount}")
    if not bin:
        return jsonify({
            "status": "error",
            "message": "Invalid BIN: Must be 6-15 digits or up to 16 digits with 'x'",
            "api_owner": "@ISmartCoder",
            "api_updates": "t.me/TheSmartDev"
        }), 400

    if amount > CC_GEN_LIMIT:
        return jsonify({
            "status": "error",
            "message": "Limit exceeded",
            "api_owner": "@ISmartCoder",
            "api_updates": "t.me/TheSmartDev"
        }), 400

    if cvv is not None:
        is_amex = is_amex_bin(bin)
        expected_cvv_length = 4 if is_amex else 3
        if len(cvv) != expected_cvv_length:
            cvv_type = "4 digits for AMEX" if is_amex else "3 digits for non-AMEX"
            return jsonify({
                "status": "error",
                "message": f"Invalid CVV format: CVV must be {cvv_type}",
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/TheSmartDev"
            }), 400

    cards = generate_custom_cards(bin, amount, month, year, cvv) if 'x' in bin.lower() else generate_credit_card(bin, amount, month, year, cvv)
    bin_info = get_bin_info(bin)

    return jsonify({
        "status": "success",
        "bin": bin,
        "amount": amount,
        "cards": cards,
        "Bank": bin_info['Bank'],
        "Country": bin_info['Country'],
        "BIN Info": bin_info['BIN Info'],
        "api_owner": "@ISmartCoder",
        "api_updates": "t.me/TheSmartDev"
    }), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)