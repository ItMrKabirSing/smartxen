from flask import Flask, request, jsonify, render_template
import re
import random
import requests
import pycountry

app = Flask(__name__)

def is_amex_bin(bin_str):
    clean_bin = bin_str.replace('x', '').replace('X', '')
    if len(clean_bin) >= 2:
        return clean_bin[:2] in ['34', '37']
    return False

def luhn_algorithm(card_number):
    digits = [int(d) for d in str(card_number) if d.isdigit()]
    if not digits or len(digits) < 13:
        return False
    checksum = 0
    for i, digit in enumerate(reversed(digits)):
        if i % 2 == 1:
            doubled = digit * 2
            if doubled > 9:
                doubled = doubled // 10 + doubled % 10
            checksum += doubled
        else:
            checksum += digit
    return checksum % 10 == 0

def calculate_luhn_check_digit(partial_card_number):
    digits = [int(d) for d in str(partial_card_number) if d.isdigit()]
    if not digits:
        return 0
    checksum = 0
    for i, digit in enumerate(reversed(digits)):
        if i % 2 == 0:
            doubled = digit * 2
            if doubled > 9:
                doubled = doubled // 10 + doubled % 10
            checksum += doubled
        else:
            checksum += digit
    check_digit = (10 - (checksum % 10)) % 10
    return check_digit

def generate_credit_card(bin, amount, month=None, year=None, cvv=None):
    cards = []
    is_amex = is_amex_bin(bin)
    target_length = 15 if is_amex else 16
    cvv_length = 4 if is_amex else 3
    bin_digits = re.sub(r'[^0-9]', '', bin)
    if len(bin_digits) > target_length:
        return []
    for _ in range(amount):
        card_body = bin_digits
        remaining_digits = target_length - len(card_body) - 1
        if remaining_digits < 0:
            continue
        for _ in range(remaining_digits):
            card_body += str(random.randint(0, 9))
        check_digit = calculate_luhn_check_digit(card_body)
        card_number = card_body + str(check_digit)
        if not luhn_algorithm(card_number):
            continue
        card_month = month if month is not None else f"{random.randint(1, 12):02d}"
        card_year = year if year is not None else str(random.randint(2025, 2035))
        card_cvv = cvv if cvv is not None else ''.join([str(random.randint(0, 9)) for _ in range(cvv_length)])
        formatted_card = f"{card_number}|{card_month}|{card_year}|{card_cvv}"
        cards.append(formatted_card)
    return cards

def generate_custom_cards(bin, amount, month=None, year=None, cvv=None):
    cards = []
    is_amex = is_amex_bin(bin)
    target_length = 15 if is_amex else 16
    cvv_length = 4 if is_amex else 3
    for _ in range(amount):
        while True:
            card_body = ''.join([str(random.randint(0, 9)) if char.lower() == 'x' else char for char in bin])
            card_body_digits = re.sub(r'[^0-9]', '', card_body)
            remaining_digits = target_length - len(card_body_digits) - 1
            if remaining_digits < 0:
                break
            card_body_digits += ''.join([str(random.randint(0, 9)) for _ in range(remaining_digits)])
            check_digit = calculate_luhn_check_digit(card_body_digits)
            card_number = card_body_digits + str(check_digit)
            if luhn_algorithm(card_number):
                card_month = month if month is not None else f"{random.randint(1, 12):02d}"
                card_year = year if year is not None else str(random.randint(2025, 2035))
                card_cvv = cvv if cvv is not None else ''.join([str(random.randint(0, 9)) for _ in range(cvv_length)])
                cards.append(f"{card_number}|{card_month}|{card_year}|{card_cvv}")
                break
    return cards

def get_flag(country_code):
    try:
        country = pycountry.countries.get(alpha_2=country_code)
        if not country:
            raise ValueError("Invalid country code")
        country_name = country.name
        flag_emoji = chr(0x1F1E6 + ord(country_code[0]) - ord('A')) + chr(0x1F1E6 + ord(country_code[1]) - ord('A'))
        return country_name, flag_emoji
    except Exception:
        return "Unknown Country", "🇺🇳"

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
                country_code = data.get('Country', {}).get('A2', 'UN')
                country_name, flag_emoji = get_flag(country_code)
                scheme = data.get('Scheme', 'Unknown Scheme')
                card_type = data.get('Type', 'Unknown Type')
                bin_info = f"{scheme} - {card_type}"
                return {
                    'Bank': bank,
                    'Country': f"{country_name} {flag_emoji}",
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

def parse_input(bin, month=None, year=None, cvv=None, amount=10):
    parsed_bin = None
    parsed_month = None
    parsed_year = None
    parsed_cvv = None
    parsed_amount = amount if isinstance(amount, int) and 1 <= amount <= 9999 else 10
    if not bin:
        return None, None, None, None, None
    bin = bin.strip()
    match = re.match(
        r'^(\d*[xX]*\d*)(?:[|:/](xx|\d{2}|xxx))?(?:[|:/](xx|\d{2,4}|xxxx))?(?:[|:/](xxx|\d{3,4}|xxxx))?$',
        bin, re.IGNORECASE
    )
    if match:
        parsed_bin, parsed_month, parsed_year, parsed_cvv = match.groups()[:4]
        if parsed_bin:
            clean_bin = re.sub(r'[^0-9xX]', '', parsed_bin)
            bin_length = len(re.sub(r'[^0-9]', '', clean_bin))
            if bin_length < 6 or bin_length > 15:
                return None, None, None, None, None
            parsed_bin = clean_bin
    if not parsed_bin:
        clean_bin = re.sub(r'[^0-9xX]', '', bin)
        bin_length = len(re.sub(r'[^0-9]', '', clean_bin))
        if 6 <= bin_length <= 15:
            parsed_bin = clean_bin
        else:
            return None, None, None, None, None
    if month and month.lower() in ['xx', 'xxx']:
        parsed_month = None
    elif month and month.isdigit() and len(month) == 2:
        month_val = int(month)
        if 1 <= month_val <= 12:
            parsed_month = f"{month_val:02d}"
    elif parsed_month and parsed_month.lower() in ['xx', 'xxx']:
        parsed_month = None
    elif parsed_month and parsed_month.isdigit() and len(parsed_month) == 2:
        month_val = int(parsed_month)
        if 1 <= month_val <= 12:
            parsed_month = f"{month_val:02d}"
        else:
            return None, None, None, None, None
    if year and year.lower() in ['xx', 'xxxx']:
        parsed_year = None
    elif year and year.isdigit():
        if len(year) == 2:
            year_int = int(year)
            if year_int >= 25:
                parsed_year = f"20{year}"
            else:
                return None, None, None, None, None
        elif len(year) == 4:
            year_int = int(year)
            if 2025 <= year_int <= 2099:
                parsed_year = year
            else:
                return None, None, None, None, None
    elif parsed_year and parsed_year.lower() in ['xx', 'xxxx']:
        parsed_year = None
    elif parsed_year and parsed_year.isdigit():
        if len(parsed_year) == 2:
            year_int = int(parsed_year)
            if year_int >= 25:
                parsed_year = f"20{parsed_year}"
            else:
                return None, None, None, None, None
        elif len(parsed_year) == 4:
            year_int = int(parsed_year)
            if 2025 <= year_int <= 2099:
                parsed_year = parsed_year
            else:
                return None, None, None, None, None
    if cvv and cvv.lower() in ['xxx', 'xxxx']:
        parsed_cvv = None
    elif cvv and cvv.isdigit():
        parsed_cvv = cvv
    elif parsed_cvv and parsed_cvv.lower() in ['xxx', 'xxxx']:
        parsed_cvv = None
    elif parsed_cvv and parsed_cvv.isdigit():
        parsed_cvv = parsed_cvv
    return parsed_bin, parsed_month, parsed_year, parsed_cvv, parsed_amount

@app.route('/', methods=['GET'])
def status():
    return render_template('status.html')

@app.route('/gen', methods=['GET'])
def generate_cards():
    bin = request.args.get('bin')
    month = request.args.get('month')
    year = request.args.get('year')
    cvv = request.args.get('cvv')
    amount = request.args.get('amount', default=10, type=int)
    CC_GEN_LIMIT = 2000
    if not bin:
        return jsonify({
            "status": "error",
            "message": "BIN parameter is required",
            "api_owner": "@ISmartCoder",
            "api_updates": "t.me/TheSmartDev"
        }), 400
    bin, month, year, cvv, amount = parse_input(bin, month, year, cvv, amount)
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
        if is_amex and len(cvv) != 4:
            return jsonify({
                "status": "error",
                "message": "Invalid CVV format: CVV must be 4 digits for AMEX",
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
