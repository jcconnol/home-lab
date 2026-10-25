import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:grace_mobile/main.dart';

class _LightingApi extends GraceApi {
  _LightingApi() : super('https://localhost');

  @override
  Future<dynamic> get(String path) async => {
    'lights': [
      {'id': 'bedroom', 'name': 'Bedroom Main Lightswitch', 'state': 'on', 'available': true},
    ],
    'presets': <Map<String, dynamic>>[],
  };
}

void main() {
  for (final width in [360.0, 412.0]) {
    testWidgets('light text has room at phone width $width', (tester) async {
      tester.view.physicalSize = Size(width, 900);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      await tester.pumpWidget(MaterialApp(home: LightingPage(api: _LightingApi())));
      await tester.pumpAndSettle();

      final name = find.text('Bedroom Main Lightswitch');
      expect(tester.getSize(name).width, greaterThan(150));
      expect(tester.getSize(find.text('INDIVIDUAL LIGHT')).height, lessThan(40));
      expect(tester.takeException(), isNull);
    });
  }
}
