import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:webview_flutter/webview_flutter.dart';

const _widgetChannel = MethodChannel('grace_mobile/widget');
const _defaultServer = String.fromEnvironment('GRACE_SERVER_URL');

void main() => runApp(const GraceMobileApp());

class GraceMobileApp extends StatelessWidget {
  const GraceMobileApp({super.key});

  @override
  Widget build(BuildContext context) => MaterialApp(
        title: 'G.R.A.C.E.',
        theme: ThemeData(
          colorScheme: ColorScheme.fromSeed(
            seedColor: const Color(0xff55e8ff),
            brightness: Brightness.dark,
          ),
          useMaterial3: true,
        ),
        home: const DashboardPage(),
      );
}

class DashboardPage extends StatefulWidget {
  const DashboardPage({super.key});

  @override
  State<DashboardPage> createState() => _DashboardPageState();
}

class _DashboardPageState extends State<DashboardPage> {
  late final WebViewController _controller;
  String _server = _defaultServer;
  int _progress = 0;
  String? _pendingPreset;

  @override
  void initState() {
    super.initState();
    _controller = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setNavigationDelegate(NavigationDelegate(
        onProgress: (value) => setState(() => _progress = value),
        onPageFinished: (_) => _applyPendingPreset(),
      ));
    _widgetChannel.setMethodCallHandler((call) async {
      if (call.method == 'applyPreset' && call.arguments is String) {
        _pendingPreset = call.arguments as String;
        await _applyPendingPreset();
      }
    });
    _widgetChannel.invokeMethod<String>('initialPreset').then((preset) {
      _pendingPreset = preset;
    });
    if (_server.isNotEmpty) _loadServer(_server);
  }

  Future<void> _loadServer(String value) async {
    final normalized = value.trim().replaceFirst(RegExp(r'/+$'), '');
    final uri = Uri.tryParse(normalized);
    if (normalized.isEmpty || uri == null || !uri.isAbsolute || uri.host.isEmpty) return;
    setState(() => _server = normalized);
    await _controller.loadRequest(uri);
  }

  Future<void> _applyPendingPreset() async {
    final preset = _pendingPreset;
    if (preset == null) return;
    _pendingPreset = null;
    await _controller.runJavaScript(
      "window.applyLightPreset && window.applyLightPreset(${jsonEncode(preset)});",
    );
  }

  Future<void> _editServer() async {
    final input = TextEditingController(text: _server);
    final url = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('G.R.A.C.E. server'),
        content: TextField(
          controller: input,
          keyboardType: TextInputType.url,
          decoration: const InputDecoration(
            hintText: 'https://192.168.1.20:8443',
            helperText: 'Use your server’s LAN URL.',
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.pop(context, input.text), child: const Text('Connect')),
        ],
      ),
    );
    input.dispose();
    if (url != null) await _loadServer(url);
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(
          title: const Text('G.R.A.C.E.'),
          actions: [IconButton(onPressed: _editServer, icon: const Icon(Icons.settings), tooltip: 'Server address')],
          bottom: _progress < 100 ? PreferredSize(
            preferredSize: const Size.fromHeight(2),
            child: LinearProgressIndicator(value: _progress / 100),
          ) : null,
        ),
        body: _server.isEmpty
            ? Center(child: FilledButton.icon(onPressed: _editServer, icon: const Icon(Icons.link), label: const Text('Connect to G.R.A.C.E.')))
            : WebViewWidget(controller: _controller),
      );
}
