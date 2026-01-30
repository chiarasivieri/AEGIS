import cv2
import numpy as np
import re

# --- 1. LSB WATERMARK (Fragile - per integrità) ---
class LSBWatermark:
    def embed(self, image, message):
        # Aggiungiamo un terminatore semplice
        msg = message + "#####"
        binary = ''.join(format(ord(c), '08b') for c in msg)
        
        flat = image.flatten()
        if len(binary) > len(flat): return image # Troppo lungo, ignoriamo
        
        # Scrittura veloce
        for i in range(len(binary)):
            flat[i] = (flat[i] & 254) | int(binary[i])
            
        return flat.reshape(image.shape)

    def extract(self, image):
        flat = image.flatten()
        # Leggiamo i primi bit e cerchiamo il terminatore
        bits = ""
        # Leggiamo abbastanza bit per trovare la firma (es. 2000 bit)
        limit = min(len(flat), 4000)
        
        for i in range(limit):
            bits += str(flat[i] & 1)
            
        # Convertiamo a caratteri
        chars = []
        for i in range(0, len(bits), 8):
            byte = bits[i:i+8]
            if len(byte) == 8:
                try: chars.append(chr(int(byte, 2)))
                except: pass
                
        full_text = "".join(chars)
        if "#####" in full_text:
            return full_text.split("#####")[0]
        return ""

# --- 2. DCT WATERMARK (Strategia "Ripetizione Infinita") ---
class DCTWatermark:
    def __init__(self):
        self.block_size = 8
        # Coefficienti robusti (Medie frequenze)
        self.u1, self.v1 = 4, 3
        self.u2, self.v2 = 3, 4
        # Forza della scrittura (più è alto, più resiste al JPG, ma si vede un po')
        self.alpha = 100.0 

    def embed(self, image, message):
        h, w, _ = image.shape
        # Usiamo il canale VERDE (indice 1), spesso compresso meno del blu
        # o YUV se preferisci, ma BGR è più semplice da gestire qui senza conversioni errate
        vis_image = image.astype(np.float32)
        channel = vis_image[:, :, 1] 

        # PREPARAZIONE MESSAGGIO
        # Formato: ###MESSAGGIO###
        # Lo ripetiamo finché non riempiamo l'immagine
        marker = "###"
        full_msg_unit = marker + message + marker
        bits_unit = ''.join(format(ord(c), '08b') for c in full_msg_unit)
        
        blocks_h = h // self.block_size
        blocks_w = w // self.block_size
        max_bits = blocks_h * blocks_w
        
        # Creiamo un flusso infinito di bit ripetuti
        repeats = (max_bits // len(bits_unit)) + 1
        full_bits_stream = (bits_unit * repeats)[:max_bits]
        
        bit_idx = 0
        
        print(f"--- DCT: Scrivo il messaggio ripetuto {repeats} volte ---")

        for row in range(blocks_h):
            for col in range(blocks_w):
                if bit_idx >= len(full_bits_stream): break
                
                # Coordinate blocco
                y = row * self.block_size
                x = col * self.block_size
                
                block = channel[y:y+8, x:x+8]
                dct_block = cv2.dct(block)
                
                # Logica di embedding
                v1 = dct_block[self.u1, self.v1]
                v2 = dct_block[self.u2, self.v2]
                bit = int(full_bits_stream[bit_idx])
                
                if bit == 0:
                    if v1 <= v2 + self.alpha:
                        diff = (v2 + self.alpha - v1) / 2.0
                        v1 += diff
                        v2 -= diff
                else: # bit == 1
                    if v2 <= v1 + self.alpha:
                        diff = (v1 + self.alpha - v2) / 2.0
                        v2 += diff
                        v1 -= diff
                
                dct_block[self.u1, self.v1] = v1
                dct_block[self.u2, self.v2] = v2
                
                channel[y:y+8, x:x+8] = cv2.idct(dct_block)
                bit_idx += 1
                
        # Salviamo
        vis_image[:, :, 1] = channel
        return np.clip(vis_image, 0, 255).astype(np.uint8)

    def extract(self, image):
        h, w, _ = image.shape
        vis_image = image.astype(np.float32)
        channel = vis_image[:, :, 1]
        
        blocks_h = h // self.block_size
        blocks_w = w // self.block_size
        
        bits = []
        
        # 1. ESTRAZIONE MASSIVA
        # Leggiamo tutti i bit dell'immagine
        for row in range(blocks_h):
            for col in range(blocks_w):
                y = row * self.block_size
                x = col * self.block_size
                
                # Check bordi
                if y+8 > h or x+8 > w: continue

                dct_block = cv2.dct(channel[y:y+8, x:x+8])
                
                v1 = dct_block[self.u1, self.v1]
                v2 = dct_block[self.u2, self.v2]
                
                if v1 > v2: bits.append('0')
                else: bits.append('1')
                
        # 2. RICERCA DEL TESORO (Pattern Matching)
        # Convertiamo i bit in una lunghissima stringa di testo
        # Ogni 8 bit -> 1 carattere
        full_text = ""
        # Ottimizzazione: processiamo a chunk per non esplodere
        raw_bits_str = "".join(bits)
        
        chars = []
        for i in range(0, len(raw_bits_str), 8):
            byte = raw_bits_str[i:i+8]
            if len(byte) == 8:
                try: 
                    # Filtro caratteri validi per evitare crash su caratteri strani
                    val = int(byte, 2)
                    if 32 <= val <= 126: # Solo caratteri stampabili ASCII
                        chars.append(chr(val))
                    else:
                        chars.append('?') # Placeholder per rumore
                except: pass
                
        giant_string = "".join(chars)
        
        # Debug nel terminale: vediamo se c'è qualcosa
        print(f"DEBUG ESTRAZIONE (Primi 100 char): {giant_string[:100]}")
        
        # 3. CERCA I MARKER "###"
        # Usiamo una regex per trovare "###...###"
        # Il '.*?' significa "prendi tutto quello che c'è in mezzo"
        matches = re.findall(r'###(.*?)###', giant_string)
        
        for match in matches:
            # Filtriamo i falsi positivi
            if "USR_" in match or "<->" in match:
                return match # Trovato!
            if len(match) > 5 and len(match) < 50:
                 # Fallback: se troviamo testo che sembra sensato
                 return match
                 
        return ""

# --- 3. COMBO (Usa entrambe) ---
class ComboWatermark:
    def __init__(self):
        self.lsb = LSBWatermark()
        self.dct = DCTWatermark()
        
    def embed(self, image, text):
        # Prima DCT (Robusto)
        temp = self.dct.embed(image, text)
        # Poi LSB (Fragile)
        final = self.lsb.embed(temp, text)
        return final
        
    def extract(self, image):
        # Proviamo LSB
        res = self.lsb.extract(image)
        if res and ("USR_" in res or "<->" in res):
            return res
            
        # Proviamo DCT
        res = self.dct.extract(image)
        if res:
            return res
            
        return ""
        
class SSWatermark:
    def embed(self, img, k=None): return img
    def extract(self, img): return ""