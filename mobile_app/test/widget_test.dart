import 'package:flutter_test/flutter_test.dart';

void main() {
  test('the default server points to the local G.R.A.C.E. dashboard', () {
    const server = String.fromEnvironment(
      'GRACE_SERVER_URL',
      defaultValue: 'https://10.0.0.5:8443',
    );

    final url = Uri.parse(server);
    expect(url.scheme, 'https');
    expect(url.hasAuthority, isTrue);
  });
}
