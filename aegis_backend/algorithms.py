import cv2
import numpy as np
from reedsolo import RSCodec, ReedSolomonError

# LSB WATERMARK (Semplice, per demo)
class LSBWatermark:
    def embed(self, image, secret_message):
        # Aggiungiamo un terminatore univoco
        secret_message += "#####"
        binary_message = ''.join(format(ord(char), '08b') for char in secret_message)
        data_len = len(binary_message)
        
        flat_image = image.flatten()
        if data_len > len(flat_image):
            raise ValueError("Messaggio troppo lungo!")
            
        for i in range(data_len):
            # Azzera l'ultimo bit e metti il nostro
            flat_image[i] = (flat_image[i] & 254) | int(binary_message[i])
            
        return flat_image.reshape(image.shape)

    def extract(self, image):
        flat_image = image.flatten()
        binary_data = ""
        # Leggiamo i primi 4000 byte per sicurezza
        limit = min(len(flat_image), 4000 * 8)
        
        for i in range(limit):
            binary_data += str(flat_image[i] & 1)
            
        all_bytes = [binary_data[i: i+8] for i in range(0, len(binary_data), 8)]
        decoded_data = ""
        
        for byte in all_bytes:
            try:
                char = chr(int(byte, 2))
                decoded_data += char
                if decoded_data.endswith("#####"):
                    return decoded_data[:-5]
            except:
                pass
        return ""

# DCT WATERMARK (ROBUSTO)
class DCTWatermark:
    def __init__(self):
        self.block_size = 8
        # Coefficienti DCT da modificare (frequenze medie, robuste a compressione)
        self.u1, self.v1 = 4, 3 
        self.u2, self.v2 = 3, 4 

    def embed(self, image, secret_message):
        # 1. Converti stringa in bit
        binary_message = ''.join(format(ord(char), '08b') for char in secret_message)
        msg_len = len(binary_message)
        
        # Lavoriamo sul canale Blu (o Y in YUV), qui usiamo BGR -> Blu è canale 0
        h, w, _ = image.shape
        b_channel = image[:, :, 0].astype(np.float32)
        
        # Calcola quanti blocchi abbiamo
        blocks_h = h // self.block_size
        blocks_w = w // self.block_size
        total_blocks = blocks_h * blocks_w
        
        # TILING: Ripetiamo il messaggio finché riempiamo l'immagine
        # Questo aiuta contro il CROP
        full_message_bits = (binary_message * (total_blocks // msg_len + 1))[:total_blocks]
        
        msg_index = 0
        
        for row in range(blocks_h):
            for col in range(blocks_w):
                if msg_index >= len(full_message_bits):
                    break
                    
                bit = int(full_message_bits[msg_index])
                
                # Coordinate blocco
                y = row * self.block_size
                x = col * self.block_size
                
                block = b_channel[y:y+8, x:x+8]
                dct_block = cv2.dct(block)
                
                # LOGICA ROBUSTAcd 
                # Modifichiamo i valori finché la differenza non regge all'arrotondamento
                v1 = dct_block[self.u1, self.v1]
                v2 = dct_block[self.u2, self.v2]
                
                alpha = 100
                max_attempts = 5 # Evita loop infiniti
                
                for _ in range(max_attempts):
                    if bit == 0:
                        # Vogliamo v1 > v2
                        if v1 <= v2 + alpha:
                            diff = (v2 + alpha - v1) / 2.0
                            v1 += diff
                            v2 -= diff
                    else: # bit == 1
                        # Vogliamo v2 > v1
                        if v2 <= v1 + alpha:
                            diff = (v1 + alpha - v2) / 2.0
                            v2 += diff
                            v1 -= diff
                    
                    # Applica modifiche
                    dct_block[self.u1, self.v1] = v1
                    dct_block[self.u2, self.v2] = v2
                    
                    # CHECK DI VALIDITÀ
                    # Simuliamo la riconversione in immagine
                    idct_block = cv2.idct(dct_block)
                    # Arrotondiamo come farebbe il salvataggio file
                    rounded_block = np.clip(idct_block, 0, 255).astype(np.uint8).astype(np.float32)
                    # Rifacciamo la DCT per vedere cosa si legge
                    check_dct = cv2.dct(rounded_block)
                    
                    c1 = check_dct[self.u1, self.v1]
                    c2 = check_dct[self.u2, self.v2]
                    
                    # Se il bit è leggibile correttamente, usciamo dal loop
                    if bit == 0 and c1 > c2 + 5: # +5 margine di sicurezza
                        break
                    elif bit == 1 and c2 > c1 + 5:
                        break
                    else:
                        # Se fallisce, aumenta la forza e riprova
                        alpha += 15 

                # Scrivi il blocco finale nell'immagine
                b_channel[y:y+8, x:x+8] = cv2.idct(dct_block)
                msg_index += 1
                
        # Ricomponi immagine
        img_watermarked = image.copy()
        img_watermarked[:, :, 0] = np.clip(b_channel, 0, 255).astype(np.uint8)
        return img_watermarked

    def extract(self, image):
        # Estrae tutti i bit possibili dall'immagine
        h, w, _ = image.shape
        b_channel = image[:, :, 0].astype(np.float32)
        
        extracted_bits = ""
        
        blocks_h = h // self.block_size
        blocks_w = w // self.block_size
        
        for row in range(blocks_h):
            for col in range(blocks_w):
                y = row * self.block_size
                x = col * self.block_size
                
                block = b_channel[y:y+8, x:x+8]
                dct_block = cv2.dct(block)
                
                v1 = dct_block[self.u1, self.v1]
                v2 = dct_block[self.u2, self.v2]
                
                if v1 > v2:
                    extracted_bits += "0"
                else:
                    extracted_bits += "1"
                    
        return extracted_bits

# COMBO: REED SOLOMON + DCT (Il migliore per il progetto)
class ComboWatermark:
    def __init__(self):
        self.dct = DCTWatermark()
        self.rsc = RSCodec(10) # 10 byte di correzione errori

    def embed(self, image, text):
        # 1. Aggiungi header fisso per riconoscere l'inizio
        # "REVENGE" è il marker. Se lo troviamo, abbiamo vinto.
        full_msg = "REVENGE_" + text
        
        # 2. Codifica Reed-Solomon (aggiunge ridondanza errori)
        msg_bytes = full_msg.encode('utf-8')
        encoded_data = self.rsc.encode(msg_bytes)
        
        # ConvertE byte encoded in stringa latin-1 per passarla bit a bit
        # (Trucco sporco ma efficace per riusare la logica DCT string-based)
        encoded_str = "".join([chr(b) for b in encoded_data])
        
        return self.dct.embed(image, encoded_str)

    def extract(self, image):
        # Estrai il flusso grezzo di bit
        raw_bits = self.dct.extract(image)
        
        # Converti bit in bytes
        bytes_data = bytearray()
        for i in range(0, len(raw_bits), 8):
            byte_chunk = raw_bits[i:i+8]
            if len(byte_chunk) == 8:
                bytes_data.append(int(byte_chunk, 2))
        
        # RICERCA DEL MESSAGGIO (SLIDING WINDOW) 
        # Poiché abbiamo ripetuto il messaggio (Tiling), cerchiamo
        # ovunque un blocco valido decodificabile con ReedSolomon
        
        # Lunghezza stimata del pacchetto (messaggio + ecc). 
        # Cerchiamo chunk da 20 a 60 byte
        for length in range(20, 100): 
            for start in range(0, len(bytes_data) - length, 1): # Scan byte per byte
                chunk = bytes(bytes_data[start : start+length])
                try:
                    # Prova a decodificare
                    decoded = self.rsc.decode(chunk)[0]
                    text = decoded.decode('utf-8')
                    
                    # Se troviamo il marker, è lui al 100%
                    if text.startswith("REVENGE_"):
                        return text.replace("REVENGE_", "")
                        
                except (ReedSolomonError, UnicodeDecodeError, ValueError):
                    continue
                    
        return "Nessuna firma rilevata (o immagine troppo corrotta)"

# Placeholder per SS (Spread Spectrum) se serve
class SSWatermark:
    def embed(self, img, msg): return img # Da implementare se richiesto
    def extract(self, img): return "Non implementato"