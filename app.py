from flask import Flask, render_template, request, session, jsonify
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from flask_session import Session
from flask_cors import CORS
import random
import time
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'hello@123'
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)
CORS(app)

ACCOUNT_SID = os.getenv('ACCOUNT_SID')
AUTH_TOKEN = os.getenv('AUTH_TOKEN')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER')
twilio_client = Client(ACCOUNT_SID, AUTH_TOKEN)

def generate_otp():
    return ''.join(random.choices('0123456789', k=6))

def send_otp(phone_number, otp):
    try:
        if not phone_number.startswith('+'):
            phone_number = '+' + phone_number.strip()
        message = twilio_client.messages.create(
            from_=TWILIO_PHONE_NUMBER,
            to=phone_number,
            body=f"Your OTP is {otp}"
        )
        return message.sid
    except TwilioRestException as e:
        print(f"Twilio error: {e}")
        return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/getOTP', methods=['POST'])
def get_otp():
    phone_number = request.form.get('phone-number')
    if not phone_number:
        return jsonify({'error': 'Phone number required'}), 400

    otp = generate_otp()
    message_sid = send_otp(phone_number, otp)
    if message_sid:
        session['otp_code'] = otp
        session['otp_time'] = time.time()
        session['user_data'] = {
            'name': request.form.get('name'),
            'prn': request.form.get('prn'),
            'email': request.form.get('email'),
            'branch': request.form.get('branch'),
            'phone-number': phone_number
        }
        return jsonify({'status': 'OTP sent'})
    else:
        return jsonify({'error': 'Failed to send OTP'}), 500

@app.route('/verifyOTP', methods=['POST'])
def verify_otp():
    code = request.form.get('verification-code')
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

if __name__ == '__main__':
    app.run(debug=True)
