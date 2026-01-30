# 🛡️ Aegis — Framework per la condivisione sicura di immagini

**Aegis** è un framework (client–server) pensato per la **condivisione sicura di immagini** tramite **watermarking forense invisibile**, con l’obiettivo di aumentare **tracciabilità** e **non ripudiabilità** in scenari di diffusione illecita di contenuti sensibili (es. *revenge porn*).

L’idea chiave: anche se un’immagine viene trasmessa in modo sicuro, una volta ricevuta è difficile impedire che venga redistribuita. Aegis introduce quindi un meccanismo di **protezione forense**: una firma nascosta nell’immagine che può essere **estratta e verificata** a posteriori per supportare l’attribuzione.

---

## ✨ Cosa fa Aegis

- Inserisce watermark **invisibili** in immagini digitali con finalità **forensi/investigative**
- Verifica la presenza e la validità del watermark tramite un backend dedicato
- Supporta più tecniche di watermarking:
  - **LSB** (spaziale): semplice e poco costoso, ma fragile
  - **DCT** (frequenze): più robusto verso compressione (es. JPEG)
  - **Spread Spectrum**: resistente e adatto a scenari forensi avanzati
- Include un algoritmo ibrido proprietario:
  - **“Aegis Combo” (DCT + ECC)**: watermark in DCT + **Reed–Solomon** per correzione d’errore + fallback “fuzzy” per immagini degradate

---

## 🧱 Architettura

Aegis è organizzato come sistema **client–server**:

- **Frontend mobile (Flutter)**  
  App utente per registrazione/login, invio e ricezione immagini, scelta algoritmo, download.
- **Backend forense (Python + Flask)**  
  Motore investigativo: riceve immagini, estrae/verifica watermark, produce output JSON.
- **Pagina amministrativa di verifica (HTML/JS)**  
  Interfaccia manuale per analisti: upload immagine sospetta → risultato forense.

---

## 🧠 Concetti chiave (forensic watermarking)

Un **watermark digitale** è un’informazione incorporata nell’immagine in modo da risultare:

- **impercettibile** (invisibile),
- **persistente** dopo trasformazioni comuni (robustezza),
- **estraibile e verificabile** con una procedura dedicata.

In Aegis, il watermark serve a supportare:
- identificazione del mittente/destinatario iniziale,
- tracciabilità della catena di distribuzione,
- attribuzione forense in caso di leak.

---

## 🛠️ Tecnologie e dipendenze

### Backend
- **Python + Flask** (API REST)
- **OpenCV** / **Pillow** (image processing)
- **reedsolo** (Reed–Solomon ECC)
- **flask-cors** (CORS)

### Frontend
- **Flutter (Dart)** — app mobile cross-platform

### Admin page
- **HTML/JavaScript** — pagina di verifica via POST

---

## 📦 Installazione

### 1) Clona il repository
```bash
git clone https://github.com/chiarasivieri/AEGIS.git
cd AEGIS
