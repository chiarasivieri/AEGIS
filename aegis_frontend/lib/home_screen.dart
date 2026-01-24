import 'dart:io';
import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'api_service.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  File? _selectedImage;          // Immagine originale (File)
  Uint8List? _resultImageBytes;  // Immagine elaborata (Bytes dalla memoria)
  bool _isLoading = false;
  
  final ApiService _api = ApiService();
  final TextEditingController _msgController = TextEditingController();
  
  // Algoritmo selezionato (default: Spread Spectrum)
  String _selectedAlgo = 'ss'; 

  // Funzione per scegliere immagine
  Future<void> _pickImage() async {
    final picker = ImagePicker();
    final pickedFile = await picker.pickImage(source: ImageSource.gallery);
    
    if (pickedFile != null) {
      setState(() {
        _selectedImage = File(pickedFile.path);
        _resultImageBytes = null; // Reset risultato precedente
      });
    }
  }

  // Funzione per inviare al server
  Future<void> _processImage() async {
    if (_selectedImage == null) return;

    setState(() => _isLoading = true);

    // Chiamata all'API
    final result = await _api.applyWatermark(
      _selectedImage!,
      _selectedAlgo,
      _msgController.text.isEmpty ? "SECRET" : _msgController.text,
    );

    setState(() {
      _resultImageBytes = result;
      _isLoading = false;
    });
    
    if (result == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("Errore durante l'elaborazione")),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("CyberSec Watermark")),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          children: [
            // --- SEZIONE 1: IMMAGINE ---
            Container(
              height: 250,
              width: double.infinity,
              decoration: BoxDecoration(
                color: Colors.grey[200],
                border: Border.all(color: Colors.grey),
              ),
              child: _resultImageBytes != null
                  ? Image.memory(_resultImageBytes!, fit: BoxFit.contain) // Mostra risultato
                  : _selectedImage != null
                      ? Image.file(_selectedImage!, fit: BoxFit.contain)  // Mostra originale
                      : const Center(child: Text("Nessuna immagine")),
            ),
            const SizedBox(height: 10),
            
            ElevatedButton.icon(
              onPressed: _pickImage,
              icon: const Icon(Icons.photo),
              label: const Text("Scegli dalla Galleria"),
            ),

            const Divider(height: 30),

            // --- SEZIONE 2: CONTROLLI ---
            const Text("Scegli Algoritmo:", style: TextStyle(fontWeight: FontWeight.bold)),
            
            RadioListTile(
              title: const Text("Least Significant Bit (LSB)"),
              subtitle: const Text("Invisibile, bassa robustezza"),
              value: 'lsb',
              groupValue: _selectedAlgo,
              onChanged: (v) => setState(() => _selectedAlgo = v!),
            ),
            RadioListTile(
              title: const Text("DCT (Frequenze)"),
              subtitle: const Text("Media robustezza JPEG"),
              value: 'dct',
              groupValue: _selectedAlgo,
              onChanged: (v) => setState(() => _selectedAlgo = v!),
            ),
            RadioListTile(
              title: const Text("Spread Spectrum (SS)"),
              subtitle: const Text("Alta sicurezza e robustezza"),
              value: 'ss',
              groupValue: _selectedAlgo,
              onChanged: (v) => setState(() => _selectedAlgo = v!),
            ),

            // Mostra input testo solo se NON è Spread Spectrum 
            // (Nello SS usiamo solo una chiave fissa per ora)
            if (_selectedAlgo != 'ss')
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 10),
                child: TextField(
                  controller: _msgController,
                  decoration: const InputDecoration(
                    labelText: "Messaggio da nascondere",
                    border: OutlineInputBorder(),
                  ),
                ),
              ),

            const SizedBox(height: 20),

            // --- PULSANTE AZIONE ---
            SizedBox(
              width: double.infinity,
              height: 50,
              child: ElevatedButton(
                style: ElevatedButton.styleFrom(backgroundColor: Colors.blueAccent),
                onPressed: (_selectedImage != null && !_isLoading) ? _processImage : null,
                child: _isLoading 
                  ? const CircularProgressIndicator(color: Colors.white)
                  : const Text("APPLICA WATERMARK", style: TextStyle(color: Colors.white)),
              ),
            ),
          ],
        ),
      ),
    );
  }
}