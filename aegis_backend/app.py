import os
import cv2
import time
import uuid
import difflib
import re
import numpy as np
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename

# IMPORTIAMO GLI ALGORITMI
# Assicurati che il file algorithms.py sia nella stessa cartella
from algorithms import LSBWatermark, DCTWatermark, SSWatermark, ComboWatermark

app = Flask(__name__)
# Abilita CORS per permettere a Flutter di comunicare
CORS(app, resources={r"/*": {"origins": "*"}})


# CONFIGURAZIONE E DATABASE

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

# Creiamo le cartelle se non esistono
for folder in [UPLOAD_FOLDER, TEMP_FOLDER, RESULTS_FOLDER]:
    os.makedirs(folder, exist_ok=True)

app.config['TEMP_FOLDER'] = TEMP_FOLDER
app.config['RESULTS_FOLDER'] = RESULTS_FOLDER
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def get_next_user_code():
    count = len(USERS_DB) + 1
    return f"USR_{count:04d}"


# FUNZIONI HELPER

def fuzzy_search_users(text):
    """
    Analizza il testo estratto per trovare mittente e destinatario.
    """
    if not text: 
        return False, "Sconosciuto", "Sconosciuto", ""
    
    # Puliamo il testo da caratteri strani
    clean_text = "".join(c for c in text if c.isprintable())
    found = False
    sender = "Sconosciuto"
    receiver = "Sconosciuto"
    
    # Cerca pattern tipo USR_xxxx
    matches = list(re.finditer(r"USR_\d{4}|SUPER_USER", clean_text))
    
    # Caso 1: Trovati due codici (Mittente e Destinatario)
    if len(matches) >= 2:
        code1 = matches[0].group()
        code2 = matches[1].group()
        
        # Mappa codici a nomi
        for u, d in USERS_DB.items():
            if d['code'] == code1: sender = f"{u} ({code1})"
            if d['code'] == code2: receiver = f"{u} ({code2})"
        found = True
        
    # Caso 2: Trovato solo un codice o formato <->
    elif "USR_" in clean_text or "<->" in clean_text:
        parts = clean_text.split('<->')
        if len(parts) == 2:
            s_code = parts[0].strip()
            r_code = parts[1].strip()
            
            for u, d in USERS_DB.items():
                if d['code'] in s_code: sender = f"{u} ({d['code']})"
                if d['code'] in r_code: receiver = f"{u} ({d['code']})"
            found = True
        elif len(matches) == 1:
            code = matches[0].group()
            sender = f"Rilevato: {code}"
            found = True

    return found, sender, receiver, clean_text

# ROTTE PRINCIPALI


@app.route('/verify', methods=['POST'])
def verify_image():
    """
    Verifica l'immagine caricata cercando il watermark.
    """
    if 'image' not in request.files:
        return jsonify({'error': 'No file'}), 400

    file = request.files['image']
    # Salviamo temporaneamente come PNG per non alterare i pixel
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'check_temp.png')
    file.save(filepath)

    # Carica immagine
    original_img = cv2.imread(filepath)
    if original_img is None:
        return jsonify({'error': 'Immagine non valida'}), 400

    print(f"\n{'='*40}\n🔍 VERIFICA AVVIATA\n{'='*40}")

    # Usiamo ComboWatermark (che include Reed-Solomon + DCT)
    verifier = ComboWatermark()

    found = False
    sender = "Sconosciuto"
    receiver = "Sconosciuto"
    technique = "Nessuna firma trovata"
    raw_sig = ""

    try:
        print("⚡ Provo estrazione...")
        extracted_msg = verifier.extract(original_img)
        
        # Controllo se il messaggio ha senso (contiene USR_ o il separatore <->)
        if extracted_msg and ("USR_" in extracted_msg or "<->" in extracted_msg):
            print(f"✅ TROVATO! Messaggio: {extracted_msg}")
            found, sender, receiver, raw_sig = fuzzy_search_users(extracted_msg)
            technique = "Analisi Spettrale/DCT (Riuscita)"
        else:
            print("❌ Nessuna firma rilevata.")

    except Exception as e:
        print(f"⚠️ Errore durante estrazione: {e}")

    # Risposta Finale JSON
    return jsonify({
        'verified': found,
        'sender': sender,
        'receiver': receiver,
        'technique': technique,
        'signature': raw_sig
    }), 200


@app.route('/accept_transfer', methods=['POST'])
def accept_transfer():
    """
    Applica il watermark e salva il file finale.
    QUESTA È LA PARTE CHE ABBIAMO MODIFICATO PER IL DOWNLOAD SICURO.
    """
    rid = request.json.get('request_id')
    if rid not in PENDING_DB: 
        return jsonify({'error': 'Richiesta scaduta o inesistente'}), 404
    
    info = PENDING_DB.pop(rid)
    
    # Costruzione firma: MITTENTE<->DESTINATARIO
    # Esempio: USR_0001<->USR_0002
    sender_code = next((v['code'] for k, v in USERS_DB.items() if k == info['sender'].lower()), 'UNK')
    receiver_code = USERS_DB[info['receiver']]['code']
    signature = f"{sender_code}<->{receiver_code}"
    
    print(f"📝 SCRITTURA FIRMA: {signature} su file {info['filepath']}")
    
    try:
        # 1. Carica immagine originale dal temp
        img = cv2.imread(info['filepath'])
        if img is None: raise Exception("Impossibile aprire il file temp")

        # 2. Applica il Watermark
        algo_name = info.get('algo', 'COMBO')
        
        if algo_name == 'COMBO':
            # Usa la nuova classe robusta
            wm = ComboWatermark()
            watermarked_img = wm.embed(img, signature)
        elif algo_name == 'LSB':
            watermarked_img = LSBWatermark().embed(img, signature)
        elif algo_name == 'DCT':
            watermarked_img = DCTWatermark().embed(img, signature)
        elif algo_name == 'SS':
            # SS semplice, non supporta testo variabile nel nostro esempio
            watermarked_img = SSWatermark().embed(img, "SS_KEY") 
        else:
            watermarked_img = img

        # 3. SALVATAGGIO FONDAMENTALE
        # Forziamo l'estensione .png per evitare la compressione JPEG che distrugge il watermark
        out_filename = f"secure_{int(time.time())}.png"
        out_path = os.path.join(app.config['RESULTS_FOLDER'], out_filename)
        
        # Scrive il file su disco
        cv2.imwrite(out_path, watermarked_img)

        # Pulizia file temporaneo originale
        if os.path.exists(info['filepath']): os.remove(info['filepath'])

        # Restituisce l'URL per scaricare il file protetto
        # Nota: L'app Flutter riceverà un URL che finisce per .png
        return jsonify({
            'signature': signature, 
            'url': f"http://127.0.0.1:5001/results/{out_filename}"
        }), 200

    except Exception as e:
        print(f"ERRORE SCRITTURA: {e}")
        return jsonify({'error': str(e)}), 500


# ALTRE ROTTE DI SUPPORTO


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
    # Default algo is COMBO
    algo = request.form.get('algorithm', 'COMBO')
    
    sender = request.form.get('sender_name')
    receiver_name = request.form.get('receiver_name', '').lower()
    receiver_key = next((k for k in USERS_DB if k == receiver_name), 'admin')
    
    PENDING_DB[rid] = {
        'sender': sender, 
        'receiver': receiver_key, 
        'filepath': fpath, 
        'algo': algo
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
def serve_temp(filename): 
    return send_from_directory(app.config['TEMP_FOLDER'], filename)

@app.route('/results/<path:filename>')
def serve_res(filename): 
    return send_from_directory(app.config['RESULTS_FOLDER'], filename)

if __name__ == '__main__':
    print('AEGIS BACKEND PRONTO')
    # Usa 0.0.0.0 per essere raggiungibile da rete esterna/simulatore
    app.run(host='0.0.0.0', port=5001, debug=True)