import os
import cv2
import time
import hashlib
import random
import uuid
import difflib
import numpy as np
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
from algorithms import LSBWatermark, DCTWatermark, SSWatermark
from reedsolo import RSCodec, ReedSolomonError

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# CONFIGURAZIONE 
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

# FUNZIONI DI SUPPORTO 

def fuzzy_search_users(decoded_text):
    """Cerca firmatari anche se il testo è leggermente corrotto."""
    best_sender = "Sconosciuto"
    best_receiver = "Sconosciuto"
    found = False
    
    # Filtra solo caratteri leggibili per pulire il rumore
    clean_text = ''.join(c for c in decoded_text if c.isprintable())
    print(f"Analisi Fuzzy su testo grezzo: '{clean_text}'")

    if "<->" in clean_text:
        parts = clean_text.split("<->")
        if len(parts) >= 2:
            candidate_sender = parts[0][-8:]
            candidate_receiver = parts[1][:8]
            for name, data in USERS_DB.items():
                if difflib.SequenceMatcher(None, data['code'], candidate_sender).ratio() > 0.7: # Abbassata soglia tolleranza
                    best_sender = f"{name} ({data['code']})"
                if difflib.SequenceMatcher(None, data['code'], candidate_receiver).ratio() > 0.7:
                    best_receiver = f"{name} ({data['code']})"
            
            if "Sconosciuto" not in best_sender or "Sconosciuto" not in best_receiver:
                found = True
    return found, best_sender, best_receiver, clean_text

# 1. SCRITTURA WATERMARK BLINDATO (COMBO)
def apply_robust_watermark(image_path, signature_text):
    try:
        img = cv2.imread(image_path)
        if img is None: return None
        
        print(f"AVVIO SCRITTURA POTENZIATA: {signature_text}")

        # 1. Encoding RS (Aggiunge ridondanza per correggere errori)
        rsc = RSCodec(10) 
        secret_data = rsc.encode(signature_text.encode('utf-8'))
        bits = []
        for byte in secret_data:
            for i in range(8):
                bits.append((byte >> (7 - i)) & 1)
        
        h, w, _ = img.shape
        # MODIFICA 1: Usiamo il canale VERDE (Indice 1) invece del BLU (Indice 0)
        # Il verde è più robusto alla compressione JPEG
        channel = img[:, :, 1].astype(np.float32)
        
        data_index = 0
        max_bits = len(bits)
        
        # MODIFICA 2: ALPHA AUMENTATO A 60 (Molto aggressivo)
        ALPHA = 60 
        
        for i in range(0, h, 8):
            for j in range(0, w, 8):
                if data_index >= max_bits: break
                block = channel[i:i+8, j:j+8]
                if block.shape != (8, 8): continue
                
                dct_block = cv2.dct(block)
                
                # Modifica coefficienti medi frequenza
                v1, v2 = dct_block[4, 3], dct_block[3, 4]
                bit = bits[data_index]
                
                if bit == 1:
                    # Forza v1 ad essere molto maggiore di v2
                    if v1 <= v2 + ALPHA: dct_block[4, 3] = v2 + ALPHA + 5
                else:
                    # Forza v2 ad essere molto maggiore di v1
                    if v2 <= v1 + ALPHA: dct_block[3, 4] = v1 + ALPHA + 5
                
                channel[i:i+8, j:j+8] = cv2.idct(dct_block)
                data_index += 1
                
        img[:, :, 1] = np.clip(channel, 0, 255)
        
        out_name = f"robust_{int(time.time())}.png"
        out_path = os.path.join(app.config['RESULTS_FOLDER'], out_name)
        
        # Salvataggio
        cv2.imwrite(out_path, img, [cv2.IMWRITE_PNG_COMPRESSION, 0])
        print(f"✅ Immagine blindata salvata in: {out_path}")
        return out_name
    except Exception as e:
        print(f"❌ Error Robust Write: {e}")
        return None

# 2. LETTURA WATERMARK BLINDATO (CON DEBUG) 
def extract_robust_watermark(img):
    try:
        h, w, _ = img.shape
        #Importante: Leggiamo lo stesso canale (VERDE)
        channel = img[:, :, 1].astype(np.float32)
        extracted_bits = []
        
        # Estraiamo TUTTI i bit possibili
        for i in range(0, h, 8):
            for j in range(0, w, 8):
                block = channel[i:i+8, j:j+8]
                if block.shape != (8, 8): continue
                dct_block = cv2.dct(block)
                v1, v2 = dct_block[4, 3], dct_block[3, 4]
                
                if v1 > v2: extracted_bits.append(1)
                else: extracted_bits.append(0)

        # Ricostruzione Bytes
        byte_array = bytearray()
        for i in range(0, len(extracted_bits), 8):
            if i + 8 > len(extracted_bits): break
            byte_val = 0
            for bit_idx in range(8):
                byte_val = (byte_val << 1) | extracted_bits[i + bit_idx]
            byte_array.append(byte_val)
            
        print(f"Bit estratti totali: {len(extracted_bits)}")
        
        # TENTATIVO DI DECODIFICA "RAW" (Senza correzione errori)
        # Questo serve per vedere se c'è qualcosa anche se ReedSolomon fallisce
        raw_preview = ""
        try:
            # Prende i primi 50 caratteri ASCII leggibili per debug
            raw_preview = byte_array[:50].decode('utf-8', errors='ignore')
            print(f"👀 PREVIEW GREZZA (NO RS): {raw_preview}")
        except: pass

        # Tentativo Decodifica ReedSolomon
        rsc = RSCodec(10)
        # Proviamo lunghezze diverse per trovare il messaggio
        for attempt_len in [20, 30, 40, 50, 60]: 
            try:
                decoded_msg = rsc.decode(byte_array[:attempt_len])[0]
                return decoded_msg.decode('utf-8'), raw_preview
            except:
                continue
        
        return None, raw_preview
            
    except Exception as e:
        print(f"Error Robust Read: {e}")
        return None, "ErroreLettura"

# ROTTE API 

@app.route('/results/<filename>')
def serve_result(filename):
    return send_from_directory(app.config['RESULTS_FOLDER'], filename)

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    input_user = data.get('username', '').strip().lower()
    input_pass = data.get('password')
    found_user_key = None
    for db_name in USERS_DB:
        if db_name.lower() == input_user:
            found_user_key = db_name
            break
    if found_user_key and USERS_DB[found_user_key]['pass'] == input_pass:
        return jsonify({'message': 'OK', 'user_code': USERS_DB[found_user_key]['code'], 'username': found_user_key}), 200
    return jsonify({'error': 'Credenziali errate'}), 401

@app.route('/request_transfer', methods=['POST'])
def request_transfer():
    if 'image' not in request.files: return jsonify({'error': 'No file'}), 400
    file = request.files['image']
    sender = request.form.get('sender_name')
    receiver = request.form.get('receiver_name')
    algo = request.form.get('algorithm', 'LSB')
    receiver_key = None
    for name in USERS_DB:
        if name.lower() == receiver.lower():
            receiver_key = name
            break
    if not receiver_key: return jsonify({'error': f"Utente {receiver} non trovato"}), 404

    filename = secure_filename(f"{uuid.uuid4()}_{file.filename}")
    filepath = os.path.join(app.config['TEMP_FOLDER'], filename)
    file.save(filepath)
    req_id = str(uuid.uuid4())
    PENDING_DB[req_id] = {"sender": sender, "receiver": receiver_key, "filepath": filepath, "algo": algo, "timestamp": time.time()}
    return jsonify({'message': 'Richiesta inviata', 'req_id': req_id}), 200

@app.route('/temp_preview/<path:filename>')
def serve_temp(filename):
    return send_from_directory(app.config['TEMP_FOLDER'], filename)

@app.route('/my_pending', methods=['POST'])
def get_pending():
    data = request.json
    my_code = data.get('user_code') 
    if not my_code:
        username_sent = data.get('username')
        if username_sent:
            for db_name, db_data in USERS_DB.items():
                if db_name.lower() == username_sent.lower():
                    my_code = db_data['code']
                    break
    if not my_code: return jsonify([]), 200

    inbox = []
    for req_id, info in PENDING_DB.items():
        dest_name = info['receiver']
        if dest_name in USERS_DB:
            dest_code = USERS_DB[dest_name]['code']
            if dest_code == my_code:
                item = info.copy()
                item['request_id'] = req_id 
                filename = os.path.basename(info['filepath'])
                item['preview_url'] = f"http://127.0.0.1:5001/temp_preview/{filename}"
                del item['filepath'] 
                inbox.append(item)
    return jsonify(inbox), 200

@app.route('/accept_transfer', methods=['POST'])
def accept_transfer():
    req_id = request.json.get('request_id')
    if req_id not in PENDING_DB: return jsonify({'error': 'Richiesta scaduta'}), 404
    req_data = PENDING_DB.pop(req_id)
    
    sender_name = req_data['sender']
    sender_code = "UNKNOWN"
    for name in USERS_DB:
        if name.lower() == sender_name.lower():
            sender_code = USERS_DB[name]['code']
            break     
    receiver_code = USERS_DB[req_data['receiver']]['code']
    signature = f"{sender_code}<->{receiver_code}"
    
    try:
        algo = req_data['algo']
        download_url = ""
        out_name = ""

        if algo == 'COMBO':
            out_name = apply_robust_watermark(req_data['filepath'], signature)
            if not out_name: raise Exception("Fallimento funzione robusta")
        else:
            img = cv2.imread(req_data['filepath'])
            output_img = None
            if algo == 'LSB': output_img = LSBWatermark().embed(img, signature)
            elif algo == 'DCT': output_img = DCTWatermark().embed(img, signature)
            elif algo == 'SS':
                key = int(hashlib.sha256(signature.encode()).hexdigest(), 16) % (10**8)
                output_img = SSWatermark(key=key).embed(img)
            
            out_name = f"signed_{int(time.time())}.png"
            out_path = os.path.join(app.config['RESULTS_FOLDER'], out_name)
            cv2.imwrite(out_path, output_img, [cv2.IMWRITE_PNG_COMPRESSION, 0])

        if os.path.exists(req_data['filepath']): os.remove(req_data['filepath'])
        download_url = f"http://127.0.0.1:5001/results/{out_name}"
        return jsonify({'signature': signature, 'url': download_url}), 200
        
    except Exception as e:
        print(f"❌ ERRORE: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/verify', methods=['POST'])
def verify_image():
    if 'image' not in request.files: return jsonify({'error': 'No file'}), 400
    file = request.files['image']
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], "check_temp_verify.png")
    file.save(filepath)
    img = cv2.imread(filepath)
    
    found = False
    sender = "Sconosciuto"
    receiver = "Sconosciuto"
    technique = "Nessuna"
    raw_sig = "" 

    print("🔍 VERIFICA: Inizio Scansione...")

    # 1. TENTATIVO BLINDATO (COMBO)
    msg_combo, raw_preview = extract_robust_watermark(img)
    
    # Se il metodo blindato fallisce, mostriamo almeno cosa ha visto (raw_preview)
    # così l'utente sa che il sistema ha provato a leggere.
    if msg_combo and "<->" in msg_combo:
        found, s, r, raw = fuzzy_search_users(msg_combo)
        if found:
            sender, receiver, raw_sig = s, r, raw
            technique = "COMBO (Blindato)"
    else:
        # Se fallisce, usiamo raw_preview come indizio
        if raw_preview and len(raw_preview) > 5:
            raw_sig = f"Grezzo: {raw_preview}"

    # 2. TENTATIVO LSB
    if not found:
        try:
            msg_lsb = LSBWatermark().extract(img)
            if "USR_" in msg_lsb:
                found, s, r, raw = fuzzy_search_users(msg_lsb)
                if found:
                    sender, receiver, raw_sig = s, r, raw
                    technique = "LSB"
        except: pass

    # 3. TENTATIVO DCT STANDARD
    if not found:
        try:
            msg_dct = DCTWatermark().extract(img)
            found_fuzzy, s, r, raw = fuzzy_search_users(msg_dct)
            if found_fuzzy:
                sender, receiver, raw_sig = s, r, raw
                technique = "DCT"
        except: pass

    # Se ancora non trovato, restituiamo quello che abbiamo trovato (anche se parziale)
    return jsonify({
        'found': found, 
        'sender': sender, 
        'receiver': receiver,
        'technique': technique,
        'watermark': raw_sig, # Questo mostrerà il testo grezzo nell'app se fallisce
        'algorithm': technique
    }), 200

if __name__ == '__main__':
    print("Aegis System (POTENZIATO) avviato su porta 5001")
    app.run(host='0.0.0.0', port=5001, debug=True)