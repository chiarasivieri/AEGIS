import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'main.dart';
import 'register_page.dart';

class LoginPage extends StatefulWidget {
  @override
  _LoginPageState createState() => _LoginPageState();
}

class _LoginPageState extends State<LoginPage> {
  final _userController = TextEditingController();
  final _passController = TextEditingController();
  String errorMessage = "";

  Future<void> login() async {
    try {
      var response = await http.post(
        Uri.parse('http://127.0.0.1:5001/login'),
        headers: {"Content-Type": "application/json"},
        body: jsonEncode({
          "username": _userController.text.toLowerCase().trim(),
          "password": _passController.text,
        }),
      );

      if (response.statusCode == 200) {
        var data = jsonDecode(response.body);
        Navigator.pushReplacement(
          context,
          MaterialPageRoute(
            builder: (context) => MyHomePage(
              userCode: data['user_code'], 
              username: data['username']
            ),
          ),
        );
      } else {
        setState(() => errorMessage = "Credenziali sbagliate");
      }
    } catch (e) {
      setState(() => errorMessage = "Server non raggiungibile (python acceso?)");
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text("Login Aegis")),
      body: Padding(
        padding: EdgeInsets.all(20),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.security, size: 80, color: Colors.indigo),
            SizedBox(height: 20),
            TextField(controller: _userController, decoration: InputDecoration(labelText: "Username")),
            TextField(controller: _passController, obscureText: true, decoration: InputDecoration(labelText: "Password")),
            SizedBox(height: 20),
            ElevatedButton(onPressed: login, child: Text("ACCEDI")),
            TextButton(
              onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => RegisterPage())),
              child: Text("Non hai un account? Registrati"),
            ),
            Text(errorMessage, style: TextStyle(color: Colors.red))
          ],
        ),
      ),
    );
  }
}