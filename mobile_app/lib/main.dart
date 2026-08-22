import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
const _defaultServer = String.fromEnvironment(
  'GRACE_SERVER_URL',
  defaultValue: 'https://10.0.0.5:8443',
);
const _homeAssistantUrl = String.fromEnvironment('GRACE_HOME_ASSISTANT_URL');
const _homeAssistantToken = String.fromEnvironment('GRACE_HOME_ASSISTANT_TOKEN');
const _smartSwitchEntityId = String.fromEnvironment('GRACE_SMART_SWITCH_ENTITY_ID');
const _smartSwitchName = String.fromEnvironment('GRACE_SMART_SWITCH_NAME', defaultValue: 'Smart light');

const _bg = Color(0xff060a12);
const _surface = Color(0xff0c1421);
const _raised = Color(0xff111f31);
const _ink = Color(0xffeef7ff);
const _muted = Color(0xff8ba0b6);
const _cyan = Color(0xff55e8ff);
const _violet = Color(0xff9b8cff);
const _coral = Color(0xffff6d73);
final _homeAssistant = HomeAssistantApi(url: _homeAssistantUrl, token: _homeAssistantToken, entityId: _smartSwitchEntityId, name: _smartSwitchName);

const _lights = [
  HomeAssistantLight('Bedroom Main Lightswitch', 'switch.bedroom_main_lightswitch'),
  HomeAssistantLight('Dining Room Light', 'switch.dining_room_light'),
  HomeAssistantLight('Kitchen Light', 'switch.kitchen_light'),
  HomeAssistantLight('Living Room Light', 'switch.living_room_light'),
  HomeAssistantLight('Stair Light', 'switch.stair_light'),
];
const _lightingPresets = [
  LightingPreset('Bedtime', {}),
  LightingPreset('Wind down', {'switch.bedroom_main_lightswitch'}),
  LightingPreset('Movie time', {'switch.stair_light'}),
  LightingPreset('Getting home', {'switch.dining_room_light', 'switch.kitchen_light', 'switch.living_room_light', 'switch.stair_light'}),
];

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  SystemChrome.setEnabledSystemUIMode(SystemUiMode.edgeToEdge);
  SystemChrome.setSystemUIOverlayStyle(const SystemUiOverlayStyle(
    statusBarColor: Colors.transparent,
    statusBarIconBrightness: Brightness.light,
    systemNavigationBarColor: Colors.transparent,
    systemNavigationBarIconBrightness: Brightness.light,
    systemStatusBarContrastEnforced: false,
    systemNavigationBarContrastEnforced: false,
  ));
  runApp(const GraceMobileApp());
}

class GraceMobileApp extends StatefulWidget {
  const GraceMobileApp({super.key});

  @override
  State<GraceMobileApp> createState() => _GraceMobileAppState();
}

class _GraceMobileAppState extends State<GraceMobileApp> {
  final _api = GraceApi(_defaultServer);
  Map<String, dynamic>? _user;
  String? _error;

  @override
  void initState() {
    super.initState();
    _restoreSession();
  }

  Future<void> _restoreSession() async {
    try {
      final user = await _api.get('/api/auth/me');
      if (user['authenticated'] == true) setState(() => _user = user);
    } catch (_) {
      setState(() => _error = 'G.R.A.C.E. could not reach the local server.');
    }
  }

  @override
  Widget build(BuildContext context) => MaterialApp(
        title: 'G.R.A.C.E.',
        debugShowCheckedModeBanner: false,
        theme: ThemeData(
          brightness: Brightness.dark,
          scaffoldBackgroundColor: _bg,
          colorScheme: const ColorScheme.dark(primary: _cyan, surface: _surface),
          fontFamily: 'sans-serif',
          useMaterial3: true,
        ),
        home: _user == null
            ? LoginPage(api: _api, error: _error, onSignedIn: (user) => setState(() => _user = user))
            : GraceDashboard(
                api: _api,
                user: _user!,
                onLogout: () => setState(() => _user = null),
              ),
      );
}

class GraceApi {
  GraceApi(this.server);

  String server;
  final Map<String, String> _cookies = {};

  Uri _url(String path) => Uri.parse('${server.replaceFirst(RegExp(r'/+$'), '')}$path');

  Future<dynamic> get(String path) => path == '/api/devices/smart-switch' ? _homeAssistant.getSwitch() : _request('GET', path);
  Future<dynamic> post(String path, [Object? body]) => path == '/api/devices/smart-switch/toggle' ? _homeAssistant.toggle() : _request('POST', path, body);
  Future<dynamic> put(String path, [Object? body]) => _request('PUT', path, body);
  Future<dynamic> delete(String path) => _request('DELETE', path);

  Future<dynamic> _request(String method, String path, [Object? body]) async {
    final client = HttpClient();
    client.badCertificateCallback = (_, __, ___) => true;
    client.connectionTimeout = const Duration(seconds: 8);
    try {
      final request = await client.openUrl(method, _url(path));
      request.headers.set(HttpHeaders.acceptHeader, 'application/json');
      if (_cookies.isNotEmpty) request.headers.set(HttpHeaders.cookieHeader, _cookies.entries.map((item) => '${item.key}=${item.value}').join('; '));
      if (body != null) {
        request.headers.contentType = ContentType.json;
        request.write(jsonEncode(body));
      }
      final response = await request.close();
      for (final cookie in response.cookies) {
        if (cookie.expires != null && cookie.expires!.isBefore(DateTime.now())) {
          _cookies.remove(cookie.name);
        } else {
          _cookies[cookie.name] = cookie.value;
        }
      }
      final text = await utf8.decoder.bind(response).join();
      final data = text.isEmpty ? <String, dynamic>{} : jsonDecode(text);
      if (response.statusCode < 200 || response.statusCode >= 300) {
        throw GraceApiException(data is Map ? '${data['detail'] ?? data['error'] ?? 'Request failed (${response.statusCode})'}' : 'Request failed (${response.statusCode})');
      }
      return data;
    } on SocketException {
      throw GraceApiException('Unable to reach your local G.R.A.C.E. server.');
    } on HandshakeException {
      throw GraceApiException('The G.R.A.C.E. certificate is not trusted on this phone.');
    } finally {
      client.close(force: true);
    }
  }
}

class HomeAssistantApi {
  const HomeAssistantApi({required this.url, required this.token, required this.entityId, required this.name});
  final String url;
  final String token;
  final String entityId;
  final String name;

  bool get isConfigured => url.isNotEmpty && token.isNotEmpty;

  Future<Map<String, dynamic>> getSwitch([String? targetEntityId, String? fallbackName]) async {
    final switchEntityId = targetEntityId ?? entityId;
    final switchName = fallbackName ?? name;
    if (!isConfigured || !switchEntityId.startsWith('switch.')) return _unavailable(switchName, 'Add Home Assistant build settings to the mobile app.');
    try {
      final data = Map<String, dynamic>.from(await _request('GET', '/api/states/$switchEntityId'));
      return {'available': data['state'] == 'on' || data['state'] == 'off', 'name': data['attributes']?['friendly_name'] ?? switchName, 'state': data['state'] ?? 'unavailable', 'message': 'Connected directly to Home Assistant.'};
    } catch (error) { return _unavailable(switchName, '$error'); }
  }

  Future<Map<String, dynamic>> toggle() async {
    if (!isConfigured || !entityId.startsWith('switch.')) return _unavailable(name, 'Add Home Assistant build settings to the mobile app.');
    try { await _request('POST', '/api/services/switch/toggle', {'entity_id': entityId}); return getSwitch(); }
    catch (error) { return _unavailable(name, '$error'); }
  }

  Future<void> setSwitches(Set<String> entityIds, {required bool on}) async {
    if (!isConfigured) throw GraceApiException('Add Home Assistant build settings to the mobile app.');
    if (entityIds.isEmpty) return;
    await _request('POST', '/api/services/switch/${on ? 'turn_on' : 'turn_off'}', {'entity_id': entityIds.toList()});
  }

  Map<String, dynamic> _unavailable(String switchName, String message) => {'available': false, 'name': switchName, 'state': 'unavailable', 'message': message};

  Future<dynamic> _request(String method, String path, [Object? body]) async {
    final client = HttpClient();
    client.badCertificateCallback = (_, __, ___) => true;
    client.connectionTimeout = const Duration(seconds: 8);
    try {
      final request = await client.openUrl(method, Uri.parse('${url.replaceFirst(RegExp(r'/+$'), '')}$path'));
      request.headers.set(HttpHeaders.authorizationHeader, 'Bearer $token');
      request.headers.set(HttpHeaders.acceptHeader, 'application/json');
      if (body != null) { request.headers.contentType = ContentType.json; request.write(jsonEncode(body)); }
      final response = await request.close().timeout(const Duration(seconds: 8));
      final text = await utf8.decoder.bind(response).join().timeout(const Duration(seconds: 8));
      if (response.statusCode < 200 || response.statusCode >= 300) throw GraceApiException('Home Assistant request failed (${response.statusCode}).');
      return text.isEmpty ? <String, dynamic>{} : jsonDecode(text);
    } on SocketException { throw GraceApiException('Unable to reach Home Assistant from this phone.'); }
    on TimeoutException { throw GraceApiException('Home Assistant did not respond within 8 seconds.'); }
    finally { client.close(force: true); }
  }
}

class GraceApiException implements Exception {
  GraceApiException(this.message);
  final String message;
  @override
  String toString() => message;
}

class OrbitBackground extends StatelessWidget {
  const OrbitBackground({super.key, required this.child});
  final Widget child;

  @override
  Widget build(BuildContext context) => Container(
        decoration: const BoxDecoration(
          gradient: RadialGradient(colors: [Color(0x269b8cff), _bg], center: Alignment(0.8, -0.95), radius: 1.2),
        ),
        child: Stack(children: [
          Positioned(top: -100, right: -125, child: _Orbit(size: 310, color: _cyan)),
          Positioned(top: 300, left: -245, child: _Orbit(size: 420, color: _violet)),
          Positioned(bottom: 42, right: -108, child: _Orbit(size: 220, color: _cyan)),
          child,
        ]),
      );
}

class _Orbit extends StatelessWidget {
  const _Orbit({required this.size, required this.color});
  final double size;
  final Color color;
  @override
  Widget build(BuildContext context) => Container(
        width: size,
        height: size,
        decoration: BoxDecoration(shape: BoxShape.circle, border: Border.all(color: color.withOpacity(.13))),
      );
}

class GraceCore extends StatelessWidget {
  const GraceCore({super.key, this.size = 42});
  final double size;
  @override
  Widget build(BuildContext context) => Container(
        width: size,
        height: size,
        decoration: BoxDecoration(shape: BoxShape.circle, border: Border.all(color: _cyan, width: 2), boxShadow: [BoxShadow(color: _cyan.withOpacity(.35), blurRadius: 20)]),
        child: Center(child: Container(width: size * .42, height: size * .42, decoration: BoxDecoration(shape: BoxShape.circle, border: Border.all(color: _violet, width: 2)))),
      );
}

class LoginPage extends StatefulWidget {
  const LoginPage({super.key, required this.api, required this.error, required this.onSignedIn});
  final GraceApi api;
  final String? error;
  final ValueChanged<Map<String, dynamic>> onSignedIn;
  @override
  State<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends State<LoginPage> {
  final _username = TextEditingController();
  final _password = TextEditingController();
  bool _signup = false;
  bool _remember = false;
  bool _busy = false;
  String? _status;

  Future<void> _submit() async {
    if (_username.text.trim().isEmpty || _password.text.isEmpty) return;
    setState(() { _busy = true; _status = null; });
    try {
      if (_signup) {
        await widget.api.post('/api/auth/signup', {'username': _username.text.trim(), 'password': _password.text});
        setState(() { _signup = false; _status = 'Account created. Sign in when ready.'; });
      } else {
        final user = Map<String, dynamic>.from(await widget.api.post('/api/auth/login', {'username': _username.text.trim(), 'password': _password.text, 'remember_me': _remember}));
        widget.onSignedIn(user);
      }
    } catch (error) {
      setState(() => _status = '$error');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        body: OrbitBackground(
          child: SafeArea(
            child: Center(
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(22),
                child: GraceCard(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                    const Row(children: [GraceCore(size: 58), SizedBox(width: 16), Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text('G.R.A.C.E.', style: TextStyle(fontSize: 19, fontWeight: FontWeight.w900, letterSpacing: 3)), Text('Private local intelligence', style: TextStyle(color: _muted))])]),
                    const SizedBox(height: 26),
                    Text(_signup ? 'Create a local account.' : 'Good evening. Ready when you are.'),
                    const SizedBox(height: 16),
                    Row(children: [Expanded(child: GraceButton(label: 'Sign in', selected: !_signup, onPressed: () => setState(() => _signup = false))), const SizedBox(width: 6), Expanded(child: GraceButton(label: 'Create account', selected: _signup, onPressed: () => setState(() => _signup = true)))]),
                    GraceField(controller: _username, label: 'Username'),
                    GraceField(controller: _password, label: 'Password', obscure: true),
                    if (!_signup) SwitchListTile.adaptive(contentPadding: EdgeInsets.zero, title: const Text('Keep me signed in', style: TextStyle(fontSize: 14, color: _muted)), value: _remember, onChanged: (value) => setState(() => _remember = value)),
                    GraceButton(label: _signup ? 'Create account' : 'Sign in', primary: true, busy: _busy, onPressed: _submit),
                    if (_status ?? widget.error case final text?) Padding(padding: const EdgeInsets.only(top: 14), child: Text(text, style: const TextStyle(color: _muted))),
                  ]),
                ),
              ),
            ),
          ),
        ),
      );
}

class GraceDashboard extends StatefulWidget {
  const GraceDashboard({super.key, required this.api, required this.user, required this.onLogout});
  final GraceApi api;
  final Map<String, dynamic> user;
  final VoidCallback onLogout;
  @override
  State<GraceDashboard> createState() => _GraceDashboardState();
}

class _GraceDashboardState extends State<GraceDashboard> {
  int _index = 0;
  @override
  Widget build(BuildContext context) {
    final pages = [HomePage(api: widget.api, onNavigate: (index) => setState(() => _index = index)), ChatPage(api: widget.api), ControlPage(api: widget.api), AccountPage(api: widget.api, user: widget.user, onLogout: widget.onLogout)];
    return Scaffold(
      body: OrbitBackground(child: SafeArea(child: AnimatedSwitcher(
        duration: const Duration(milliseconds: 180),
        child: KeyedSubtree(key: ValueKey(_index), child: pages[_index]),
      ))),
      bottomNavigationBar: NavigationBar(
        height: 68,
        backgroundColor: const Color(0xff08101c),
        indicatorColor: _cyan.withOpacity(.12),
        selectedIndex: _index,
        onDestinationSelected: (value) => setState(() => _index = value),
        destinations: const [NavigationDestination(icon: Icon(Icons.home_outlined), selectedIcon: Icon(Icons.home), label: 'Home'), NavigationDestination(icon: Icon(Icons.all_inclusive), label: 'Ask'), NavigationDestination(icon: Icon(Icons.grid_view_outlined), label: 'Control'), NavigationDestination(icon: Icon(Icons.person_outline), selectedIcon: Icon(Icons.person), label: 'You')],
      ),
    );
  }
}

class HomePage extends StatefulWidget {
  const HomePage({super.key, required this.api, required this.onNavigate});
  final GraceApi api;
  final ValueChanged<int> onNavigate;
  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  String _summary = 'Loading your workspace…';
  @override
  void initState() { super.initState(); _load(); }
  Future<void> _load() async { try { final data = await widget.api.get('/api/status'); if (mounted) setState(() => _summary = '${data['memory_count']} memories · watch mode ${data['watch_mode'] == true ? 'active' : 'standing by'} · music ${data['music']['status']}'); } catch (error) { if (mounted) setState(() => _summary = '$error'); } }
  @override
  Widget build(BuildContext context) => GracePage(child: ListView(children: [
    Padding(padding: const EdgeInsets.fromLTRB(4, 8, 4, 32), child: Row(children: [const GraceCore(size: 48), const SizedBox(width: 12), const Text('G.R.A.C.E.', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w900, letterSpacing: 4)), const Spacer(), CircleAvatar(radius: 25, backgroundColor: _surface, child: const Text('A', style: TextStyle(color: _ink, fontSize: 21, fontWeight: FontWeight.bold)))])),
    const Padding(padding: EdgeInsets.fromLTRB(4, 0, 4, 14), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text('Good evening.', style: TextStyle(fontSize: 34, fontWeight: FontWeight.w800, height: 1.05)), SizedBox(height: 7), Text('Generally Reliable Assistant for Computing and Engineering', style: TextStyle(color: _muted))])),
    GraceButton(icon: Icons.all_inclusive, label: 'Ask G.R.A.C.E.\nWhat do you need?', alignStart: true, onPressed: () => widget.onNavigate(1)),
    const SizedBox(height: 12),
    GridView.count(crossAxisCount: 2, shrinkWrap: true, physics: const NeverScrollableScrollPhysics(), mainAxisSpacing: 10, crossAxisSpacing: 10, childAspectRatio: 1.45, children: [ToolTile(icon: Icons.mic_none, title: 'Voice', subtitle: 'Talk with G.R.A.C.E.', onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => VoicePage(api: widget.api)))), ToolTile(icon: Icons.cloud_outlined, title: 'Weather', subtitle: 'Check conditions', onTap: () => _feature('weather')), ToolTile(icon: Icons.music_note, title: 'Music', subtitle: 'Open controls', onTap: () => _feature('music')), ToolTile(icon: Icons.auto_awesome, title: 'Create', subtitle: 'Generate an image', onTap: () => _feature('images'))]),
    const SizedBox(height: 10),
    DeviceHomeCard(onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const LightingPage()))),
    GraceCard(child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [const Icon(Icons.memory, color: _cyan), const SizedBox(width: 12), Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [const Text('SYSTEM STATE', style: TextStyle(color: _cyan, fontSize: 11, fontWeight: FontWeight.bold, letterSpacing: 1.5)), const SizedBox(height: 4), const Text('All systems nominal', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18)), const SizedBox(height: 6), Text(_summary, style: const TextStyle(color: _muted))]))])),
  ]));
  void _feature(String name) => Navigator.push(context, MaterialPageRoute(builder: (_) => FeaturePage(api: widget.api, feature: name)));
}

class DeviceHomeCard extends StatelessWidget {
  const DeviceHomeCard({super.key, required this.onTap});
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(20),
        child: GraceCard(child: const Row(children: [
          Icon(Icons.light_mode_outlined, color: _cyan, size: 30),
          SizedBox(width: 20),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('Lighting', style: TextStyle(fontSize: 23, fontWeight: FontWeight.bold)),
            SizedBox(height: 3),
            Text('Layouts and individual light controls', style: TextStyle(color: _muted, fontSize: 16)),
          ])),
        ])),
      );
}

class HomeAssistantLight {
  const HomeAssistantLight(this.name, this.entityId);
  final String name;
  final String entityId;
}

class LightingPreset {
  const LightingPreset(this.name, this.lightsOn);
  final String name;
  final Set<String> lightsOn;
}

class LightingPage extends StatefulWidget {
  const LightingPage({super.key});
  @override
  State<LightingPage> createState() => _LightingPageState();
}

class _LightingPageState extends State<LightingPage> {
  Map<String, Map<String, dynamic>> _devices = {};
  bool _loading = true;
  bool _busy = false;
  String? _status;

  @override
  void initState() { super.initState(); _load(); }
  Future<void> _load() async {
    if (mounted) setState(() => _loading = true);
    try {
      final devices = await Future.wait(_lights.map((light) async => MapEntry(light.entityId, await _homeAssistant.getSwitch(light.entityId, light.name))));
      if (mounted) setState(() {
        _devices = Map.fromEntries(devices);
        _status = _devices.values.every((device) => device['available'] != true) ? '${_devices.values.first['message']} Check the phone’s local-network connection and Home Assistant build settings.' : null;
      });
    } catch (error) {
      if (mounted) setState(() => _status = '$error');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _setLight(HomeAssistantLight light, bool on) async {
    setState(() { _busy = true; _status = '${on ? 'Turning on' : 'Turning off'} ${light.name}…'; });
    try {
      await _homeAssistant.setSwitches({light.entityId}, on: on);
      await _load();
      if (mounted) setState(() => _status = '${light.name} turned ${on ? 'on' : 'off'}.');
    } catch (error) {
      if (mounted) setState(() => _status = '$error');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _applyPreset(LightingPreset preset) async {
    setState(() { _busy = true; _status = 'Applying ${preset.name}…'; });
    try {
      final allLightIds = _lights.map((light) => light.entityId).toSet();
      await _homeAssistant.setSwitches(allLightIds.difference(preset.lightsOn), on: false);
      await _homeAssistant.setSwitches(preset.lightsOn, on: true);
      await _load();
      if (mounted) setState(() => _status = '${preset.name} applied.');
    } catch (error) {
      if (mounted) setState(() => _status = '$error');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(body: OrbitBackground(child: SafeArea(child: GracePage(child: ListView(children: [
      Row(children: [TextButton(onPressed: () => Navigator.pop(context), child: const Text('‹ Control')), const Spacer(), IconButton(onPressed: _busy || _loading ? null : _load, icon: _loading ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2)) : const Icon(Icons.refresh), tooltip: 'Refresh lights'), const Text('Lighting', style: TextStyle(fontSize: 28, fontWeight: FontWeight.bold))]),
      GraceCard(child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        const Text('Lighting layouts', style: TextStyle(fontSize: 28, fontWeight: FontWeight.bold)),
        const SizedBox(height: 22),
        GridView.count(crossAxisCount: 2, shrinkWrap: true, physics: const NeverScrollableScrollPhysics(), mainAxisSpacing: 12, crossAxisSpacing: 12, childAspectRatio: 2.55, children: _lightingPresets.map((preset) => GraceButton(label: preset.name, primary: true, compact: true, busy: _busy, onPressed: _busy || _loading ? null : () => _applyPreset(preset))).toList()),
        const SizedBox(height: 22),
        Text(_loading ? 'Loading lighting controls from Home Assistant…' : 'Choose a layout or control a light below. Changes are sent directly to Home Assistant.', style: const TextStyle(color: _muted, fontSize: 17)),
      ])),
      if (_loading) ..._lights.map((_) => const LightingSkeletonCard()) else ..._lights.map((light) {
        final device = _devices[light.entityId];
        final isOn = device?['state'] == 'on';
        return GraceCard(child: Row(children: [Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [const Text('INDIVIDUAL LIGHT', style: TextStyle(color: _cyan, fontSize: 11, fontWeight: FontWeight.bold, letterSpacing: 2)), const SizedBox(height: 8), Text('${device?['name'] ?? light.name}', style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold)), Text(device == null ? 'Loading…' : device['available'] == true ? (isOn ? 'On' : 'Off') : '${device['message']}', style: const TextStyle(color: _muted))])), const SizedBox(width: 12), GraceButton(label: isOn ? 'Turn off' : 'Turn on', primary: !isOn, compact: true, busy: _busy, onPressed: !_busy && device?['available'] == true ? () => _setLight(light, !isOn) : null)]));
      }),
      if (_status != null) Padding(padding: const EdgeInsets.all(8), child: Text(_status!, style: const TextStyle(color: _coral))),
    ])))));
  }
}

class LightingSkeletonCard extends StatelessWidget {
  const LightingSkeletonCard({super.key});

  @override
  Widget build(BuildContext context) => GraceCard(child: Row(children: [
    Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      _SkeletonBar(width: 105, height: 11),
      const SizedBox(height: 12),
      _SkeletonBar(width: 210, height: 21),
      const SizedBox(height: 8),
      _SkeletonBar(width: 130, height: 14),
    ])),
    const SizedBox(width: 12),
    const _SkeletonBar(width: 84, height: 44),
  ]));
}

class _SkeletonBar extends StatelessWidget {
  const _SkeletonBar({required this.width, required this.height});
  final double width;
  final double height;

  @override
  Widget build(BuildContext context) => Container(width: width, height: height, decoration: BoxDecoration(color: _raised, borderRadius: BorderRadius.circular(8)));
}

class ChatPage extends StatefulWidget { const ChatPage({super.key, required this.api}); final GraceApi api; @override State<ChatPage> createState() => _ChatPageState(); }
class _ChatPageState extends State<ChatPage> {
  final _input = TextEditingController(); final _scroll = ScrollController(); final List<ChatMessage> _messages = [const ChatMessage('assistant', 'Good evening. What do you need?')]; bool _sending = false;
  Future<void> _send() async { final text = _input.text.trim(); if (text.isEmpty || _sending) return; setState(() { _messages.add(ChatMessage('user', text)); _messages.add(const ChatMessage('assistant', 'Thinking…')); _sending = true; _input.clear(); }); try { final reply = await widget.api.post('/api/chat', {'message': text, 'conversation_id': 'mobile'}); if (mounted) setState(() => _messages[_messages.length - 1] = ChatMessage('assistant', '${reply['answer'] ?? 'G.R.A.C.E. did not return a response.'}')); } catch (error) { if (mounted) setState(() => _messages[_messages.length - 1] = ChatMessage('assistant', '$error')); } finally { if (mounted) setState(() => _sending = false); } WidgetsBinding.instance.addPostFrameCallback((_) { if (_scroll.hasClients) _scroll.animateTo(_scroll.position.maxScrollExtent, duration: const Duration(milliseconds: 200), curve: Curves.easeOut); }); }
  @override Widget build(BuildContext context) => GracePage(child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [const Text('Conversation', style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold)), TextButton(onPressed: _sending ? null : () => setState(() { _messages..clear()..add(const ChatMessage('assistant', 'Good evening. What do you need?')); }), child: const Text('New'))]), const SizedBox(height: 8), Expanded(child: ListView.separated(controller: _scroll, itemCount: _messages.length, separatorBuilder: (_, __) => const SizedBox(height: 10), itemBuilder: (_, index) { final item = _messages[index]; final user = item.role == 'user'; return Align(alignment: user ? Alignment.centerRight : Alignment.centerLeft, child: Container(constraints: const BoxConstraints(maxWidth: 330), padding: const EdgeInsets.all(13), decoration: BoxDecoration(color: user ? _violet.withOpacity(.16) : _cyan.withOpacity(.06), borderRadius: BorderRadius.circular(17), border: Border(left: BorderSide(color: user ? _violet : _cyan, width: user ? 1 : 2))), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text(user ? 'You' : 'G.R.A.C.E.', style: const TextStyle(color: _muted, fontSize: 12)), const SizedBox(height: 3), Text(item.text)]))); })), Row(children: [Expanded(child: TextField(controller: _input, minLines: 1, maxLines: 4, onSubmitted: (_) => _send(), decoration: const InputDecoration(hintText: 'What do you need?'))), const SizedBox(width: 8), GraceButton(label: 'Send', primary: true, compact: true, busy: _sending, onPressed: _send)])]));
}
class ChatMessage { const ChatMessage(this.role, this.text); final String role; final String text; }

class VoicePage extends StatefulWidget { const VoicePage({super.key, required this.api}); final GraceApi api; @override State<VoicePage> createState() => _VoicePageState(); }
class _VoicePageState extends State<VoicePage> { final _input = TextEditingController(); String _response = 'Ready when you are.'; String _status = 'Type what you would like to say.'; bool _busy = false; Future<void> _send() async { final text = _input.text.trim(); if (text.isEmpty) { setState(() => _status = 'Say or type something first.'); return; } setState(() { _busy = true; _status = 'G.R.A.C.E. is thinking…'; _response = 'Thinking…'; }); try { final id = 'voice-${DateTime.now().microsecondsSinceEpoch}'; await widget.api.post('/api/chat/jobs', {'message': text, 'conversation_id': 'mobile-voice', 'job_id': id}); while (true) { final job = await widget.api.get('/api/chat/jobs/$id'); if (!mounted) return; setState(() => _response = '${job['answer'] ?? 'Thinking…'}'); if (job['status'] == 'complete' || job['status'] == 'error') break; await Future<void>.delayed(const Duration(milliseconds: 400)); } setState(() => _status = 'Response ready.'); } catch (error) { setState(() => _status = '$error'); } finally { if (mounted) setState(() => _busy = false); } } @override Widget build(BuildContext context) => Scaffold(body: OrbitBackground(child: SafeArea(child: GracePage(child: ListView(children: [Row(children: [TextButton(onPressed: () => Navigator.pop(context), child: const Text('‹ Back')), const Spacer(), const Text('Voice conversation', style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold))]), GraceCard(child: Column(children: [Container(width: 112, height: 112, decoration: BoxDecoration(shape: BoxShape.circle, color: _cyan.withOpacity(.08), border: Border.all(color: _cyan.withOpacity(.45)), boxShadow: [BoxShadow(color: _cyan.withOpacity(.18), blurRadius: 30)]), child: const Icon(Icons.mic_none, size: 42, color: _cyan)), const SizedBox(height: 16), Text(_status, style: const TextStyle(color: _muted)), GraceField(controller: _input, label: 'You said', maxLines: 3, hint: 'Type your words here'), GraceButton(label: 'Send to G.R.A.C.E.', primary: true, busy: _busy, onPressed: _send)])), GraceCard(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [const Text('G.R.A.C.E.', style: TextStyle(color: _cyan, fontSize: 11, fontWeight: FontWeight.bold, letterSpacing: 1.5)), const SizedBox(height: 8), Text(_response)]))]))))); }

class ControlPage extends StatelessWidget { const ControlPage({super.key, required this.api}); final GraceApi api; @override Widget build(BuildContext context) { const tools = [('devices', Icons.power_settings_new, 'Devices', 'Lights, plugs, and switches'), ('music', Icons.music_note, 'Music', 'Playback and volume'), ('images', Icons.auto_awesome, 'Image studio', 'Create and save locally'), ('weather', Icons.cloud_outlined, 'Weather', 'Current conditions'), ('network', Icons.all_inclusive, 'Network', 'Local diagnostics'), ('briefings', Icons.wb_sunny_outlined, 'Briefings', 'Daily summaries'), ('memory', Icons.memory, 'Memory', 'Notes G.R.A.C.E. keeps')]; return GracePage(child: ListView(children: [const Text('CONNECTED SPACE', style: TextStyle(color: _cyan, fontSize: 11, fontWeight: FontWeight.bold, letterSpacing: 1.5)), const Text('Control', style: TextStyle(fontSize: 28, fontWeight: FontWeight.bold)), const SizedBox(height: 14), GridView.count(crossAxisCount: 2, shrinkWrap: true, physics: const NeverScrollableScrollPhysics(), mainAxisSpacing: 10, crossAxisSpacing: 10, childAspectRatio: 1.2, children: tools.map((tool) => ToolTile(icon: tool.$2, title: tool.$3, subtitle: tool.$4, onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => FeaturePage(api: api, feature: tool.$1))))).toList())])); } }

class AccountPage extends StatelessWidget {
  const AccountPage({super.key, required this.api, required this.user, required this.onLogout});
  final GraceApi api;
  final Map<String, dynamic> user;
  final VoidCallback onLogout;

  @override
  Widget build(BuildContext context) => GracePage(
        child: ListView(children: [
          const Text('ACCOUNT', style: TextStyle(color: _cyan, fontSize: 11, fontWeight: FontWeight.bold, letterSpacing: 1.5)),
          Text('${user['username'] ?? 'You'}', style: const TextStyle(fontSize: 28, fontWeight: FontWeight.bold)),
          const SizedBox(height: 14),
          GraceCard(child: Column(children: [
            ListTile(contentPadding: EdgeInsets.zero, title: const Text('Access level'), subtitle: Text(user['role'] == 'admin' ? 'Administrator' : 'Standard user')),
            if (user['role'] == 'admin') const Divider(color: Colors.white12),
            if (user['role'] == 'admin') ListTile(contentPadding: EdgeInsets.zero, title: const Text('G.R.A.C.E. personality'), subtitle: const Text('Admin controls'), trailing: const Icon(Icons.chevron_right), onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => PersonalityPage(api: api)))),
          ])),
          GraceButton(label: 'Server address', onPressed: () => _serverDialog(context)),
          const SizedBox(height: 10),
          GraceButton(label: 'Log out', danger: true, onPressed: () async { try { await api.post('/api/auth/logout'); } finally { onLogout(); } }),
        ]),
      );

  Future<void> _serverDialog(BuildContext context) async {
    final field = TextEditingController(text: api.server);
    final value = await showDialog<String>(context: context, builder: (_) => AlertDialog(title: const Text('G.R.A.C.E. server'), content: TextField(controller: field, decoration: const InputDecoration(hintText: 'https://10.0.0.5:8443')), actions: [TextButton(onPressed: () => Navigator.pop(context), child: const Text('Cancel')), FilledButton(onPressed: () => Navigator.pop(context, field.text), child: const Text('Save'))]));
    if (value != null && Uri.tryParse(value)?.hasAuthority == true) api.server = value;
    field.dispose();
  }
}

class PersonalityPage extends StatefulWidget { const PersonalityPage({super.key, required this.api}); final GraceApi api; @override State<PersonalityPage> createState() => _PersonalityPageState(); }
class _PersonalityPageState extends State<PersonalityPage> { final _personality = TextEditingController(); String _humor = 'subtle', _formality = 'polished', _length = 'standard', _proactive = 'important', _status = ''; bool _confirm = false; @override void initState() { super.initState(); _load(); } Future<void> _load() async { try { final data = await widget.api.get('/api/settings'); setState(() { _personality.text = '${data['personality']}'; _humor = '${data['humor']}'; _formality = '${data['formality']}'; _length = '${data['response_length']}'; _proactive = '${data['proactive_comments']}'; _confirm = data['confirm_sensitive_actions'] == true; }); } catch (error) { setState(() => _status = '$error'); } } Future<void> _save() async { setState(() => _status = 'Saving…'); try { await widget.api.put('/api/settings', {'personality': _personality.text, 'humor': _humor, 'formality': _formality, 'response_length': _length, 'proactive_comments': _proactive, 'confirm_sensitive_actions': _confirm}); setState(() => _status = 'Personality saved. I shall endeavor to remain tolerable.'); } catch (error) { setState(() => _status = '$error'); } } @override Widget build(BuildContext context) => Scaffold(body: OrbitBackground(child: SafeArea(child: GracePage(child: ListView(children: [Row(children: [TextButton(onPressed: () => Navigator.pop(context), child: const Text('‹ Account')), const Spacer(), const Text('Personality', style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold))]), GraceCard(child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [const Text('Highly competent, discreet, and occasionally dry. Helpful first; funny second.', style: TextStyle(color: _muted)), GraceField(controller: _personality, label: 'Core personality', maxLines: 4), GraceSelect(label: 'Humor', value: _humor, items: const ['off', 'subtle', 'balanced', 'playful'], onChanged: (v) => setState(() => _humor = v)), GraceSelect(label: 'Formality', value: _formality, items: const ['casual', 'polished', 'formal'], onChanged: (v) => setState(() => _formality = v)), GraceSelect(label: 'Response length', value: _length, items: const ['brief', 'standard', 'detailed'], onChanged: (v) => setState(() => _length = v)), GraceSelect(label: 'Proactive comments', value: _proactive, items: const ['never', 'important', 'occasionally'], onChanged: (v) => setState(() => _proactive = v)), SwitchListTile.adaptive(contentPadding: EdgeInsets.zero, title: const Text('Confirm sensitive actions'), value: _confirm, onChanged: (v) => setState(() => _confirm = v)), GraceButton(label: 'Save personality', primary: true, onPressed: _save), if (_status.isNotEmpty) Padding(padding: const EdgeInsets.only(top: 10), child: Text(_status, style: const TextStyle(color: _muted))) ]))]))))); }

class FeaturePage extends StatefulWidget { const FeaturePage({super.key, required this.api, required this.feature}); final GraceApi api; final String feature; @override State<FeaturePage> createState() => _FeaturePageState(); }
class _FeaturePageState extends State<FeaturePage> { late Future<dynamic> _data; final _memory = TextEditingController(); final _imagePrompt = TextEditingController(); Map<String, dynamic>? _generated; @override void initState() { super.initState(); _data = _load(); } Future<dynamic> _load() { const routes = {'devices': '/api/devices/smart-switch', 'weather': '/api/weather', 'music': '/api/music', 'network': '/api/network', 'briefings': '/api/briefings', 'memory': '/api/memory', 'images': '/api/images/saved'}; return widget.api.get(routes[widget.feature]!); } void _refresh() => setState(() => _data = _load()); String get _title => const {'devices': 'Smart devices', 'weather': 'Weather', 'music': 'Music', 'network': 'Network', 'briefings': 'Briefings', 'memory': 'Memory', 'images': 'Image studio'}[widget.feature]!; Future<void> _post(String route, [Object? body]) async { await widget.api.post(route, body); _refresh(); } @override Widget build(BuildContext context) => Scaffold(body: OrbitBackground(child: SafeArea(child: GracePage(child: FutureBuilder<dynamic>(future: _data, builder: (_, snapshot) { final body = snapshot.hasError ? GraceCard(child: Text('${snapshot.error}', style: const TextStyle(color: _coral))) : !snapshot.hasData ? const Center(child: Padding(padding: EdgeInsets.all(40), child: CircularProgressIndicator())) : _body(Map<String, dynamic>.from(snapshot.data)); return ListView(children: [Row(children: [TextButton(onPressed: () => Navigator.pop(context), child: const Text('‹ Control')), const Spacer(), Text(_title, style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold))]), const SizedBox(height: 10), body]); }))))); Widget _body(Map<String, dynamic> data) { switch (widget.feature) { case 'weather': return GraceCard(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text('${data['location']}', style: const TextStyle(color: _cyan, fontSize: 11, fontWeight: FontWeight.bold, letterSpacing: 1.5)), Text('${data['condition']}', style: const TextStyle(fontSize: 26, fontWeight: FontWeight.bold)), const SizedBox(height: 14), GridView.count(crossAxisCount: 2, shrinkWrap: true, physics: const NeverScrollableScrollPhysics(), childAspectRatio: 2.3, children: [('Temperature', '${data['temperature_f']}°F'), ('Feels like', '${data['feels_like_f']}°F'), ('Humidity', '${data['humidity_percent']}%'), ('Wind', '${data['wind_mph']} mph')].map((x) => Metric(label: x.$1, value: x.$2)).toList())])); case 'devices': final on = data['state'] == 'on'; return GraceCard(child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [const Text('ZIGBEE SWITCH', style: TextStyle(color: _cyan, fontSize: 11, fontWeight: FontWeight.bold, letterSpacing: 1.5)), Text('${data['name']}', style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold)), Text(data['available'] == true ? (on ? 'On' : 'Off') : 'Unavailable', style: const TextStyle(color: _muted)), const SizedBox(height: 14), GraceButton(label: on ? 'Turn off' : 'Turn on', primary: !on, onPressed: data['available'] == true ? () => _post('/api/devices/smart-switch/toggle') : null), Text('${data['message']}', style: const TextStyle(color: _muted))])); case 'music': return GraceCard(child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [const Text('NOW PLAYING', style: TextStyle(color: _cyan, fontSize: 11, fontWeight: FontWeight.bold, letterSpacing: 1.5)), Text('${data['track'] ?? 'Nothing selected'}', style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold)), Text('${data['status']} · volume ${data['volume']}%', style: const TextStyle(color: _muted)), Row(children: [Expanded(child: GraceButton(label: 'Previous', compact: true, onPressed: () => _post('/api/music/command', {'action': 'previous'}))), const SizedBox(width: 6), Expanded(child: GraceButton(label: data['status'] == 'playing' ? 'Pause' : 'Play', compact: true, primary: true, onPressed: () => _post('/api/music/command', {'action': data['status'] == 'playing' ? 'pause' : 'play'}))), const SizedBox(width: 6), Expanded(child: GraceButton(label: 'Next', compact: true, onPressed: () => _post('/api/music/command', {'action': 'next'})))]), Slider(value: ((data['volume'] ?? 0) as num).toDouble(), min: 0, max: 100, divisions: 20, onChanged: (_) {}, onChangeEnd: (v) => _post('/api/music/command', {'action': 'volume', 'volume': v.round()})), Text('${data['message']}', style: const TextStyle(color: _muted))])); case 'network': return GraceCard(child: Column(children: [InfoRow('Hostname', '${data['hostname']}'), InfoRow('Server', '${data['server_host']}:${data['server_port']}'), InfoRow('Client', '${data['client_host'] ?? 'Unknown'}'), GraceButton(label: 'Scan local network', onPressed: () async { final scanned = await widget.api.post('/api/network/scan'); if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Found ${(scanned['machines'] as List).length} responding devices.'))); })])); case 'briefings': final history = List.from(data['history'] ?? []).reversed.toList(); return GraceCard(child: Column(children: [Row(children: [Expanded(child: GraceButton(label: 'Morning briefing', compact: true, primary: true, onPressed: () => _post('/api/briefings/morning'))), const SizedBox(width: 8), Expanded(child: GraceButton(label: 'Afternoon briefing', compact: true, onPressed: () => _post('/api/briefings/afternoon')))]), if (history.isEmpty) const Padding(padding: EdgeInsets.all(16), child: Text('No briefings yet.', style: TextStyle(color: _muted))), ...history.map((item) => ListTile(contentPadding: EdgeInsets.zero, title: Text('${item['period']}'), subtitle: Text('${item['text']}', style: const TextStyle(color: _muted))))])); case 'memory': final memories = List.from(data['memories'] ?? []); return GraceCard(child: Column(children: [GraceField(controller: _memory, label: 'New memory', hint: 'Something worth remembering'), GraceButton(label: 'Save memory', primary: true, onPressed: () async { if (_memory.text.trim().isEmpty) return; await _post('/api/memory', {'content': _memory.text.trim(), 'category': 'note'}); _memory.clear(); }), ...memories.map((item) => ListTile(contentPadding: EdgeInsets.zero, title: Text('${item['content']}'), subtitle: Text('${item['category']}', style: const TextStyle(color: _muted)), trailing: IconButton(icon: const Icon(Icons.delete_outline, color: _coral), onPressed: () async { await widget.api.delete('/api/memory/${item['id']}'); _refresh(); })))])); default: return _images(data); } }
  Widget _images(Map<String, dynamic> data) => Column(children: [GraceCard(child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [GraceField(controller: _imagePrompt, label: 'Describe an image', maxLines: 3, hint: 'A cinematic sunrise over a quiet laboratory'), GraceButton(label: 'Generate', primary: true, onPressed: () async { final image = await widget.api.post('/api/images/generate', {'prompt': _imagePrompt.text, 'negative_prompt': 'blurry, low quality, distorted, text, watermark'}); setState(() => _generated = Map<String, dynamic>.from(image)); }), if (_generated != null) Image.memory(base64Decode('${_generated!['image_base64']}')), if (_generated != null) GraceButton(label: 'Save image', onPressed: () => _post('/api/images/save', _generated))])), GridView.count(crossAxisCount: 2, shrinkWrap: true, physics: const NeverScrollableScrollPhysics(), crossAxisSpacing: 8, mainAxisSpacing: 8, children: List.from(data['images'] ?? []).map<Widget>((image) => Container(color: _raised, child: Center(child: Text('${image['filename'] ?? image}', textAlign: TextAlign.center, style: const TextStyle(color: _muted))))).toList())]); }

class GracePage extends StatelessWidget { const GracePage({super.key, required this.child}); final Widget child; @override Widget build(BuildContext context) => Padding(padding: const EdgeInsets.fromLTRB(14, 4, 14, 10), child: child); }
class GraceCard extends StatelessWidget { const GraceCard({super.key, required this.child}); final Widget child; @override Widget build(BuildContext context) => Container(margin: const EdgeInsets.symmetric(vertical: 6), padding: const EdgeInsets.all(16), decoration: BoxDecoration(color: _surface.withOpacity(.94), borderRadius: BorderRadius.circular(20), border: Border.all(color: _cyan.withOpacity(.18))), child: child); }
class GraceButton extends StatelessWidget { const GraceButton({super.key, required this.label, this.onPressed, this.primary = false, this.danger = false, this.selected = false, this.busy = false, this.compact = false, this.icon, this.alignStart = false}); final String label; final VoidCallback? onPressed; final bool primary, danger, selected, busy, compact, alignStart; final IconData? icon; @override Widget build(BuildContext context) { final active = primary || selected; return FilledButton.icon(onPressed: busy ? null : onPressed, icon: busy ? const SizedBox(width: 17, height: 17, child: CircularProgressIndicator(strokeWidth: 2)) : icon == null ? const SizedBox.shrink() : Icon(icon, color: active ? _ink : _cyan), label: Text(label, textAlign: alignStart ? TextAlign.left : TextAlign.center), style: FilledButton.styleFrom(minimumSize: Size.fromHeight(compact ? 44 : 50), alignment: alignStart ? Alignment.centerLeft : Alignment.center, padding: const EdgeInsets.symmetric(horizontal: 14), foregroundColor: danger ? const Color(0xffff9da1) : _ink, backgroundColor: active ? const Color(0xff277ec8) : Colors.transparent, side: BorderSide(color: danger ? _coral.withOpacity(.6) : _cyan.withOpacity(active ? 0 : .22)), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(13)))); } }
class GraceField extends StatelessWidget { const GraceField({super.key, required this.controller, required this.label, this.obscure = false, this.maxLines = 1, this.hint}); final TextEditingController controller; final String label; final bool obscure; final int maxLines; final String? hint; @override Widget build(BuildContext context) => Padding(padding: const EdgeInsets.only(top: 13), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text(label.toUpperCase(), style: const TextStyle(color: _muted, fontSize: 11, fontWeight: FontWeight.bold, letterSpacing: 1)), const SizedBox(height: 6), TextField(controller: controller, obscureText: obscure, maxLines: maxLines, decoration: InputDecoration(hintText: hint, filled: true, fillColor: const Color(0xff070d17), border: OutlineInputBorder(borderRadius: BorderRadius.circular(13), borderSide: BorderSide(color: _cyan.withOpacity(.2)))))])); }
class GraceSelect extends StatelessWidget { const GraceSelect({super.key, required this.label, required this.value, required this.items, required this.onChanged}); final String label, value; final List<String> items; final ValueChanged<String> onChanged; @override Widget build(BuildContext context) => Padding(padding: const EdgeInsets.only(top: 13), child: DropdownButtonFormField<String>(value: value, decoration: InputDecoration(labelText: label, filled: true, fillColor: const Color(0xff070d17), border: OutlineInputBorder(borderRadius: BorderRadius.circular(13))), items: items.map((item) => DropdownMenuItem(value: item, child: Text(item))).toList(), onChanged: (value) { if (value != null) onChanged(value); })); }
class ToolTile extends StatelessWidget { const ToolTile({super.key, required this.icon, required this.title, required this.subtitle, required this.onTap}); final IconData icon; final String title, subtitle; final VoidCallback onTap; @override Widget build(BuildContext context) => InkWell(onTap: onTap, borderRadius: BorderRadius.circular(16), child: Container(padding: const EdgeInsets.all(13), decoration: BoxDecoration(color: _surface.withOpacity(.9), borderRadius: BorderRadius.circular(16), border: Border.all(color: _cyan.withOpacity(.18))), child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [Icon(icon, color: _cyan), Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text(title, style: const TextStyle(fontWeight: FontWeight.bold)), Text(subtitle, style: const TextStyle(color: _muted, fontSize: 12))])]))); }
class Metric extends StatelessWidget { const Metric({super.key, required this.label, required this.value}); final String label, value; @override Widget build(BuildContext context) => Container(margin: const EdgeInsets.all(3), padding: const EdgeInsets.all(10), decoration: BoxDecoration(color: Colors.black.withOpacity(.15), border: Border.all(color: _cyan.withOpacity(.15)), borderRadius: BorderRadius.circular(12)), child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisAlignment: MainAxisAlignment.center, children: [Text(label, style: const TextStyle(color: _muted, fontSize: 11)), Text(value, style: const TextStyle(fontWeight: FontWeight.bold))])); }
class InfoRow extends StatelessWidget { const InfoRow(this.label, this.value, {super.key}); final String label, value; @override Widget build(BuildContext context) => ListTile(contentPadding: EdgeInsets.zero, title: Text(label), trailing: Text(value, style: const TextStyle(fontWeight: FontWeight.bold))); }
