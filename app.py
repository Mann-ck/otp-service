from flask import Flask, render_template, request, session, jsonify, redirect
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from flask_session import Session
from flask_cors import CORS
import random
import time
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'hello@123'
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)
CORS(app)

# Load Twilio credentials
ACCOUNT_SID = os.getenv('ACCOUNT_SID')
AUTH_TOKEN = os.getenv('AUTH_TOKEN')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER')

# Validate credentials early
if not all([ACCOUNT_SID, AUTH_TOKEN, TWILIO_PHONE_NUMBER]):
    print("❌ Missing Twilio credentials. Please check your .env file.")
    sys.exit(1)

twilio_client = Client(ACCOUNT_SID, AUTH_TOKEN)

def generate_otp():
    return ''.join(random.choices('0123456789', k=6))

def send_otp(phone_number, otp):
    try:
        if not phone_number.startswith('+'):
            phone_number = '+91' + phone_number.strip()  # Assuming Indian numbers
        message = twilio_client.messages.create(
            from_=TWILIO_PHONE_NUMBER,
            to=phone_number,
            body=f"Your OTP is {otp}"
        )
        print("✅ OTP sent. Message SID:", message.sid)
        return message.sid
    except TwilioRestException as e:
        print("❌ Twilio Error:", str(e))
        return None
    except Exception as ex:
        print("❌ General error sending OTP:", str(ex))
        return None

@app.route('/')
def index():
    verified_name = request.args.get('verified_name')
    if not verified_name:
        return redirect("http://localhost:8501")  # Assumes Streamlit is running
    session['verified_name'] = verified_name.strip()
    return render_template('index.html')

@app.route('/getOTP', methods=['POST'])
def get_otp():
    try:
        phone_number = request.form.get('phone-number', '').strip()
        name_entered = request.form.get('name', '').strip()
        verified_name = session.get('verified_name', '').strip()

        if not phone_number or not name_entered:
            return jsonify({'error': 'Name and phone number are required'}), 400

        if verified_name.lower() != name_entered.lower():
            return jsonify({'error': 'Name does not match verified identity'}), 403

        otp = generate_otp()
        message_sid = send_otp(phone_number, otp)

        if message_sid:
            session['otp_code'] = otp
            session['otp_time'] = time.time()
            session['user_data'] = {
                'name': name_entered,
                'prn': request.form.get('prn'),
                'email': request.form.get('email'),
                'branch': request.form.get('branch'),
                'phone-number': phone_number
            }
            return jsonify({'status': 'OTP sent'})  # Frontend should redirect on this
        else:
            return jsonify({'error': 'Failed to send OTP'}), 500

    except Exception as e:
        print("❌ Exception in get_otp:", str(e))
        return jsonify({'error': 'Internal Server Error'}), 500

@app.route('/verify')
def verify_page():
    return render_template('verify.html')

@app.route('/verifyOTP', methods=['POST'])
def verify_otp():
    try:
        code = request.form.get('verification-code', '').strip()
        if not code:
            return jsonify({'error': 'Verification code required'}), 400

        stored_code = session.get('otp_code')
        if not stored_code:
            return jsonify({'error': 'OTP expired or not found'}), 403

        if code == stored_code:
            if time.time() - session.get('otp_time', 0) > 120:
                return jsonify({'error': 'OTP expired'}), 401
            return jsonify({'status': 'success', 'user': session.get('user_data')})
        else:
            return jsonify({'error': 'Incorrect OTP'}), 401

    except Exception as e:
        print("❌ Exception in verify_otp:", str(e))
        return jsonify({'error': 'Internal Server Error'}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
