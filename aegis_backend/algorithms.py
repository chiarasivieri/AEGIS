import cv2
import numpy as np
from collections import Counter
import re

# --- LSB (Lasciamo vuoto per ora) ---
class LSBWatermark:
    def embed(self, img, m): return img
    def extract(self, img): return ""

# --- DCT (Versione Stabile con Marker) ---
class DCTWatermark:
    def __init__(self):
        self.block_size = 8
        self.Q = 120         # Forza della firma
        self.marker = "###"   # Marker di inizio/fine

    def to_bits(self, message):
        bits = []
        for char in message:
            bin_val = format(ord(char), '08b')
            bits.extend([int(b) for b in bin_val])
        return bits

    def embed(self, img, message):
        # Aggiungi marker: ###MESSAGGIO###
        full_msg = self.marker + message + self.marker
        
        img_float = np.float32(img)
        h, w, _ = img_float.shape
        b_channel = img_float[:, :, 0]
        
        msg_bits = self.to_bits(full_msg)
        msg_len = len(msg_bits)
        if msg_len == 0: return img

        bit_idx = 0
        
        # Scriviamo su tutta l'immagine
        for i in range(0, h - self.block_size, self.block_size):
            for j in range(0, w - self.block_size, self.block_size):
                block = b_channel[i:i+self.block_size, j:j+self.block_size]
                dct_block = cv2.dct(block)
                
                bit = msg_bits[bit_idx % msg_len]
                
                # Usiamo frequenze (1,2) e (2,1) che resistono al JPEG
                v1 = dct_block[1, 2]
                v2 = dct_block[2, 1]
                
                if bit == 1:
                    if v1 <= v2:
                        dct_block[1, 2] = v2 + self.Q
                        dct_block[2, 1] = v1 - self.Q
                    else:
                        if (v1 - v2) < self.Q:
                            dct_block[1, 2] += self.Q/2 + 5
                            dct_block[2, 1] -= self.Q/2 + 5
                else:
                    if v1 >= v2:
                        dct_block[1, 2] = v2 - self.Q
                        dct_block[2, 1] = v1 + self.Q
                    else:
                        if (v2 - v1) < self.Q:
                            dct_block[1, 2] -= self.Q/2 + 5
                            dct_block[2, 1] += self.Q/2 + 5

                b_channel[i:i+self.block_size, j:j+self.block_size] = cv2.idct(dct_block)
                bit_idx += 1

        img_float[:, :, 0] = b_channel
        return np.uint8(img_float)

    def extract_raw_bits(self, b_channel, h, w, off_y, off_x):
        bits = []
        step = self.block_size
        for i in range(off_y, h - step, step):
            for j in range(off_x, w - step, step):
                block = b_channel[i:i+step, j:j+step]
                dct_block = cv2.dct(block)
                if dct_block[1, 2] > dct_block[2, 1]:
                    bits.append('1')
                else:
                    bits.append('0')
        return "".join(bits)

    def extract(self, img, expected_len_bytes=None):
        img_float = np.float32(img)
        h, w, _ = img_float.shape
        b_channel = img_float[:, :, 0]
        
        candidates = []
        
        # Grid Search: prova tutti gli allineamenti possibili
        # Questo garantisce che il Crop non rompa tutto
        for dy in range(8):
            for dx in range(8):
                raw_bits = self.extract_raw_bits(b_channel, h, w, dy, dx)
                
                # Converti bit in testo
                chars = []
                for k in range(0, len(raw_bits), 8):
                    chunk = raw_bits[k:k+8]
                    if len(chunk) < 8: break
                    chars.append(chr(int(chunk, 2)))
                full_text = "".join(chars)
                
                # Cerca i marker ###...###
                matches = re.findall(r'###(.*?)###', full_text)
                for m in matches:
                    if len(m) > 0 and all(c.isalnum() or c in "_- " for c in m):
                        candidates.append(m)
        
        if not candidates: return "Nessun dato"
        return Counter(candidates).most_common(1)[0][0]

class SSWatermark:
    def __init__(self, key=42): pass
    def embed(self, img): return img