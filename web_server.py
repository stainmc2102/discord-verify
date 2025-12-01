from flask import Flask, render_template, request, redirect, url_for, session
import os
import requests
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SESSION_SECRET', 'default-secret-key')

RECAPTCHA_SITE_KEY = os.getenv('RECAPTCHA_SITE_KEY', '')
RECAPTCHA_SECRET_KEY = os.getenv('RECAPTCHA_SECRET_KEY', '')

verified_users = set()
user_info_store = {}
public_url = None

def get_ngrok_url():
    return public_url

def verify_recaptcha(response_token):
    if not RECAPTCHA_SECRET_KEY:
        return True

    data = {
        'secret': RECAPTCHA_SECRET_KEY,
        'response': response_token
    }

    try:
        response = requests.post('https://www.google.com/recaptcha/api/siteverify', data=data)
        result = response.json()
        return result.get('success', False)
    except Exception as e:
        print(f"Lỗi xác minh reCAPTCHA: {e}")
        return False

@app.route('/')
def home():
    return redirect(url_for('verify_page'))

@app.route('/verify')
def verify_page():
    return render_template('verify.html', 
                         site_key=RECAPTCHA_SITE_KEY,
                         user_id=None,
                         user_info=None,
                         error=None,
                         success=False)

@app.route('/verify/<verify_key>')
def verify_user(verify_key):
    user_info = user_info_store.get(verify_key, None)

    if verify_key in verified_users:
        return render_template('verify.html',
                             site_key=RECAPTCHA_SITE_KEY,
                             user_id=verify_key,
                             user_info=user_info,
                             error=None,
                             success=True,
                             already_verified=True)

    return render_template('verify.html',
                         site_key=RECAPTCHA_SITE_KEY,
                         user_id=verify_key,
                         user_info=user_info,
                         error=None,
                         success=False)

@app.route('/verify/<verify_key>', methods=['POST'])
def process_verification(verify_key):
    user_info = user_info_store.get(verify_key, None)
    recaptcha_response = request.form.get('g-recaptcha-response', '')

    if not recaptcha_response:
        return render_template('verify.html',
                             site_key=RECAPTCHA_SITE_KEY,
                             user_id=verify_key,
                             user_info=user_info,
                             error="Vui lòng hoàn thành captcha.",
                             success=False)

    if verify_recaptcha(recaptcha_response):
        verified_users.add(verify_key)
        print(f"Người dùng {verify_key} đã xác minh thành công!")

        return render_template('verify.html',
                             site_key=RECAPTCHA_SITE_KEY,
                             user_id=verify_key,
                             user_info=user_info,
                             error=None,
                             success=True)
    else:
        return render_template('verify.html',
                             site_key=RECAPTCHA_SITE_KEY,
                             user_id=verify_key,
                             user_info=user_info,
                             error="Xác minh captcha thất bại. Vui lòng thử lại.",
                             success=False)

@app.route('/status/<verify_key>')
def check_status(verify_key):
    is_verified = verify_key in verified_users
    return {'verify_key': verify_key, 'verified': is_verified}

def run_flask_app():
    global public_url

    configured_url = os.getenv('PUBLIC_URL')

    if configured_url:
        public_url = configured_url.rstrip('/')
        print(f"Sử dụng URL công khai: {public_url}")
    else:
        try:
            from pyngrok import ngrok, conf

            home_dir = os.path.expanduser("~")
            ngrok_dir = os.path.join(home_dir, "ngrok_bin")
            ngrok_path = os.path.join(ngrok_dir, "ngrok")
            config_path = os.path.join(ngrok_dir, "ngrok.yml")

            os.makedirs(ngrok_dir, exist_ok=True)

            pyngrok_config = conf.PyngrokConfig(
                ngrok_path=ngrok_path,
                config_path=config_path
            )
            conf.set_default(pyngrok_config)

            ngrok_token = os.getenv('NGROK_AUTH_TOKEN')
            if ngrok_token:
                ngrok.set_auth_token(ngrok_token, pyngrok_config=pyngrok_config)

            tunnel = ngrok.connect("3000", pyngrok_config=pyngrok_config)
            public_url = tunnel.public_url
            print(f"Đường hầm ngrok đã mở tại: {public_url}")
        except Exception as e:
            print(f"Lỗi khởi động ngrok: {e}")
            print("Tip: Đặt PUBLIC_URL trong biến môi trường nếu hosting không hỗ trợ ngrok")
            public_url = None

    app.run(host='0.0.0.0', port=3000, debug=False, use_reloader=False)

if __name__ == '__main__':
    run_flask_app()
