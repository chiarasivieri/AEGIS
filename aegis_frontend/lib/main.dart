import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:http/http.dart' as http;
import 'dart:io';
import 'dart:convert';
import 'package:url_launcher/url_launcher.dart';

// IMPORTA LA TUA PAGINA DI REGISTRAZIONE
// Assicurati che il file si chiami esattamente 'register_page.dart' e sia nella cartella lib/
import 'register_page.dart';

// CONFIGURAZIONE
// Usa 127.0.0.1 per Linux Desktop/Web.
// Se usi Emulatore Android, cambia in: "http://10.0.2.2:5001"
const String SERVER_IP = "http://127.0.0.1:5001"; 

void main() => runApp(MyApp());

class MyApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        primarySwatch: Colors.indigo,
        useMaterial3: true,
      ),
      home: LoginPage(),
    );
  }
}

// --- 1. LOGIN PAGE ---
class LoginPage extends StatefulWidget {
  @override
  _LoginPageState createState() => _LoginPageState();
}

class _LoginPageState extends State<LoginPage> {
  final _userCtrl = TextEditingController();
  final _passCtrl = TextEditingController();

  Future login() async {
    try {
      var res = await http.post(
        Uri.parse('$SERVER_IP/login'),
        headers: {"Content-Type": "application/json"},
        body: jsonEncode({
          "username": _userCtrl.text.trim(),
          "password": _passCtrl.text.trim()
        })
      );

      if (res.statusCode == 200) {
        var body = jsonDecode(res.body);
        Navigator.pushReplacement(
          context,
          MaterialPageRoute(builder: (context) => MyHomePage(
            userCode: body['user_code'],
            username: body['username']
          ))
        );
      } else {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Credenziali errate!")));
      }
    } catch (e) {
      print(e);
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Errore server: controlla che Python sia acceso")));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text("Aegis Login")),
      body: Padding(
        padding: EdgeInsets.all(20),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.security, size: 80, color: Colors.indigo),
            SizedBox(height: 20),
            TextField(controller: _userCtrl, decoration: InputDecoration(labelText: "Utente (es. chiara)", border: OutlineInputBorder())),
            SizedBox(height: 10),
            TextField(controller: _passCtrl, decoration: InputDecoration(labelText: "Password", border: OutlineInputBorder()), obscureText: true),
            SizedBox(height: 20),
            
            SizedBox(width: double.infinity, child: ElevatedButton(onPressed: login, child: Text("ACCEDI"))),
            
            SizedBox(height: 15),
            // --- PULSANTE REGISTRAZIONE AGGIUNTO ---
            TextButton(
              onPressed: () {
                Navigator.push(context, MaterialPageRoute(builder: (context) => RegisterPage()));
              }, 
              child: Text("Non hai un account? Registrati qui")
            )
          ],
        ),
      ),
    );
  }
}

// --- 2. HOME PAGE (3 SCHEDE) ---
class MyHomePage extends StatefulWidget {
  final String userCode;
  final String username;
  MyHomePage({required this.userCode, required this.username});

  @override
  _MyHomePageState createState() => _MyHomePageState();
}

class _MyHomePageState extends State<MyHomePage> {
  int _idx = 0;

  void logout() {
    Navigator.pushReplacement(context, MaterialPageRoute(builder: (context) => LoginPage()));
  }

  @override
  Widget build(BuildContext context) {
    // ELENCO DELLE 3 SCHEDE
    final List<Widget> _pages = [
      SendTab(username: widget.username),     // Tab 0: Invia
      InboxTab(username: widget.username, userCode: widget.userCode), // Tab 1: Posta
      VerifyTab(),                            // Tab 2: Verifica
    ];

    return Scaffold(
      appBar: AppBar(
        title: Text("Ciao, ${widget.username}"),
        backgroundColor: Colors.indigo,
        foregroundColor: Colors.white,
        actions: [IconButton(icon: Icon(Icons.exit_to_app), onPressed: logout, tooltip: "Esci")],
      ),
      body: _pages[_idx],
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _idx,
        onTap: (i) => setState(() => _idx = i),
        selectedItemColor: Colors.indigo,
        items: [
          BottomNavigationBarItem(icon: Icon(Icons.send), label: "Invia"),
          BottomNavigationBarItem(icon: Icon(Icons.lock), label: "Posta"), // Icona Lucchetto
          BottomNavigationBarItem(icon: Icon(Icons.manage_search), label: "Verifica"),
        ],
      ),
    );
  }
}

// --- TAB 1: INVIA ---
class SendTab extends StatefulWidget {
  final String username;
  SendTab({required this.username});
  @override
  _SendTabState createState() => _SendTabState();
}

class _SendTabState extends State<SendTab> {
  File? _img;
  final _recCtrl = TextEditingController();
  bool _loading = false;

  Future getImg() async {
    final f = await ImagePicker().pickImage(source: ImageSource.gallery);
    if (f != null) setState(() => _img = File(f.path));
  }

  Future send(String algo) async {
    if (_img == null || _recCtrl.text.isEmpty) {
       ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Manca foto o destinatario!")));
       return;
    }
    setState(() => _loading = true);

    var req = http.MultipartRequest('POST', Uri.parse('$SERVER_IP/request_transfer'));
    req.files.add(await http.MultipartFile.fromPath('image', _img!.path));
    req.fields['sender_name'] = widget.username;
    req.fields['receiver_name'] = _recCtrl.text.toLowerCase().trim();
    req.fields['algorithm'] = algo;

    try {
      var res = await req.send();
      if (res.statusCode == 200) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("✅ Inviato con successo!")));
        setState(() { _img = null; _recCtrl.clear(); });
      } else {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("❌ Errore (utente non trovato?)")));
      }
    } catch (e) { print(e); }
    setState(() => _loading = false);
  }

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: EdgeInsets.all(20),
      child: Column(
        children: [
          GestureDetector(
            onTap: getImg,
            child: Container(
              height: 200, 
              width: double.infinity,
              decoration: BoxDecoration(color: Colors.grey[200], borderRadius: BorderRadius.circular(10), border: Border.all(color: Colors.grey)),
              child: _img == null 
                ? Column(mainAxisAlignment: MainAxisAlignment.center, children:[Icon(Icons.camera_alt, size: 40), Text("Clicca per caricare")]) 
                : ClipRRect(borderRadius: BorderRadius.circular(10), child: Image.file(_img!, fit: BoxFit.cover)),
            ),
          ),
          SizedBox(height: 20),
          TextField(controller: _recCtrl, decoration: InputDecoration(labelText: "Destinatario", border: OutlineInputBorder())),
          SizedBox(height: 20),
          if (_loading) CircularProgressIndicator() else Column(
            children: [
              Row(children: [
                Expanded(child: ElevatedButton(onPressed: () => send('LSB'), child: Text("LSB"))),
                SizedBox(width: 10),
                Expanded(child: ElevatedButton(onPressed: () => send('DCT'), child: Text("DCT"))),
              ]),
              SizedBox(height: 10),
              SizedBox(width: double.infinity, child: ElevatedButton(onPressed: () => send('SS'), child: Text("Spread Spectrum"))),
              SizedBox(height: 15),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton.icon(
                  icon: Icon(Icons.lock_outline),
                  label: Text("INVIA BLINDATO (COMBO)"),
                  onPressed: () => send('COMBO'),
                  style: ElevatedButton.styleFrom(backgroundColor: Colors.purple[800], foregroundColor: Colors.white, padding: EdgeInsets.all(15)),
                ),
              )
            ],
          )
        ],
      ),
    );
  }
}

// --- TAB 2: POSTA (MODIFICATA: NO ANTEPRIMA) ---
class InboxTab extends StatefulWidget {
  final String username;
  final String userCode;
  InboxTab({required this.username, required this.userCode});
  @override
  _InboxTabState createState() => _InboxTabState();
}

class _InboxTabState extends State<InboxTab> {
  List data = [];
  bool isLoading = false;

  @override
  void initState() {
    super.initState();
    refresh();
  }

  Future refresh() async {
    setState(() => isLoading = true);
    try {
      var res = await http.post(
        Uri.parse('$SERVER_IP/my_pending'),
        headers: {"Content-Type": "application/json"},
        body: jsonEncode({ "username": widget.username, "user_code": widget.userCode })
      );
      if (res.statusCode == 200 && mounted) setState(() => data = jsonDecode(res.body));
    } catch (e) { print(e); } 
    finally { if (mounted) setState(() => isLoading = false); }
  }

  Future accept(String reqId) async {
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Applicazione firma in corso...")));
    try {
      var res = await http.post(
        Uri.parse('$SERVER_IP/accept_transfer'),
        headers: {"Content-Type": "application/json"},
        body: jsonEncode({"request_id": reqId})
      );
      if (res.statusCode == 200) {
        var body = jsonDecode(res.body);
        _showSuccessDialog(body['url'], body['signature']);
      }
    } catch (e) { print(e); }
  }

  void _showSuccessDialog(String url, String sig) {
    // STAMPA DI SICUREZZA NEL TERMINALE
    print("\n------------------------------------------------");
    print(">>> LINK DOWNLOAD: $url");
    print("------------------------------------------------\n");

    showDialog(context: context, builder: (_) => AlertDialog(
      title: Text("✅ Firma Applicata!"),
      content: Column(mainAxisSize: MainAxisSize.min, children: [
        Text("L'immagine è stata firmata."),
        Divider(),
        Text("Codice Firma:", style: TextStyle(fontSize: 12, color: Colors.grey)),
        SelectableText(sig, style: TextStyle(fontWeight: FontWeight.bold)),
        SizedBox(height: 20),
        ElevatedButton.icon(
          icon: Icon(Icons.download),
          label: Text("SCARICA ORA"),
          style: ElevatedButton.styleFrom(backgroundColor: Colors.green, foregroundColor: Colors.white),
          onPressed: () async {
            final uri = Uri.parse(url);
            if (await canLaunchUrl(uri)) {
              await launchUrl(uri, mode: LaunchMode.externalApplication);
            } else {
              print("Errore apertura browser. Copia il link dal terminale.");
            }
          }
        ),
        SizedBox(height: 10),
        Text("Se non apre il browser, guarda il terminale nero!", style: TextStyle(fontSize: 10, color: Colors.red)),
      ]),
      actions: [TextButton(child: Text("CHIUDI"), onPressed: () { Navigator.pop(context); refresh(); })],
    ));
  }

  @override
  Widget build(BuildContext context) {
    return Column(children: [
      Padding(padding: EdgeInsets.all(8), child: ElevatedButton.icon(onPressed: refresh, icon: Icon(Icons.refresh), label: Text("Aggiorna Posta"))),
      Expanded(
        child: isLoading ? Center(child: CircularProgressIndicator()) : ListView.builder(
            itemCount: data.length,
            itemBuilder: (ctx, i) {
               var item = data[i];
               return Card(
                elevation: 4,
                margin: EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                child: Column(
                  children: [
                    // --- ZONA CRITTOGRAFATA (NASCONDE L'IMMAGINE) ---
                    Container(
                      height: 120,
                      width: double.infinity,
                      decoration: BoxDecoration(
                        color: Colors.grey[300],
                        borderRadius: BorderRadius.vertical(top: Radius.circular(4))
                      ),
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.lock, size: 40, color: Colors.grey[700]),
                          SizedBox(height: 5),
                          Text("IMMAGINE PROTETTA", style: TextStyle(fontWeight: FontWeight.bold, color: Colors.grey[800])),
                          Text("Accetta per rivelare e scaricare", style: TextStyle(fontSize: 12, color: Colors.grey[600])),
                        ],
                      ),
                    ),
                    ListTile(
                      title: Text("Da: ${item['sender']}"),
                      subtitle: Text("Metodo richiesto: ${item['algo']}"),
                      trailing: ElevatedButton(
                        child: Text("ACCETTA"), 
                        onPressed: () => accept(item['request_id']),
                        style: ElevatedButton.styleFrom(backgroundColor: Colors.indigo, foregroundColor: Colors.white),
                      ),
                    ),
                  ],
                ),
              );
            },
          ),
      )
    ]);
  }
}

// --- TAB 3: VERIFICA (STRESS TEST) ---
class VerifyTab extends StatefulWidget {
  @override
  _VerifyTabState createState() => _VerifyTabState();
}

class _VerifyTabState extends State<VerifyTab> {
  File? _img;
  String _result = "";
  bool _loading = false;

  Future pickImage() async {
    final f = await ImagePicker().pickImage(source: ImageSource.gallery);
    if (f != null) setState(() { _img = File(f.path); _result = ""; });
  }

  Future verify() async {
    if (_img == null) return;
    setState(() => _loading = true);

    var req = http.MultipartRequest('POST', Uri.parse('$SERVER_IP/verify'));
    req.files.add(await http.MultipartFile.fromPath('image', _img!.path));

    try {
      var res = await req.send();
      var respStr = await res.stream.bytesToString();
      var body = jsonDecode(respStr);

      setState(() {
        if (body['found'] == true) {
          _result = "✅ FIRMA TROVATA!\n\n"
                    "Mittente: ${body['sender']}\n"
                    "Destinatario: ${body['receiver']}\n"
                    "Tecnica: ${body['technique']}\n"
                    "Raw: ${body['watermark']}";
        } else {
          _result = "❌ NESSUNA FIRMA.\nIl file è pulito o troppo danneggiato.\nDettagli grezzi: ${body['watermark']}";
        }
      });
    } catch (e) {
      setState(() => _result = "Errore: $e");
    }
    setState(() => _loading = false);
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.all(20),
      child: Column(
        children: [
          Text("Stress Test & Verifica", style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
          SizedBox(height: 10),
          Text("Carica un'immagine sospetta/modificata per cercare la firma.", textAlign: TextAlign.center, style: TextStyle(color: Colors.grey)),
          SizedBox(height: 20),
          GestureDetector(
            onTap: pickImage,
            child: Container(
              height: 150, width: double.infinity,
              decoration: BoxDecoration(color: Colors.grey[200], border: Border.all(color: Colors.grey), borderRadius: BorderRadius.circular(10)),
              child: _img == null 
                ? Column(mainAxisAlignment: MainAxisAlignment.center, children: [Icon(Icons.upload_file, size: 40), Text("Carica immagine")])
                : Image.file(_img!, fit: BoxFit.cover),
            ),
          ),
          SizedBox(height: 20),
          if (_loading) CircularProgressIndicator()
          else SizedBox(width: double.infinity, child: ElevatedButton.icon(icon: Icon(Icons.search), label: Text("ANALIZZA ORA"), onPressed: verify, style: ElevatedButton.styleFrom(backgroundColor: Colors.indigo, foregroundColor: Colors.white, padding: EdgeInsets.all(15)))),
          SizedBox(height: 20),
          if (_result.isNotEmpty) Container(
            padding: EdgeInsets.all(15),
            width: double.infinity,
            color: _result.contains("✅") ? Colors.green[50] : Colors.red[50],
            child: Text(_result, style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
          )
        ],
      ),
    );
  }
}