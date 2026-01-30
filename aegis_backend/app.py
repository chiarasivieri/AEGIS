import os
import cv2
import time
import uuid
import re
import numpy as np
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename

# IMPORTIAMO GLI ALGORITMI
from algorithms import LSBWatermark, DCTWatermark, SSWatermark, ComboWatermark

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# DATABASE SIMULATO
USERS_DB = {
    "admin":  {"pass": "admin", "code": "SUPER_USER"},
    "chiara": {"pass": "1234", "code": "USR_0001"},
    "marzia": {"pass": "1234", "code": "USR_0002"},
    "professore": {"pass": "1234", "code": "USR_9999"}
}

PENDING_DB = {} 
UPLOAD_FOLDER = 'uploads'
TEMP_FOLDER = 'uploads/temp'
RESULTS_FOLDER = 'results'

for folder in [UPLOAD_FOLDER, TEMP_FOLDER, RESULTS_FOLDER]:
    os.makedirs(folder, exist_ok=True)

app.config['TEMP_FOLDER'] = TEMP_FOLDER
app.config['RESULTS_FOLDER'] = RESULTS_FOLDER
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def get_next_user_code():
    count = len(USERS_DB) + 1
    return f"USR_{count:04d}"

# --- FUNZIONE DI RICERCA FLESSIBILE ---
def fuzzy_search_users(text):
    if not text: return False, "Sconosciuto", "Sconosciuto", ""
    
    clean_text = "".join(c for c in text if c.isprintable())
    sender = "Sconosciuto"
    receiver = "Sconosciuto"
    found = False
    
    # Cerca codici USR_xxxx
    codes = re.findall(r"USR_\d{4}|SUPER_USER", clean_text)
    
    if len(codes) >= 2:
        code1, code2 = codes[0], codes[1]
        for u, d in USERS_DB.items():
            if d['code'] == code1: sender = f"{u} ({code1})"
            if d['code'] == code2: receiver = f"{u} ({code2})"
        found = True
    elif len(codes) == 1:
        # Trovato parziale
        sender = f"Parziale: {codes[0]}"
        found = True
    elif "<->" in clean_text:
        # Trovato separatore ma codici corrotti
        sender = "Firma corrotta"
        found = True
        
    return found, sender, receiver, clean_text

# --- ROTTE ---

@app.route('/verify', methods=['POST'])
def verify_image():
    if 'image' not in request.files: return jsonify({'error': 'No file'}), 400

    file = request.files['image']
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'check_temp.png')
    file.save(filepath)

    original_img = cv2.imread(filepath)
    if original_img is None: return jsonify({'error': 'Img error'}), 400

    print(f"\n🔍 VERIFICA AVVIATA...")

    verifier = ComboWatermark()
    
    found = False
    sender = "..."
    receiver = "..."
    technique = "Nessuna firma"
    raw_sig = ""

    try:
        extracted_msg = verifier.extract(original_img)
        print(f"📄 LOG ESTRAZIONE: {extracted_msg}") # Logghiamo sempre
        
        if extracted_msg and ("USR_" in extracted_msg or "<->" in extracted_msg):
            print(f"✅ SUCCESSO! Messaggio valido identificato.")
            found, sender, receiver, raw_sig = fuzzy_search_users(extracted_msg)
            technique = "Firma Recuperata (Combo)"
        else:
            print("❌ Nessun pattern USR_ trovato nel testo estratto.")

    except Exception as e:
        print(f"Error: {e}")

    # --- IL TRUCCO È QUI: Restituiamo TUTTE le chiavi possibili ---
    # L'app vecchia cerca 'found' e 'watermark'
    # L'app nuova cerca 'verified' e 'signature'
    return jsonify({
        'verified': found,      # Nuova versione
        'found': found,         # Vecchia versione (CRUCIALE)
        'sender': sender,
        'receiver': receiver,
        'technique': technique,
        'signature': raw_sig,   # Nuova versione
        'watermark': raw_sig    # Vecchia versione (CRUCIALE)
    }), 200

@app.route('/accept_transfer', methods=['POST'])
def accept_transfer():
    rid = request.json.get('request_id')
    if rid not in PENDING_DB: return jsonify({'error': 'No req'}), 404
    
    info = PENDING_DB.pop(rid)
    
    sender_code = "UNK"
    for k,v in USERS_DB.items():
        if k == info['sender'].lower(): sender_code = v['code']
        
    receiver_code = USERS_DB[info['receiver']]['code']
    signature = f"{sender_code}<->{receiver_code}"
    
    print(f"📝 SCRITTURA: {signature}")
    
    img = cv2.imread(info['filepath'])
    # Usa l'algoritmo che hai scelto (quello che funziona)
    wm = ComboWatermark()
    watermarked_img = wm.embed(img, signature)
    
    out_filename = f"secure_{int(time.time())}.png"
    out_path = os.path.join(app.config['RESULTS_FOLDER'], out_filename)
    cv2.imwrite(out_path, watermarked_img)
    
    if os.path.exists(info['filepath']): os.remove(info['filepath'])

    return jsonify({
        'signature': signature, 
        'url': f"http://127.0.0.1:5001/results/{out_filename}"
    }), 200

# LOGIN & ALTRE ROTTE STANDARD (Invariate)
@app.route('/register', methods=['POST'])
def register():
    data = request.json
    u = data.get('username', '').strip().lower()
    if u in USERS_DB: return jsonify({'error': 'Esiste'}), 409
    code = get_next_user_code()
    USERS_DB[u] = {'pass': data.get('password'), 'code': code}
    return jsonify({'message': 'OK', 'user_code': code}), 200

@app.route('/login', methods=['POST'])
def login():
    d = request.json
    u = d.get('username', '').lower()
    if u in USERS_DB and USERS_DB[u]['pass'] == d.get('password'):
        return jsonify({'message': 'OK', 'user_code': USERS_DB[u]['code'], 'username': u}), 200
    return jsonify({'error': 'No'}), 401

@app.route('/request_transfer', methods=['POST'])
def request_transfer():
    if 'image' not in request.files: return jsonify({'error': 'No file'}), 400
    f = request.files['image']
    fname = secure_filename(f"{uuid.uuid4()}_{f.filename}")
    fpath = os.path.join(app.config['TEMP_FOLDER'], fname)
    f.save(fpath)
    
    rid = str(uuid.uuid4())
    sender = request.form.get('sender_name')
    receiver_name = request.form.get('receiver_name', '').lower()
    receiver_key = next((k for k in USERS_DB if k == receiver_name), 'admin')
    
    PENDING_DB[rid] = {
        'sender': sender, 
        'receiver': receiver_key, 
        'filepath': fpath, 
        'algo': 'COMBO'
    }
    return jsonify({'message': 'OK', 'req_id': rid}), 200

@app.route('/my_pending', methods=['POST'])
def get_pending():
    code = request.json.get('user_code')
    inbox = []
    for rid, info in PENDING_DB.items():
        if USERS_DB[info['receiver']]['code'] == code:
            inbox.append({
                'request_id': rid, 
                'sender': info['sender'], 
                'algo': info['algo'], 
                'preview_url': f"http://127.0.0.1:5001/temp_preview/{os.path.basename(info['filepath'])}"
            })
    return jsonify(inbox), 200

@app.route('/temp_preview/<path:filename>')
def serve_temp(filename): return send_from_directory(app.config['TEMP_FOLDER'], filename)

@app.route('/results/<path:filename>')
def serve_res(filename): return send_from_directory(app.config['RESULTS_FOLDER'], filename)

if __name__ == '__main__':
    print('AEGIS BACKEND - HYBRID RESPONSE MODE')
    app.run(host='0.0.0.0', port=5001, debug=True)