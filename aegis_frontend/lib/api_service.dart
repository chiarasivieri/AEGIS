import 'dart:io';
import 'dart:typed_data';
import 'package:http/http.dart' as http;

class ApiService {
  // Per iOS Simulator usa 127.0.0.1
  // Per Android Emulator usa 10.0.2.2
  static const String baseUrl = "http://127.0.0.1:5000";

  Future<Uint8List?> applyWatermark(File imageFile, String type, String message) async {
    var uri = Uri.parse("$baseUrl/apply");
    var request = http.MultipartRequest('POST', uri);

    request.fields['type'] = type;
    request.fields['message'] = message;
    
    request.files.add(await http.MultipartFile.fromPath(
      'image', 
      imageFile.path,
    ));

    try {
      var response = await request.send();
      if (response.statusCode == 200) {
        return await response.stream.toBytes();
      } else {
        print("Errore Server: ${response.statusCode}");
        return null;
      }
    } catch (e) {
      print("Errore Connessione: $e");
      return null;
    }
  }
}