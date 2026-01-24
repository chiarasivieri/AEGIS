import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

class RegisterPage extends StatefulWidget {
  @override
  _RegisterPageState createState() => _RegisterPageState();
}

class _RegisterPageState extends State<RegisterPage> {
  final _userController = TextEditingController();
  final _passController = TextEditingController();
  String message = "";

  Future<void> register() async {
    try {
      var response = await http.post(
        Uri.parse('http://127.0.0.1:5001/register'),
        headers: {"Content-Type": "application/json"},
        body: jsonEncode({
          "username": _userController.text.toLowerCase().trim(),
          "password": _passController.text,
        }),
      );

      if (response.statusCode == 200) {
        setState(() => message = "✅ Registrato! Torna indietro e fai Login.");
      } else {
        setState(() => message = "❌ Utente già esistente");
      }
    } catch (e) {
      setState(() => message = "Errore connessione");
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text("Registrazione")),
      body: Padding(
        padding: EdgeInsets.all(20),
        child: Column(
          children: [
            TextField(controller: _userController, decoration: InputDecoration(labelText: "Nuovo Username")),
            TextField(controller: _passController, obscureText: true, decoration: InputDecoration(labelText: "Password")),
            SizedBox(height: 20),
            ElevatedButton(onPressed: register, child: Text("REGISTRATI")),
            SizedBox(height: 20),
            Text(message, textAlign: TextAlign.center, style: TextStyle(fontWeight: FontWeight.bold)),
          ],
        ),
      ),
    );
  }
}