
---

```markdown
# Aegis: Framework per la Condivisione Sicura di Immagini tramite Digital Watermarking

## Descrizione del Progetto
Aegis è un proof-of-concept sviluppato nell'ambito del corso di Cybersecurity presso l'Alma Mater Studiorum - Università di Bologna. Il progetto affronta il problema della "non ripudiabilità" nella condivisione di contenuti sensibili, colmando il gap forense lasciato dalle comuni app di messaggistica.

Aegis introduce un sistema di watermarking invisibile che lega l'identità del mittente e del destinatario all'immagine stessa. L'obiettivo è trasformare l'immagine in una prova forense resiliente a manipolazioni quali compressione, ritaglio (cropping) e ricodifica.

## Architettura Tecnica
Il sistema adotta un'architettura Client-Server:

* **Backend (Python/Flask):** Motore forense che gestisce l'embedding e l'estrazione del watermark, le trasformate (DCT) e le API REST.
* **Frontend (Dart/Flutter):** Applicazione mobile cross-platform per l'upload sicuro e la gestione utente.

### Algoritmo Proprietario: Aegis Combo (Dual Layer)
Il core del progetto è la classe `ComboWatermark`, che implementa una strategia a doppia difesa:

1.  **Layer Robusto (DCT):** L'immagine viene trasformata nel dominio delle frequenze. Il watermark viene inserito nei coefficienti della trasformata del coseno, garantendo resistenza alla compressione JPEG e al ridimensionamento.
2.  **Layer Integrità (LSB):** Sull'immagine risultante viene applicata una steganografia LSB (Least Significant Bit) per la verifica rapida dell'integrità bit-exact.
3.  **Resilienza al Cropping:** L'algoritmo utilizza una tecnica di *Tiling* (ripetizione della firma) e *Grid Search* (scansione a finestra mobile) per recuperare la firma anche da immagini parzialmente ritagliate.

## Struttura della Repository

```text
/
├── aegis_backend/          # Server API e Logica Forense
│   ├── venv/               # Ambiente virtuale Python
│   ├── app.py              # Entry point Flask e routing
│   ├── algorithms.py       # Implementazione classi LSB, DCT e Combo
│   ├── requirements.txt    # Dipendenze del progetto
│   └── admin_check.html    # Interfaccia di verifica per analisti
│
├── aegis_frontend/         # Applicazione Mobile (Flutter)
│   ├── lib/
│   │   ├── main.dart       # Entry point applicazione
│   │   └── ...             # Widget e logica UI
│   └── pubspec.yaml        # Gestione pacchetti Dart
│
└── report_and_slides/      # Documentazione
    ├── AEGIS.pdf           # Relazione tecnica completa
    └── AEGIS_slides.pdf    # Presentazione del progetto

```

## Requisiti di Sistema

* **Backend:** Python 3.8+, OpenCV, NumPy, Flask.
* **Frontend:** Flutter SDK 3.0+.

## Installazione e Avvio

### 1. Configurazione del Backend

Navigare nella cartella del server, attivare l'ambiente virtuale e installare le dipendenze.

```bash
cd aegis_backend

# Creazione virtual environment (se non presente)
python -m venv venv

# Attivazione (Windows)
.\venv\Scripts\activate
# Attivazione (Mac/Linux)
source venv/bin/activate

# Installazione dipendenze
pip install -r requirements.txt

# Avvio del server
python app.py

```

Il server sarà attivo all'indirizzo `http://127.0.0.1:5001`.

### 2. Configurazione del Frontend

Navigare nella cartella dell'applicazione Flutter e avviare l'app.

**Nota:** Per i test su emulatore Android, le chiamate API sono configurate su `10.0.2.2` (alias di localhost per Android).

```bash
cd aegis_frontend
flutter pub get
flutter run

```

## Utilizzo

1. **Marcatura (Embedding):** Tramite l'app mobile, selezionare un'immagine e un destinatario. Il backend applicherà l'algoritmo *Combo*.
2. **Verifica Forense:** Utilizzare il file `admin_check.html` o l'apposita sezione dell'app per caricare un'immagine sospetta.
3. **Analisi:** Il sistema restituirà i payload estratti (ID Mittente/Destinatario) e la tecnica rilevata.

## Disclaimer

Questo software è stato sviluppato a scopo puramente didattico e accademico. L'efficacia forense del watermarking non è garantita per utilizzi legali in ambienti di produzione senza ulteriori certificazioni.

## Autori

* **Marzia De Maina**
* **Chiara Sivieri**

Alma Mater Studiorum - Università di Bologna
Corso di Cybersecurity - A.A. 2025/2026

```

```