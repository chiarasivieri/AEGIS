import cv2
import numpy as np
import os
import difflib
from algorithms import DCTWatermark

# CONFIGURAZIONE 
NOME_FILE = "robust_1769254446.png"  # La tua foto di test


# 1. DEFINIZIONE ATTACCHI 

def attacco_jpeg(img, qualita):
    cv2.imwrite("temp_full.jpg", img, [cv2.IMWRITE_JPEG_QUALITY, qualita])
    return cv2.imread("temp_full.jpg")

def attacco_crop(img):
    h, w, _ = img.shape
    # Taglia il cuore dell'immagine (60% centrale)
    return img[int(h*0.2):int(h*0.8), int(w*0.2):int(w*0.8)]

def attacco_rumore(img):
    # Aggiunge "grana" (Rumore Gaussiano)
    row, col, ch = img.shape
    mean = 0
    var = 50 
    sigma = var**0.5
    gauss = np.random.normal(mean, sigma, (row, col, ch))
    gauss = gauss.reshape(row, col, ch)
    noisy = img + gauss
    return np.clip(noisy, 0, 255).astype(np.uint8)

def attacco_luminosita(img):
    # Aumenta luminosità (+50) e Contrasto
    return cv2.convertScaleAbs(img, alpha=1.1, beta=40)

def attacco_resize(img):
    # Ridimensiona al 50% e poi riporta originale (simula anteprime web)
    h, w, _ = img.shape
    small = cv2.resize(img, (int(w/2), int(h/2)), interpolation=cv2.INTER_LINEAR)
    back_to_normal = cv2.resize(small, (w, h), interpolation=cv2.INTER_LINEAR)
    return back_to_normal

# 2. VALUTAZIONE INTELLIGENTE

def valuta(test_name, originale, letto):
    print(f"🔹 {test_name}:".ljust(35), end=" ")
    
    if originale == letto:
        print("✅ SUPERATO (Perfetto)")
        return

    # Calcola somiglianza (0.0 - 1.0)
    ratio = difflib.SequenceMatcher(None, originale, letto).ratio()
    
    if ratio > 0.60: # Tolleranza al 75%
        print(f" SUPERATO PARZIALMENTE (Letto: '{letto}' - Simile al {int(ratio*100)}%)")
    elif len(letto) > 3 and (originale in letto or letto in originale):
        print(f" SUPERATO PARZIALMENTE (Frammento trovato: '{letto}')")
    else:
        print(f"FALLITO (Letto: '{letto}')")

# 3. ESECUZIONE 

print(f"\nSUITE COMPLETA SU FOTO REALE: {NOME_FILE} ")

img_originale = cv2.imread(NOME_FILE)
if img_originale is None:
    print(f"Errore: File '{NOME_FILE}' non trovato.")
    exit()

print(f"Immagine caricata: {img_originale.shape[1]}x{img_originale.shape[0]} pixel")

dct = DCTWatermark()
# Per sicurezza, firmiamo l'immagine caricata in memoria
# (così siamo sicuri che la firma sia fresca e corretta per il confronto)
print(f"✍️  Inserimento firma '{FIRMA}' in corso...")
img_firmata = dct.embed(img_originale.copy(), FIRMA)

print("\n--- INIZIO TORTURA ---")

# 1. JPEG Soft
valuta("Compressione JPEG (70%)", FIRMA, dct.extract(attacco_jpeg(img_firmata, 70)))

# 2. JPEG Hard
valuta("Compressione JPEG (50%)", FIRMA, dct.extract(attacco_jpeg(img_firmata, 50)))

# 3. Crop
valuta("Ritaglio Centrale (Crop)", FIRMA, dct.extract(attacco_crop(img_firmata)))

# 4. Luminosità
valuta("Aumento Luminosità (+40)", FIRMA, dct.extract(attacco_luminosita(img_firmata)))

# 5. Rumore
valuta("Aggiunta Rumore (Noise)", FIRMA, dct.extract(attacco_rumore(img_firmata)))

# 6. Resize (Il test più difficile)
valuta("Ridimensionamento (50% -> 100%)", FIRMA, dct.extract(attacco_resize(img_firmata)))


if os.path.exists("temp_full.jpg"): os.remove("temp_full.jpg")