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
    if len(bin_digits) >= target_length:
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
    bin_digits = re.sub(r'[^0-9]', '', bin)
    if len(bin_digits) >= target_length:
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

def parse_input(user_input, amount=10):
    bin = None
    month = None
    year = None
    cvv = None
    parsed_amount = amount
    if not user_input:
        return None, None, None, None, None
    digits_x_pattern = r'(?:[0-9xX][a-zA-Z0-9!@#$%^&*()_+\-=\[\]{};:\'",.<>/?\\|]*)+(?:[|:/][\d]{2}|xx|xxx|xxxx]+(?:[|:/][\d]{2,4}|xx|xxx|xxxx]+(?:[|:/][\d]{3,4}|xxx|xxxx|rnd]+)?)?)?'
    matches = re.findall(digits_x_pattern, user_input, re.IGNORECASE)
    if matches:
        for match in matches:
            parts = re.split(r'[|:/]', match)
            bin_part = ''.join(filter(lambda x: x.isdigit() or x in 'xX', parts[0]))
            digits_only = re.sub(r'[^0-9]', '', bin_part)
            if 6 <= len(digits_only) <= 16:
                if len(parts) > 1:
                    full_match = bin_part + '|' + '|'.join(parts[1:])
                    bin = full_match
                else:
                    bin = digits_only
                break
    if not bin:
        return None, None, None, None, None
    parts = re.split(r'[|:/]', bin)
    bin_part = parts[0] if parts else ""
    digits_only = re.sub(r'[^0-9xX]', '', bin_part)
    if digits_only:
        if 6 <= len(re.sub(r'[^0-9]', '', digits_only)) <= 16:
            bin = digits_only
        else:
            return None, None, None, None, None
    else:
        return None, None, None, None, None
    if len(parts) > 1:
        if parts[1].lower() == 'xx':
            month = None
        elif parts[1].isdigit() and len(parts[1]) == 2:
            month_val = int(parts[1])
            if 1 <= month_val <= 12:
                month = f"{month_val:02d}"
    if len(parts) > 2:
        if parts[2].lower() in ['xx', 'xxxx']:
            year = None
        elif parts[2].isdigit():
            year_str = parts[2]
            if len(year_str) == 2:
                year_int = int(year_str)
                if year_int >= 25:
                    year = f"20{year_str}"
            elif len(year_str) == 4:
                year_int = int(year_str)
                if 2025 <= year_int <= 2099:
                    year = year_str
    if len(parts) > 3 and parts[3]:
        if parts[3].lower() in ['xxx', 'xxxx', 'rnd']:
            cvv = None
        elif parts[3].isdigit():
            cvv = parts[3]
    return bin, month, year, cvv, parsed_amount

@app.route('/', methods=['GET'])
def status():
    return render_template('status.html')

@app.route('/gen', methods=['GET'])
def generate_cards():
    CC_GEN_LIMIT = 2000
    bin = request.args.get('bin')
    month = request.args.get('month')
    year = request.args.get('year')
    cvv = request.args.get('cvv')
    amount = request.args.get('amount', default=10, type=int)
    if not bin:
        return jsonify({
            "status": "error",
            "message": "BIN parameter is required",
            "api_owner": "@ISmartCoder",
            "api_updates": "t.me/TheSmartDev"
        }), 400
    if amount < 1 or amount > CC_GEN_LIMIT:
        return jsonify({
            "status": "error",
            "message": f"Invalid amount: Must be between 1 and {CC_GEN_LIMIT}",
            "api_owner": "@ISmartCoder",
            "api_updates": "t.me/TheSmartDev"
        }), 400
    user_input = bin
    if month:
        user_input += f"|{month}"
    if year:
        user_input += f"|{year}"
    if cvv:
        user_input += f"|{cvv}"
    bin, month, year, cvv, parsed_amount = parse_input(user_input, amount)
    if not bin:
        return jsonify({
            "status": "error",
            "message": "Invalid BIN: Must be 6-15 digits or up to 16 digits with 'x'",
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
        elif not is_amex and len(cvv) != 3:
            return jsonify({
                "status": "error",
                "message": "Invalid CVV format: CVV must be 3 digits for non-AMEX",
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/TheSmartDev"
            }), 400
    cards = generate_credit_card(bin, parsed_amount, month, year, cvv)
    bin_info = get_bin_info(bin)
    return jsonify({
        "status": "success",
        "bin": bin,
        "amount": parsed_amount,
        "cards": cards,
        "Bank": bin_info['Bank'],
        "Country": bin_info['Country'],
        "BIN Info": bin_info['BIN Info'],
        "api_owner": "@ISmartCoder",
        "api_updates": "t.me/TheSmartDev"
    }), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
