from flask import Flask, request, jsonify
from flask_cors import CORS
from pywebpush import webpush, WebPushException
import os, json

app = Flask(__name__)
CORS(app)

VAPID_PRIVATE_KEY = os.environ.get('VAPID_PRIVATE_KEY')
VAPID_PUBLIC_KEY = os.environ.get('VAPID_PUBLIC_KEY')
VAPID_EMAIL = os.environ.get('VAPID_EMAIL', 'mailto:admin@rakeshmart.com')
ADMIN_SECRET = os.environ.get('ADMIN_SECRET')
TOKENS_FILE = 'admin_tokens.json'

def load_tokens():
    try:
        if os.path.exists(TOKENS_FILE):
            with open(TOKENS_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    return []

def save_tokens(tokens):
    with open(TOKENS_FILE, 'w') as f:
        json.dump(tokens, f)

# Admin ka browser subscription save karo
@app.route('/admin/register-token', methods=['POST'])
def register_admin_token():
    auth = request.headers.get('X-Auth-Key')
    if auth != ADMIN_SECRET:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.json
    sub = data.get('subscription')
    if not sub:
        return jsonify({'error': 'No subscription'}), 400
    tokens = load_tokens()
    # Duplicate endpoint hatao
    tokens = [t for t in tokens if t.get('endpoint') != sub.get('endpoint')]
    tokens.append(sub)
    save_tokens(tokens)
    print(f'Admin token registered. Total: {len(tokens)}')
    return jsonify({'success': True})

# Google Apps Script yahan call karega
@app.route('/admin/notify-order', methods=['POST'])
def notify_new_order():
    auth = request.headers.get('X-Auth-Key')
    if auth != ADMIN_SECRET:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.json
    customer_name = data.get('customerName', 'Customer')
    amount = data.get('amount', '')
    order_id = data.get('orderId', '')
    items = data.get('items', '')
    
    payload = json.dumps({
        'title': '🛒 New Order - Rakesh Mart',
        'body': f'{customer_name} ne order kiya! ₹{amount}\n{items}',
        'url': 'https://rakeshmart.github.io/rakesh_dash/',
        'orderId': order_id
    })
    
    tokens = load_tokens()
    success = 0
    valid_tokens = []
    
    for sub in tokens:
        try:
            webpush(
                subscription_info=sub,
                data=payload,
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims={"sub": VAPID_EMAIL}
            )
            success += 1
            valid_tokens.append(sub)
        except WebPushException as e:
            if '410' in str(e) or '404' in str(e):
                pass  # Expired token, hatao
            else:
                valid_tokens.append(sub)
    
    save_tokens(valid_tokens)
    print(f'Notifications sent: {success}/{len(tokens)}')
    return jsonify({'success': True, 'sent': success})

@app.route('/health', methods=['GET'])
def health():
    tokens = load_tokens()
    return jsonify({'status': 'ok', 'admin_devices': len(tokens)})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
