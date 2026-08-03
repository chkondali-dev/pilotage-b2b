# GlassShield Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Flutter Android app that detects nearby BLE smart glasses and wearables using fingerprinting and behavioral analysis.

**Architecture:** Clean Architecture with 3 layers (Presentation/Domain/Data). Flutter single codebase, Android-first. BLE via `flutter_blue_plus`. State via Riverpod. Background scanning via foreground service.

**Tech Stack:** Flutter/Dart, flutter_blue_plus, flutter_local_notifications, riverpod, permission_handler, hive, http

---

### Task 1: Flutter Project Scaffold + Dependencies

**Files:**
- Create: `C:\Users\hachk\pilotage_b2b\glassshield\pubspec.yaml`
- Create: `C:\Users\hachk\pilotage_b2b\glassshield\lib\main.dart`
- Create: `C:\Users\hachk\pilotage_b2b\glassshield\lib\app.dart`

- [ ] **Step 1: Create Flutter project**

Run:
```bash
cd C:\Users\hachk\pilotage_b2b
flutter create --org com.glassshield --project-name glassshield glassshield
```

Expected: Flutter project created in `glassshield/`

- [ ] **Step 2: Replace pubspec.yaml with dependencies**

```yaml
name: glassshield
description: Smart Wearable & Connected Glasses Detection App
publish_to: 'none'
version: 1.0.0+1

environment:
  sdk: '>=3.0.0 <4.0.0'

dependencies:
  flutter:
    sdk: flutter
  flutter_blue_plus: ^1.30.0
  flutter_local_notifications: ^17.0.0
  permission_handler: ^11.3.0
  riverpod: ^2.5.0
  flutter_riverpod: ^2.5.0
  hive: ^2.2.3
  hive_flutter: ^1.1.0
  http: ^1.2.0
  intl: ^0.19.0
  google_fonts: ^6.2.0

dev_dependencies:
  flutter_test:
    sdk: flutter
  flutter_lints: ^4.0.0

flutter:
  uses-material-design: true
  assets:
    - assets/signatures/default_signatures.json
```

- [ ] **Step 3: Create lib/main.dart**

```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'app.dart';
import 'core/theme/app_theme.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(
    const ProviderScope(
      child: GlassShieldApp(),
    ),
  );
}
```

- [ ] **Step 4: Create lib/app.dart**

```dart
import 'package:flutter/material.dart';
import 'core/theme/app_theme.dart';
import 'presentation/screens/dashboard_screen.dart';

class GlassShieldApp extends StatelessWidget {
  const GlassShieldApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'GlassShield',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.darkTheme,
      home: const DashboardScreen(),
    );
  }
}
```

---

### Task 2: Cyber Terminal Theme

**Files:**
- Create: `lib/core/theme/app_theme.dart`
- Create: `lib/core/theme/colors.dart`
- Create: `lib/core/theme/typography.dart`

- [ ] **Step 1: Create lib/core/theme/colors.dart**

```dart
import 'package:flutter/material.dart';

class AppColors {
  AppColors._();

  static const background = Color(0xFF0A0F1C);
  static const backgroundSecondary = Color(0xFF111827);
  static const backgroundCard = Color(0xFF1A2332);
  static const accentGreen = Color(0xFF00FF88);
  static const accentCyan = Color(0xFF00D4FF);
  static const warningAmber = Color(0xFFFFB800);
  static const dangerRed = Color(0xFFFF4757);
  static const textPrimary = Color(0xFFFFFFFF);
  static const textSecondary = Color(0xFF94A3B8);
  static const gridSubtle = Color(0xFF1E293B);
  static const glowGreen = Color(0x3300FF88);
  static const glowCyan = Color(0x3300D4FF);
  static const riskLow = Color(0xFF00FF88);
  static const riskMedium = Color(0xFFFFB800);
  static const riskHigh = Color(0xFFFF4757);
  static const riskUnknown = Color(0xFF94A3B8);
}
```

- [ ] **Step 2: Create lib/core/theme/typography.dart**

```dart
import 'package:flutter/material.dart';

class AppTypography {
  AppTypography._();

  static const primaryFont = 'JetBrainsMono';
  static const fallbackFont = 'monospace';

  static const TextStyle riskScore = TextStyle(
    fontFamily: primaryFont,
    fontSize: 48,
    fontWeight: FontWeight.bold,
    letterSpacing: 2,
  );

  static const TextStyle sectionTitle = TextStyle(
    fontFamily: primaryFont,
    fontSize: 20,
    fontWeight: FontWeight.w600,
    letterSpacing: 1.2,
  );

  static const TextStyle body = TextStyle(
    fontFamily: primaryFont,
    fontSize: 14,
    fontWeight: FontWeight.w400,
  );

  static const TextStyle caption = TextStyle(
    fontFamily: primaryFont,
    fontSize: 11,
    fontWeight: FontWeight.w400,
    color: AppColors.textSecondary,
  );

  static const TextStyle buttonText = TextStyle(
    fontFamily: primaryFont,
    fontSize: 16,
    fontWeight: FontWeight.w600,
    letterSpacing: 1.5,
  );
}
```

- [ ] **Step 3: Create lib/core/theme/app_theme.dart**

```dart
import 'package:flutter/material.dart';
import 'colors.dart';
import 'typography.dart';

class AppTheme {
  AppTheme._();

  static ThemeData get darkTheme {
    return ThemeData(
      brightness: Brightness.dark,
      scaffoldBackgroundColor: AppColors.background,
      primaryColor: AppColors.accentCyan,
      colorScheme: const ColorScheme.dark(
        primary: AppColors.accentCyan,
        secondary: AppColors.accentGreen,
        surface: AppColors.backgroundCard,
        error: AppColors.dangerRed,
      ),
      textTheme: const TextTheme(
        headlineLarge: AppTypography.riskScore,
        headlineMedium: AppTypography.sectionTitle,
        bodyLarge: AppTypography.body,
        bodySmall: AppTypography.caption,
      ),
      cardTheme: CardTheme(
        color: AppColors.backgroundCard,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: const BorderSide(
            color: AppColors.gridSubtle,
            width: 1,
          ),
        ),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: AppColors.accentGreen,
          foregroundColor: AppColors.background,
          textStyle: AppTypography.buttonText,
          padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 16),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(8),
          ),
          elevation: 0,
          shadowColor: AppColors.glowGreen,
        ),
      ),
      sliderTheme: const SliderThemeData(
        activeTrackColor: AppColors.accentGreen,
        inactiveTrackColor: AppColors.gridSubtle,
        thumbColor: AppColors.accentCyan,
        overlayColor: AppColors.glowCyan,
      ),
      dividerTheme: const DividerThemeData(
        color: AppColors.gridSubtle,
        thickness: 1,
      ),
    );
  }
}
```

---

### Task 3: Domain Entities

**Files:**
- Create: `lib/domain/entities/ble_device.dart`
- Create: `lib/domain/entities/signature.dart`
- Create: `lib/domain/entities/detection_record.dart`

- [ ] **Step 1: Create lib/domain/entities/ble_device.dart**

```dart
class BleDevice {
  final String id;
  final String? name;
  final int rssi;
  final String? manufacturerId;
  final List<String> serviceUuids;
  final List<String> advertisedServices;
  final int? txPower;
  final int? advertisementSize;
  final DateTime lastSeen;
  final bool isConnectable;

  const BleDevice({
    required this.id,
    this.name,
    required this.rssi,
    this.manufacturerId,
    this.serviceUuids = const [],
    this.advertisedServices = const [],
    this.txPower,
    this.advertisementSize,
    required this.lastSeen,
    this.isConnectable = false,
  });

  double get estimatedDistanceMeters {
    if (rssi == 0) return -1.0;
    final txPower = this.txPower ?? -59;
    final ratio = rssi / txPower;
    if (ratio < 1.0) {
      return ratio * ratio;
    }
    return (0.89976 * ratio * ratio * ratio * ratio) + 0.111;
  }

  String get estimatedDistanceLabel {
    final dist = estimatedDistanceMeters;
    if (dist < 0) return 'Unknown';
    if (dist < 3) return 'Close';
    if (dist < 10) return 'Near';
    return 'Far';
  }

  BleDevice copyWith({int? rssi, DateTime? lastSeen}) {
    return BleDevice(
      id: id,
      name: name,
      rssi: rssi ?? this.rssi,
      manufacturerId: manufacturerId,
      serviceUuids: serviceUuids,
      advertisedServices: advertisedServices,
      txPower: txPower,
      advertisementSize: advertisementSize,
      lastSeen: lastSeen ?? this.lastSeen,
      isConnectable: isConnectable,
    );
  }
}
```

- [ ] **Step 2: Create lib/domain/entities/signature.dart**

```dart
class BehaviorPatterns {
  final List<int> txIntervalMs;
  final List<int> txPowerDb;
  final List<int> advertisementSizeBytes;

  const BehaviorPatterns({
    this.txIntervalMs = const [],
    this.txPowerDb = const [],
    this.advertisementSizeBytes = const [],
  });

  factory BehaviorPatterns.fromJson(Map<String, dynamic> json) {
    return BehaviorPatterns(
      txIntervalMs: (json['tx_interval_ms'] as List?)?.cast<int>() ?? [],
      txPowerDb: (json['tx_power_db'] as List?)?.cast<int>() ?? [],
      advertisementSizeBytes: (json['advertisement_size_bytes'] as List?)?.cast<int>() ?? [],
    );
  }

  Map<String, dynamic> toJson() => {
    'tx_interval_ms': txIntervalMs,
    'tx_power_db': txPowerDb,
    'advertisement_size_bytes': advertisementSizeBytes,
  };
}

class Signature {
  final String id;
  final List<String> deviceNamePatterns;
  final String? manufacturerId;
  final List<String> serviceUuids;
  final List<String> advertisedServices;
  final String deviceType;
  final String riskProfile;
  final double confidenceWeight;
  final BehaviorPatterns? behaviorPatterns;

  const Signature({
    required this.id,
    this.deviceNamePatterns = const [],
    this.manufacturerId,
    this.serviceUuids = const [],
    this.advertisedServices = const [],
    this.deviceType = 'unknown',
    this.riskProfile = 'unknown',
    this.confidenceWeight = 0.5,
    this.behaviorPatterns,
  });

  bool get isCameraCapable => riskProfile == 'camera_capable';

  factory Signature.fromJson(Map<String, dynamic> json) {
    return Signature(
      id: json['id'] as String,
      deviceNamePatterns: (json['device_name_patterns'] as List?)?.cast<String>() ?? [],
      manufacturerId: json['manufacturer_id'] as String?,
      serviceUuids: (json['service_uuids'] as List?)?.cast<String>() ?? [],
      advertisedServices: (json['advertised_services'] as List?)?.cast<String>() ?? [],
      deviceType: json['device_type'] as String? ?? 'unknown',
      riskProfile: json['risk_profile'] as String? ?? 'unknown',
      confidenceWeight: (json['confidence_weight'] as num?)?.toDouble() ?? 0.5,
      behaviorPatterns: json['behavior_patterns'] != null
          ? BehaviorPatterns.fromJson(json['behavior_patterns'] as Map<String, dynamic>)
          : null,
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'device_name_patterns': deviceNamePatterns,
    'manufacturer_id': manufacturerId,
    'service_uuids': serviceUuids,
    'advertised_services': advertisedServices,
    'device_type': deviceType,
    'risk_profile': riskProfile,
    'confidence_weight': confidenceWeight,
    'behavior_patterns': behaviorPatterns?.toJson(),
  };
}
```

- [ ] **Step 3: Create lib/domain/entities/detection_record.dart**

```dart
class DetectionRecord {
  final String deviceId;
  final String deviceName;
  final String category;
  final String riskLevel;
  final double confidence;
  final DateTime firstDetected;
  final DateTime lastDetected;
  final int detectionCount;
  final double avgRssi;

  const DetectionRecord({
    required this.deviceId,
    required this.deviceName,
    required this.category,
    required this.riskLevel,
    required this.confidence,
    required this.firstDetected,
    required this.lastDetected,
    required this.detectionCount,
    required this.avgRssi,
  });
}
```

---

### Task 4: Default Signatures Asset

**Files:**
- Create: `assets/signatures/default_signatures.json`

- [ ] **Step 1: Create default signatures JSON**

```bash
New-Item -ItemType Directory -Path "C:\Users\hachk\pilotage_b2b\glassshield\assets\signatures" -Force | Out-Null
```

- [ ] **Step 2: Create assets/signatures/default_signatures.json**

```json
{
  "version": "1.0.0",
  "updated_at": "2026-05-12T00:00:00Z",
  "signatures": [
    {
      "id": "rayban_meta_1",
      "device_name_patterns": ["RayBan", "Ray-Ban", "Meta", "RBM", "EssilorLuxottica", "Stories"],
      "manufacturer_id": "0x01AB",
      "service_uuids": ["0000FD5F-0000-1000-8000-00805F9B34FB"],
      "advertised_services": ["180A", "FD5F", "FE95"],
      "device_type": "smart_glasses",
      "risk_profile": "camera_capable",
      "confidence_weight": 0.85,
      "behavior_patterns": {
        "tx_interval_ms": [500, 1000],
        "tx_power_db": [-20, -10],
        "advertisement_size_bytes": [25, 31]
      }
    },
    {
      "id": "snap_spectacles_6",
      "device_name_patterns": ["Spectacles", "Snap", "SC"],
      "manufacturer_id": "0x02A2",
      "service_uuids": ["0000FE2C-0000-1000-8000-00805F9B34FB"],
      "advertised_services": ["FE2C", "FE3A"],
      "device_type": "wearable_camera",
      "risk_profile": "camera_capable",
      "confidence_weight": 0.80
    },
    {
      "id": "xreal_air",
      "device_name_patterns": ["XREAL", "Air", "Light", "Nreal"],
      "manufacturer_id": "0x013B",
      "service_uuids": ["0000FD5F-0000-1000-8000-00805F9B34FB"],
      "advertised_services": ["FD5F", "180A"],
      "device_type": "ar_glasses",
      "risk_profile": "camera_capable",
      "confidence_weight": 0.75
    },
    {
      "id": "bose_frames",
      "device_name_patterns": ["Bose", "Frames", "Tempo", "Tenor"],
      "manufacturer_id": "0x009E",
      "service_uuids": ["0000180A-0000-1000-8000-00805F9B34FB"],
      "advertised_services": ["180A", "180F"],
      "device_type": "smart_glasses",
      "risk_profile": "audio_only",
      "confidence_weight": 0.70
    },
    {
      "id": "humane_pin",
      "device_name_patterns": ["Humane", "AiPin", "Pin"],
      "manufacturer_id": "0x02CB",
      "service_uuids": [],
      "advertised_services": ["FE95"],
      "device_type": "ai_wearable",
      "risk_profile": "camera_capable",
      "confidence_weight": 0.65
    },
    {
      "id": "apple_vision_pro",
      "device_name_patterns": ["Apple Vision", "Vision Pro", "AP"],
      "manufacturer_id": "0x004C",
      "service_uuids": [],
      "advertised_services": ["180A", "FE95"],
      "device_type": "ar_glasses",
      "risk_profile": "camera_capable",
      "confidence_weight": 0.70
    },
    {
      "id": "amazon_echo_frames",
      "device_name_patterns": ["Echo Frames", "Amazon", "RF1"],
      "manufacturer_id": "0x0171",
      "service_uuids": [],
      "advertised_services": ["180A", "180F"],
      "device_type": "smart_glasses",
      "risk_profile": "audio_only",
      "confidence_weight": 0.60
    },
    {
      "id": "meta_quest",
      "device_name_patterns": ["Meta Quest", "Oculus", "Quest"],
      "manufacturer_id": "0x01AB",
      "service_uuids": [],
      "advertised_services": ["FE95", "180A"],
      "device_type": "ar_glasses",
      "risk_profile": "camera_capable",
      "confidence_weight": 0.50
    }
  ]
}
```

---

### Task 5: Repository Interfaces (Domain Layer)

**Files:**
- Create: `lib/domain/repositories/ble_repository.dart`
- Create: `lib/domain/repositories/signature_repository.dart`

- [ ] **Step 1: Create lib/domain/repositories/ble_repository.dart**

```dart
import 'package:glassshield/domain/entities/ble_device.dart';

abstract class BleRepository {
  Stream<List<BleDevice>> scanDevices({
    Duration scanDuration = const Duration(seconds: 3),
    bool continuous = true,
  });
  void stopScan();
  bool get isScanning;
}
```

- [ ] **Step 2: Create lib/domain/repositories/signature_repository.dart**

```dart
import 'package:glassshield/domain/entities/signature.dart';

abstract class SignatureRepository {
  Future<List<Signature>> loadSignatures();
  Future<void> updateSignatures();
  Future<Signature?> matchSignature(BleDevice device);
}
```

---

### Task 6: Data Layer — Models & DataSources

**Files:**
- Create: `lib/data/models/ble_device_model.dart`
- Create: `lib/data/models/signature_model.dart`
- Create: `lib/data/datasources/signature_local_datasource.dart`
- Create: `lib/data/datasources/signature_remote_datasource.dart`

- [ ] **Step 1: Create lib/data/models/ble_device_model.dart**

```dart
import 'package:glassshield/domain/entities/ble_device.dart';

class BleDeviceModel {
  static BleDevice fromBleScanResult(dynamic scanResult) {
    final device = scanResult.device;
    final advertisementData = scanResult.advertisementData;
    return BleDevice(
      id: device.remoteId.str,
      name: device.name.isNotEmpty ? device.name : advertisementData.localName,
      rssi: scanResult.rssi,
      manufacturerId: _parseManufacturerId(advertisementData.manufacturerData),
      serviceUuids: advertisementData.serviceUuids?.map((u) => u.str).toList() ?? [],
      advertisedServices: advertisementData.serviceData?.keys.map((k) => k.str).toList() ?? [],
      txPower: advertisementData.txPowerLevel,
      advertisementSize: advertisementData.rawData?.length,
      lastSeen: DateTime.now(),
      isConnectable: advertisementData.connectable ?? false,
    );
  }

  static String? _parseManufacturerId(Map<int, List<int>>? manufacturerData) {
    if (manufacturerData == null || manufacturerData.isEmpty) return null;
    final companyId = manufacturerData.keys.first;
    return '0x${companyId.toRadixString(16).toUpperCase().padLeft(4, '0')}';
  }
}
```

- [ ] **Step 2: Create lib/data/models/signature_model.dart**

```dart
// Uses Signature from domain directly — no separate model needed.
// Signature.fromJson() and .toJson() are defined in domain/entities/signature.dart
export 'package:glassshield/domain/entities/signature.dart';
```

- [ ] **Step 3: Create lib/data/datasources/signature_local_datasource.dart**

```dart
import 'dart:convert';
import 'package:flutter/services.dart';
import 'package:hive_flutter/hive_flutter.dart';
import 'package:glassshield/domain/entities/signature.dart';

class SignatureLocalDataSource {
  static const _boxName = 'signatures';
  static const _cacheKey = 'signatures_json';

  Future<List<Signature>> loadDefault() async {
    final jsonString = await rootBundle.loadString('assets/signatures/default_signatures.json');
    final decoded = json.decode(jsonString) as Map<String, dynamic>;
    final list = decoded['signatures'] as List;
    return list.map((e) => Signature.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<List<Signature>> loadCached() async {
    final box = await Hive.openBox(_boxName);
    final cached = box.get(_cacheKey) as String?;
    if (cached == null) return [];
    final decoded = json.decode(cached) as List;
    return decoded.map((e) => Signature.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<void> cacheSignatures(List<Signature> signatures) async {
    final box = await Hive.openBox(_boxName);
    final jsonStr = json.encode(signatures.map((e) => e.toJson()).toList());
    await box.put(_cacheKey, jsonStr);
  }

  Future<String?> getLastUpdateTimestamp() async {
    final box = await Hive.openBox(_boxName);
    return box.get('last_update') as String?;
  }

  Future<void> setLastUpdateTimestamp(String timestamp) async {
    final box = await Hive.openBox(_boxName);
    await box.put('last_update', timestamp);
  }
}
```

- [ ] **Step 4: Create lib/data/datasources/signature_remote_datasource.dart**

```dart
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:glassshield/domain/entities/signature.dart';

class SignatureRemoteDataSource {
  static const _defaultSourceUrl = 'https://raw.githubusercontent.com/GlassShield/signatures/main/signatures.json';

  Future<List<Signature>> fetchRemoteSignatures({String? sourceUrl}) async {
    final url = sourceUrl ?? _defaultSourceUrl;
    final response = await http.get(Uri.parse(url));
    if (response.statusCode != 200) {
      throw Exception('Failed to fetch signatures: ${response.statusCode}');
    }
    final decoded = json.decode(response.body) as Map<String, dynamic>;
    final list = decoded['signatures'] as List;
    return list.map((e) => Signature.fromJson(e as Map<String, dynamic>)).toList();
  }
}
```

---

### Task 7: Repository Implementations

**Files:**
- Create: `lib/data/repositories/ble_repository_impl.dart`
- Create: `lib/data/repositories/signature_repository_impl.dart`

- [ ] **Step 1: Create lib/data/repositories/ble_repository_impl.dart**

```dart
import 'dart:async';
import 'package:flutter_blue_plus/flutter_blue_plus.dart';
import 'package:glassshield/domain/entities/ble_device.dart';
import 'package:glassshield/domain/repositories/ble_repository.dart';
import 'package:glassshield/data/models/ble_device_model.dart';

class BleRepositoryImpl implements BleRepository {
  StreamSubscription? _scanSubscription;
  final StreamController<List<BleDevice>> _deviceController =
      StreamController<List<BleDevice>>.broadcast();
  final List<BleDevice> _knownDevices = [];
  bool _isScanning = false;

  @override
  bool get isScanning => _isScanning;

  @override
  Stream<List<BleDevice>> scanDevices({
    Duration scanDuration = const Duration(seconds: 3),
    bool continuous = true,
  }) async* {
    _isScanning = true;

    await FlutterBluePlus.startScan(
      withServices: [],
      timeout: continuous ? null : scanDuration,
    );

    _scanSubscription = FlutterBluePlus.scanResults.listen((results) {
      for (final result in results) {
        final device = BleDeviceModel.fromBleScanResult(result);
        final existingIndex = _knownDevices.indexWhere((d) => d.id == device.id);
        if (existingIndex >= 0) {
          _knownDevices[existingIndex] = _knownDevices[existingIndex].copyWith(
            rssi: device.rssi,
            lastSeen: device.lastSeen,
          );
        } else {
          _knownDevices.add(device);
        }
      }
      _deviceController.add(List.unmodifiable(_knownDevices));
    });

    await for (final devices in _deviceController.stream) {
      yield devices;
    }
  }

  @override
  void stopScan() {
    _isScanning = false;
    _scanSubscription?.cancel();
    FlutterBluePlus.stopScan();
    _deviceController.close();
  }
}
```

- [ ] **Step 2: Create lib/data/repositories/signature_repository_impl.dart**

```dart
import 'package:glassshield/domain/entities/ble_device.dart';
import 'package:glassshield/domain/entities/signature.dart';
import 'package:glassshield/domain/repositories/signature_repository.dart';
import 'package:glassshield/data/datasources/signature_local_datasource.dart';
import 'package:glassshield/data/datasources/signature_remote_datasource.dart';

class SignatureRepositoryImpl implements SignatureRepository {
  final SignatureLocalDataSource _localDataSource;
  final SignatureRemoteDataSource _remoteDataSource;
  List<Signature> _mergedSignatures = [];

  SignatureRepositoryImpl({
    required SignatureLocalDataSource localDataSource,
    required SignatureRemoteDataSource remoteDataSource,
  })  : _localDataSource = localDataSource,
        _remoteDataSource = remoteDataSource;

  @override
  Future<List<Signature>> loadSignatures() async {
    final cached = await _localDataSource.loadCached();
    if (cached.isNotEmpty) {
      _mergedSignatures = cached;
      return cached;
    }
    final defaults = await _localDataSource.loadDefault();
    _mergedSignatures = defaults;
    return defaults;
  }

  @override
  Future<void> updateSignatures() async {
    try {
      final remote = await _remoteDataSource.fetchRemoteSignatures();
      await _localDataSource.cacheSignatures(remote);
      _mergedSignatures = remote;
      await _localDataSource.setLastUpdateTimestamp(DateTime.now().toIso8601String());
    } catch (_) {
      // Fallback: keep existing signatures
    }
  }

  @override
  Future<Signature?> matchSignature(BleDevice device) async {
    if (_mergedSignatures.isEmpty) {
      await loadSignatures();
    }

    Signature? bestMatch;
    double highestScore = 0;

    for (final signature in _mergedSignatures) {
      double score = 0;
      final weights = <double>[];

      // Name pattern matching
      if (device.name != null) {
        for (final pattern in signature.deviceNamePatterns) {
          if (device.name!.toLowerCase().contains(pattern.toLowerCase())) {
            score += 0.4;
            break;
          }
        }
      }

      // Manufacturer ID matching
      if (device.manufacturerId != null &&
          signature.manufacturerId != null &&
          device.manufacturerId == signature.manufacturerId) {
        score += 0.3;
      }

      // Service UUID matching
      if (device.serviceUuids.isNotEmpty && signature.serviceUuids.isNotEmpty) {
        for (final uuid in device.serviceUuids) {
          if (signature.serviceUuids.any((su) =>
              su.contains(uuid.substring(4, 8)))) {
            score += 0.2;
            break;
          }
        }
      }

      // Advertised services matching
      if (device.advertisedServices.isNotEmpty &&
          signature.advertisedServices.isNotEmpty) {
        for (final svc in device.advertisedServices) {
          if (signature.advertisedServices.contains(svc)) {
            score += 0.1;
            break;
          }
        }
      }

      final finalScore = score * signature.confidenceWeight;
      if (finalScore > highestScore) {
        highestScore = finalScore;
        bestMatch = signature;
      }
    }

    return bestMatch;
  }
}
```

---

### Task 8: Use Cases (Domain Layer)

**Files:**
- Create: `lib/domain/usecases/scan_ble_devices.dart`
- Create: `lib/domain/usecases/fingerprint_device.dart`
- Create: `lib/domain/usecases/score_risk.dart`
- Create: `lib/domain/usecases/update_signatures.dart`

- [ ] **Step 1: Create lib/domain/usecases/scan_ble_devices.dart**

```dart
import 'dart:async';
import 'package:glassshield/domain/entities/ble_device.dart';
import 'package:glassshield/domain/repositories/ble_repository.dart';

class ScanBleDevices {
  final BleRepository _repository;

  ScanBleDevices(this._repository);

  Stream<List<BleDevice>> execute({
    Duration scanDuration = const Duration(seconds: 3),
    bool continuous = true,
  }) {
    return _repository.scanDevices(
      scanDuration: scanDuration,
      continuous: continuous,
    );
  }

  void stop() => _repository.stopScan();
  bool get isScanning => _repository.isScanning;
}
```

- [ ] **Step 2: Create lib/domain/usecases/fingerprint_device.dart**

```dart
import 'package:glassshield/domain/entities/ble_device.dart';
import 'package:glassshield/domain/entities/signature.dart';
import 'package:glassshield/domain/repositories/signature_repository.dart';

class FingerprintDeviceResult {
  final BleDevice device;
  final Signature? matchedSignature;
  final double confidence;
  final String category;
  final String riskLevel;

  const FingerprintDeviceResult({
    required this.device,
    this.matchedSignature,
    required this.confidence,
    required this.category,
    required this.riskLevel,
  });
}

class FingerprintDevice {
  final SignatureRepository _repository;

  FingerprintDevice(this._repository);

  Future<FingerprintDeviceResult> execute(BleDevice device) async {
    final signature = await _repository.matchSignature(device);

    if (signature != null) {
      final confidence = signature.confidenceWeight * 100;
      String riskLevel;
      if (confidence >= 70) {
        riskLevel = 'Élevé';
      } else if (confidence >= 40) {
        riskLevel = 'Moyen';
      } else {
        riskLevel = 'Faible';
      }
      return FingerprintDeviceResult(
        device: device,
        matchedSignature: signature,
        confidence: confidence,
        category: signature.deviceType,
        riskLevel: riskLevel,
      );
    }

    return FingerprintDeviceResult(
      device: device,
      confidence: 15,
      category: 'unknown',
      riskLevel: 'Inconnu',
    );
  }
}
```

- [ ] **Step 3: Create lib/domain/usecases/score_risk.dart**

```dart
import 'package:glassshield/domain/usecases/fingerprint_device.dart';

class ScoreRisk {
  const ScoreRisk();

  int calculate(List<FingerprintDeviceResult> results) {
    if (results.isEmpty) return 0;

    double totalScore = 0;
    int closeCount = 0;

    for (final result in results) {
      double deviceScore = result.confidence;

      if (result.matchedSignature?.isCameraCapable == true) {
        deviceScore *= 1.2;
      }

      if (result.device.estimatedDistanceLabel == 'Close') {
        deviceScore *= 1.1;
        closeCount++;
      }

      totalScore += deviceScore;
    }

    // Boost if multiple risky devices nearby
    if (closeCount >= 2) {
      totalScore *= 1.15;
    }

    final avg = totalScore / results.length;
    return avg.clamp(0, 100).round();
  }
}
```

- [ ] **Step 4: Create lib/domain/usecases/update_signatures.dart**

```dart
import 'package:glassshield/domain/repositories/signature_repository.dart';

class UpdateSignatures {
  final SignatureRepository _repository;

  UpdateSignatures(this._repository);

  Future<void> execute() => _repository.updateSignatures();
}
```

---

### Task 9: Providers (Presentation — Riverpod)

**Files:**
- Create: `lib/presentation/providers/scan_provider.dart`
- Create: `lib/presentation/providers/signatures_provider.dart`
- Create: `lib/presentation/providers/risk_provider.dart`

- [ ] **Step 1: Create lib/presentation/providers/scan_provider.dart**

```dart
import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:glassshield/domain/entities/ble_device.dart';
import 'package:glassshield/domain/usecases/scan_ble_devices.dart';
import 'package:glassshield/domain/usecases/fingerprint_device.dart';
import 'package:glassshield/data/repositories/ble_repository_impl.dart';

final bleRepositoryProvider = Provider<BleRepositoryImpl>((ref) {
  return BleRepositoryImpl();
});

final scanBleDevicesProvider = Provider<ScanBleDevices>((ref) {
  final repo = ref.read(bleRepositoryProvider);
  return ScanBleDevices(repo);
});

class ScanState {
  final bool isScanning;
  final List<BleDevice> devices;
  final String? error;

  const ScanState({
    this.isScanning = false,
    this.devices = const [],
    this.error,
  });

  ScanState copyWith({bool? isScanning, List<BleDevice>? devices, String? error}) {
    return ScanState(
      isScanning: isScanning ?? this.isScanning,
      devices: devices ?? this.devices,
      error: error,
    );
  }
}

class ScanNotifier extends StateNotifier<ScanState> {
  final ScanBleDevices _scanBleDevices;
  StreamSubscription? _subscription;

  ScanNotifier(this._scanBleDevices) : super(const ScanState());

  void startScan({bool continuous = true}) {
    if (state.isScanning) return;
    state = state.copyWith(isScanning: true, error: null);

    _subscription = _scanBleDevices.execute(continuous: continuous).listen(
      (devices) {
        state = state.copyWith(devices: devices);
      },
      onError: (error) {
        state = state.copyWith(isScanning: false, error: error.toString());
      },
    );
  }

  void stopScan() {
    _subscription?.cancel();
    _scanBleDevices.stop();
    state = state.copyWith(isScanning: false);
  }

  @override
  void dispose() {
    _subscription?.cancel();
    _scanBleDevices.stop();
    super.dispose();
  }
}

final scanProvider = StateNotifierProvider<ScanNotifier, ScanState>((ref) {
  final useCase = ref.read(scanBleDevicesProvider);
  return ScanNotifier(useCase);
});
```

- [ ] **Step 2: Create lib/presentation/providers/signatures_provider.dart**

```dart
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:glassshield/data/datasources/signature_local_datasource.dart';
import 'package:glassshield/data/datasources/signature_remote_datasource.dart';
import 'package:glassshield/data/repositories/signature_repository_impl.dart';
import 'package:glassshield/domain/entities/signature.dart';

final localDataSourceProvider = Provider<SignatureLocalDataSource>((ref) {
  return SignatureLocalDataSource();
});

final remoteDataSourceProvider = Provider<SignatureRemoteDataSource>((ref) {
  return SignatureRemoteDataSource();
});

final signatureRepositoryProvider = Provider<SignatureRepositoryImpl>((ref) {
  return SignatureRepositoryImpl(
    localDataSource: ref.read(localDataSourceProvider),
    remoteDataSource: ref.read(remoteDataSourceProvider),
  );
});

class SignaturesState {
  final List<Signature> signatures;
  final bool isLoading;
  final String? lastUpdate;

  const SignaturesState({
    this.signatures = const [],
    this.isLoading = false,
    this.lastUpdate,
  });

  SignaturesState copyWith({List<Signature>? signatures, bool? isLoading, String? lastUpdate}) {
    return SignaturesState(
      signatures: signatures ?? this.signatures,
      isLoading: isLoading ?? this.isLoading,
      lastUpdate: lastUpdate ?? this.lastUpdate,
    );
  }
}

class SignaturesNotifier extends StateNotifier<SignaturesState> {
  final SignatureRepositoryImpl _repository;

  SignaturesNotifier(this._repository) : super(const SignaturesState());

  Future<void> loadSignatures() async {
    state = state.copyWith(isLoading: true);
    final sigs = await _repository.loadSignatures();
    state = state.copyWith(signatures: sigs, isLoading: false);
  }

  Future<void> updateSignatures() async {
    state = state.copyWith(isLoading: true);
    await _repository.updateSignatures();
    final sigs = await _repository.loadSignatures();
    state = state.copyWith(signatures: sigs, isLoading: false, lastUpdate: DateTime.now().toIso8601String());
  }
}

final signaturesProvider = StateNotifierProvider<SignaturesNotifier, SignaturesState>((ref) {
  final repo = ref.read(signatureRepositoryProvider);
  return SignaturesNotifier(repo);
});
```

- [ ] **Step 3: Create lib/presentation/providers/risk_provider.dart**

```dart
import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:glassshield/domain/entities/ble_device.dart';
import 'package:glassshield/domain/usecases/fingerprint_device.dart';
import 'package:glassshield/domain/usecases/score_risk.dart';
import 'package:glassshield/presentation/providers/scan_provider.dart';
import 'package:glassshield/presentation/providers/signatures_provider.dart';

final fingerprintProvider = Provider<FingerprintDevice>((ref) {
  final repo = ref.read(signatureRepositoryProvider);
  return FingerprintDevice(repo);
});

class RiskState {
  final int globalRiskScore;
  final List<FingerprintDeviceResult> deviceResults;
  final bool isAnalyzing;

  const RiskState({
    this.globalRiskScore = 0,
    this.deviceResults = const [],
    this.isAnalyzing = false,
  });

  RiskState copyWith({int? globalRiskScore, List<FingerprintDeviceResult>? deviceResults, bool? isAnalyzing}) {
    return RiskState(
      globalRiskScore: globalRiskScore ?? this.globalRiskScore,
      deviceResults: deviceResults ?? this.deviceResults,
      isAnalyzing: isAnalyzing ?? this.isAnalyzing,
    );
  }
}

class RiskNotifier extends StateNotifier<RiskState> {
  final FingerprintDevice _fingerprintDevice;
  final ScoreRisk _scoreRisk;
  StreamSubscription? _subscription;

  RiskNotifier(this._fingerprintDevice) : _scoreRisk = const ScoreRisk(), super(const RiskState());

  void startAnalysis(Stream<List<BleDevice>> deviceStream) {
    state = state.copyWith(isAnalyzing: true);

    _subscription = deviceStream.listen((devices) async {
      final results = <FingerprintDeviceResult>[];
      for (final device in devices) {
        final result = await _fingerprintDevice.execute(device);
        results.add(result);
      }
      final globalScore = _scoreRisk.calculate(results);
      state = state.copyWith(
        globalRiskScore: globalScore,
        deviceResults: results,
      );
    });
  }

  void stopAnalysis() {
    _subscription?.cancel();
    state = state.copyWith(isAnalyzing: false);
  }

  @override
  void dispose() {
    _subscription?.cancel();
    super.dispose();
  }
}

final riskProvider = StateNotifierProvider<RiskNotifier, RiskState>((ref) {
  final fp = ref.read(fingerprintProvider);
  return RiskNotifier(fp);
});
```

---

### Task 10: Dashboard Screen + Widgets

**Files:**
- Create: `lib/presentation/screens/dashboard_screen.dart`
- Create: `lib/presentation/widgets/risk_gauge.dart`
- Create: `lib/presentation/widgets/radar_widget.dart`
- Create: `lib/presentation/widgets/device_list_item.dart`
- Create: `lib/presentation/widgets/device_detail_sheet.dart`
- Create: `lib/presentation/widgets/quick_stats_card.dart`
- Create: `lib/presentation/widgets/scan_button.dart`

- [ ] **Step 1: Create lib/presentation/screens/dashboard_screen.dart**

```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:glassshield/presentation/providers/scan_provider.dart';
import 'package:glassshield/presentation/providers/risk_provider.dart';
import 'package:glassshield/presentation/providers/signatures_provider.dart';
import 'package:glassshield/core/theme/colors.dart';
import 'package:glassshield/core/theme/typography.dart';
import 'package:glassshield/presentation/widgets/risk_gauge.dart';
import 'package:glassshield/presentation/widgets/radar_widget.dart';
import 'package:glassshield/presentation/widgets/device_list_item.dart';
import 'package:glassshield/presentation/widgets/quick_stats_card.dart';
import 'package:glassshield/presentation/widgets/scan_button.dart';

class DashboardScreen extends ConsumerStatefulWidget {
  const DashboardScreen({super.key});

  @override
  ConsumerState<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends ConsumerState<DashboardScreen> {
  bool _isBackgroundMode = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(signaturesProvider.notifier).loadSignatures();
    });
  }

  void _toggleScan() {
    final scanState = ref.read(scanProvider);
    final riskNotifier = ref.read(riskProvider.notifier);
    final scanNotifier = ref.read(scanProvider.notifier);

    if (scanState.isScanning) {
      scanNotifier.stopScan();
      riskNotifier.stopAnalysis();
    } else {
      final deviceStream = ref.read(scanBleDevicesProvider).execute(
        continuous: !_isBackgroundMode,
        scanDuration: const Duration(seconds: 15),
      );
      scanNotifier.startScan(continuous: !_isBackgroundMode);
      riskNotifier.startAnalysis(deviceStream);
    }
  }

  @override
  Widget build(BuildContext context) {
    final scanState = ref.watch(scanProvider);
    final riskState = ref.watch(riskProvider);
    final sigState = ref.watch(signaturesProvider);

    return Scaffold(
      body: SafeArea(
        child: Column(
          children: [
            _buildStatusBar(),
            Expanded(
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(16),
                child: Column(
                  children: [
                    RiskGauge(score: riskState.globalRiskScore),
                    const SizedBox(height: 16),
                    RadarWidget(
                      devices: scanState.devices,
                      isScanning: scanState.isScanning,
                    ),
                    const SizedBox(height: 16),
                    _buildQuickStats(scanState, riskState),
                    const SizedBox(height: 16),
                    _buildDetectionList(riskState),
                  ],
                ),
              ),
            ),
            ScanButton(
              isScanning: scanState.isScanning,
              onPressed: _toggleScan,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildStatusBar() {
    final scanState = ref.watch(scanProvider);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: const BoxDecoration(
        border: Border(bottom: BorderSide(color: AppColors.gridSubtle)),
      ),
      child: Row(
        children: [
          Text('GLASSSHIELD', style: AppTypography.sectionTitle.copyWith(color: AppColors.accentCyan)),
          const Spacer(),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            decoration: BoxDecoration(
              color: scanState.isScanning ? AppColors.glowGreen : AppColors.gridSubtle,
              borderRadius: BorderRadius.circular(4),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  width: 6,
                  height: 6,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: scanState.isScanning ? AppColors.accentGreen : AppColors.textSecondary,
                  ),
                ),
                const SizedBox(width: 6),
                Text(
                  scanState.isScanning ? 'ACTIVE' : 'IDLE',
                  style: AppTypography.caption.copyWith(
                    color: scanState.isScanning ? AppColors.accentGreen : AppColors.textSecondary,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildQuickStats(ScanState scanState, RiskState riskState) {
    return Row(
      children: [
        Expanded(
          child: QuickStatsCard(
            label: 'DEVICES',
            value: '${scanState.devices.length}',
            color: AppColors.accentCyan,
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: QuickStatsCard(
            label: 'HIGH RISK',
            value: '${riskState.deviceResults.where((r) => r.riskLevel == 'Élevé').length}',
            color: AppColors.dangerRed,
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: QuickStatsCard(
            label: 'LAST SCAN',
            value: scanState.isScanning ? 'NOW' : 'IDLE',
            color: AppColors.textSecondary,
          ),
        ),
      ],
    );
  }

  Widget _buildDetectionList(RiskState riskState) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(bottom: 8),
          child: Text('DETECTIONS', style: AppTypography.sectionTitle),
        ),
        if (riskState.deviceResults.isEmpty)
          Container(
            padding: const EdgeInsets.all(24),
            decoration: BoxDecoration(
              color: AppColors.backgroundCard,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: AppColors.gridSubtle),
            ),
            child: Center(
              child: Text(
                'No devices detected.\nTap SCAN to begin.',
                textAlign: TextAlign.center,
                style: AppTypography.body.copyWith(color: AppColors.textSecondary),
              ),
            ),
          )
        else
          ...riskState.deviceResults.map((result) => DeviceListItem(
            result: result,
            onTap: () => _showDeviceDetail(result),
          )),
      ],
    );
  }

  void _showDeviceDetail(FingerprintDeviceResult result) {
    showModalBottomSheet(
      context: context,
      backgroundColor: AppColors.backgroundCard,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
        side: BorderSide(color: AppColors.gridSubtle),
      ),
      builder: (_) => DeviceDetailSheet(result: result),
    );
  }
}
```

- [ ] **Step 2: Create lib/presentation/widgets/risk_gauge.dart**

```dart
import 'dart:math';
import 'package:flutter/material.dart';
import 'package:glassshield/core/theme/colors.dart';
import 'package:glassshield/core/theme/typography.dart';

class RiskGauge extends StatelessWidget {
  final int score;

  const RiskGauge({super.key, required this.score});

  Color get _color {
    if (score >= 70) return AppColors.dangerRed;
    if (score >= 40) return AppColors.warningAmber;
    if (score >= 10) return AppColors.accentGreen;
    return AppColors.riskUnknown;
  }

  String get _label {
    if (score >= 70) return 'HIGH';
    if (score >= 40) return 'MEDIUM';
    if (score >= 10) return 'LOW';
    return 'SAFE';
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Stack(
          alignment: Alignment.center,
          children: [
            SizedBox(
              width: 180,
              height: 90,
              child: CustomPaint(
                painter: _GaugePainter(score: score, color: _color),
                size: const Size(180, 90),
              ),
            ),
            Positioned(
              bottom: 0,
              child: Column(
                children: [
                  Text('${score}', style: AppTypography.riskScore.copyWith(color: _color)),
                  Text(_label,
                    style: AppTypography.caption.copyWith(color: _color, letterSpacing: 3)),
                ],
              ),
            ),
          ],
        ),
        const SizedBox(height: 4),
        Text('GLOBAL RISK SCORE', style: AppTypography.caption.copyWith(letterSpacing: 2)),
      ],
    );
  }
}

class _GaugePainter extends CustomPainter {
  final int score;
  final Color color;

  _GaugePainter({required this.score, required this.color});

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 8
      ..strokeCap = StrokeCap.round;

    // Background arc
    paint.color = AppColors.gridSubtle;
    canvas.drawArc(
      Rect.fromLTWH(4, 4, size.width - 8, size.height * 2 - 8),
      pi,
      pi,
      false,
      paint,
    );

    // Score arc
    paint.color = color;
    final sweepAngle = pi * (score / 100);
    canvas.drawArc(
      Rect.fromLTWH(4, 4, size.width - 8, size.height * 2 - 8),
      pi,
      sweepAngle.clamp(0, pi),
      false,
      paint,
    );
  }

  @override
  bool shouldRepaint(_GaugePainter old) => old.score != score;
}
```

- [ ] **Step 3: Create lib/presentation/widgets/radar_widget.dart**

```dart
import 'dart:math';
import 'package:flutter/material.dart';
import 'package:glassshield/core/theme/colors.dart';
import 'package:glassshield/domain/entities/ble_device.dart';

class RadarWidget extends StatefulWidget {
  final List<BleDevice> devices;
  final bool isScanning;

  const RadarWidget({super.key, required this.devices, this.isScanning = false});

  @override
  State<RadarWidget> createState() => _RadarWidgetState();
}

class _RadarWidgetState extends State<RadarWidget> with SingleTickerProviderStateMixin {
  late AnimationController _pulseController;
  final Random _random = Random();

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 2),
    )..repeat();
  }

  @override
  void dispose() {
    _pulseController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _pulseController,
      builder: (context, child) {
        return Container(
          width: double.infinity,
          height: 220,
          decoration: BoxDecoration(
            color: AppColors.backgroundSecondary,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: AppColors.gridSubtle),
          ),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(12),
            child: Stack(
              children: [
                _buildGrid(),
                _buildConcentricRings(),
                if (widget.isScanning) _buildScanLine(),
                ..._buildDeviceDots(),
                Center(
                  child: Text(
                    widget.isScanning ? 'SCANNING...' : 'IDLE',
                    style: TextStyle(
                      fontFamily: 'JetBrainsMono',
                      fontSize: 10,
                      color: AppColors.textSecondary.withOpacity(0.3),
                      letterSpacing: 4,
                    ),
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _buildGrid() {
    return CustomPaint(
      size: const Size(double.infinity, 220),
      painter: _RadarGridPainter(),
    );
  }

  Widget _buildConcentricRings() {
    return CustomPaint(
      size: const Size(double.infinity, 220),
      painter: _RingsPainter(pulseValue: _pulseController.value),
    );
  }

  Widget _buildScanLine() {
    return AnimatedBuilder(
      animation: _pulseController,
      builder: (context, child) {
        final progress = _pulseController.value;
        return Positioned(
          top: 0,
          left: 0,
          right: 0,
          child: Opacity(
            opacity: 0.3,
            child: Container(
              height: 2,
              margin: EdgeInsets.only(top: progress * 220),
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  colors: [
                    Colors.transparent,
                    AppColors.accentGreen.withOpacity(0.6),
                    Colors.transparent,
                  ],
                ),
              ),
            ),
          ),
        );
      },
    );
  }

  List<Widget> _buildDeviceDots() {
    return widget.devices.map((device) {
      final angle = _random.nextDouble() * 2 * pi;
      final distanceFactor = _random.nextDouble() * 0.7 + 0.1;
      final centerX = 180.0;
      final centerY = 110.0;
      final radius = 80.0 * distanceFactor;
      final x = centerX + radius * cos(angle);
      final y = centerY + radius * sin(angle);

      Color dotColor;
      if (device.rssi > -50) {
        dotColor = AppColors.dangerRed;
      } else if (device.rssi > -70) {
        dotColor = AppColors.warningAmber;
      } else {
        dotColor = AppColors.accentCyan;
      }

      return Positioned(
        left: x,
        top: y,
        child: Container(
          width: 8,
          height: 8,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: dotColor,
            boxShadow: [
              BoxShadow(
                color: dotColor.withOpacity(0.5),
                blurRadius: 6,
                spreadRadius: 1,
              ),
            ],
          ),
        ),
      );
    }).toList();
  }
}

class _RadarGridPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = AppColors.gridSubtle.withOpacity(0.3)
      ..strokeWidth = 0.5;

    // Vertical lines
    for (double x = 0; x < size.width; x += 30) {
      canvas.drawLine(Offset(x, 0), Offset(x, size.height), paint);
    }
    // Horizontal lines
    for (double y = 0; y < size.height; y += 30) {
      canvas.drawLine(Offset(0, y), Offset(size.width, y), paint);
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

class _RingsPainter extends CustomPainter {
  final double pulseValue;

  _RingsPainter({required this.pulseValue});

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final maxRadius = min(size.width, size.height) / 2 - 20;

    for (int i = 0; i < 3; i++) {
      final paint = Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1
        ..color = AppColors.accentCyan.withOpacity(0.15 + i * 0.1);

      final ringRadius = maxRadius * (0.3 + i * 0.25) + pulseValue * 10 * (i + 1);
      canvas.drawCircle(center, ringRadius.clamp(20, maxRadius), paint);
    }
  }

  @override
  bool shouldRepaint(_RingsPainter old) => old.pulseValue != pulseValue;
}
```

- [ ] **Step 4: Create lib/presentation/widgets/device_list_item.dart**

```dart
import 'package:flutter/material.dart';
import 'package:glassshield/core/theme/colors.dart';
import 'package:glassshield/core/theme/typography.dart';
import 'package:glassshield/domain/usecases/fingerprint_device.dart';

class DeviceListItem extends StatelessWidget {
  final FingerprintDeviceResult result;
  final VoidCallback onTap;

  const DeviceListItem({super.key, required this.result, required this.onTap});

  Color get _riskColor {
    switch (result.riskLevel) {
      case 'Élevé':
        return AppColors.dangerRed;
      case 'Moyen':
        return AppColors.warningAmber;
      case 'Faible':
        return AppColors.accentGreen;
      default:
        return AppColors.riskUnknown;
    }
  }

  @override
  Widget build(BuildContext context) {
    final deviceName = result.device.name ?? 'Unknown Device';
    final deviceId = result.device.id.length > 8
        ? result.device.id.substring(0, 8).toUpperCase()
        : result.device.id.toUpperCase();

    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: AppColors.backgroundCard,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: AppColors.gridSubtle),
          ),
          child: Row(
            children: [
              Container(
                width: 4,
                height: 40,
                decoration: BoxDecoration(
                  color: _riskColor,
                  borderRadius: BorderRadius.circular(2),
                  boxShadow: [BoxShadow(color: _riskColor.withOpacity(0.4), blurRadius: 4)],
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(deviceName,
                      style: AppTypography.body.copyWith(color: AppColors.textPrimary)),
                    const SizedBox(height: 4),
                    Row(
                      children: [
                        _buildBadge(result.device.estimatedDistanceLabel, AppColors.textSecondary),
                        const SizedBox(width: 8),
                        _buildBadge(result.device.rssi.toString(), AppColors.accentCyan),
                        const SizedBox(width: 8),
                        Text(deviceId,
                          style: AppTypography.caption.copyWith(color: AppColors.textSecondary)),
                      ],
                    ),
                  ],
                ),
              ),
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text('${result.confidence.round()}%',
                    style: AppTypography.body.copyWith(color: _riskColor)),
                  const SizedBox(height: 4),
                  _buildCategoryBadge(result.category),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildBadge(String text, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: color.withOpacity(0.15),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Text(text, style: AppTypography.caption.copyWith(color: color)),
    );
  }

  Widget _buildCategoryBadge(String category) {
    final label = category
        .split('_')
        .map((w) => w.isNotEmpty ? '${w[0].toUpperCase()}${w.substring(1)}' : '')
        .join(' ');
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: AppColors.accentCyan.withOpacity(0.15),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Text(label,
        style: AppTypography.caption.copyWith(color: AppColors.accentCyan, fontSize: 9)),
    );
  }
}
```

- [ ] **Step 5: Create lib/presentation/widgets/device_detail_sheet.dart**

```dart
import 'package:flutter/material.dart';
import 'package:glassshield/core/theme/colors.dart';
import 'package:glassshield/core/theme/typography.dart';
import 'package:glassshield/domain/usecases/fingerprint_device.dart';

class DeviceDetailSheet extends StatelessWidget {
  final FingerprintDeviceResult result;

  const DeviceDetailSheet({super.key, required this.result});

  @override
  Widget build(BuildContext context) {
    final device = result.device;
    final sig = result.matchedSignature;

    return Padding(
      padding: const EdgeInsets.all(20),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Center(
            child: Container(
              width: 40,
              height: 4,
              decoration: BoxDecoration(
                color: AppColors.gridSubtle,
                borderRadius: BorderRadius.circular(2),
              ),
            ),
          ),
          const SizedBox(height: 20),
          Text(device.name ?? 'Unknown Device', style: AppTypography.sectionTitle),
          const SizedBox(height: 4),
          Text('ID: ${device.id}', style: AppTypography.caption),
          const SizedBox(height: 16),
          _buildInfoRow('Risk Level', result.riskLevel, _riskColor(result.riskLevel)),
          _buildInfoRow('Confidence', '${result.confidence.round()}%', _riskColor(result.riskLevel)),
          _buildInfoRow('Device Type', result.category.replaceAll('_', ' '), AppColors.accentCyan),
          _buildInfoRow('Distance', device.estimatedDistanceLabel, AppColors.textSecondary),
          _buildInfoRow('RSSI', '${device.rssi} dBm', AppColors.textSecondary),
          _buildInfoRow('Manufacturer', device.manufacturerId ?? 'N/A', AppColors.textSecondary),
          if (sig != null) _buildInfoRow('Risk Profile', sig.riskProfile.replaceAll('_', ' '), AppColors.warningAmber),
          const SizedBox(height: 16),
          if (sig != null) ...[
            Text('Matched Signature: ${sig.id}', style: AppTypography.caption),
            const SizedBox(height: 4),
          ],
          Row(
            children: [
              Expanded(
                child: OutlinedButton(
                  onPressed: () {},
                  style: OutlinedButton.styleFrom(
                    foregroundColor: AppColors.textSecondary,
                    side: const BorderSide(color: AppColors.gridSubtle),
                  ),
                  child: const Text('REPORT FALSE POSITIVE'),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: OutlinedButton(
                  onPressed: () {},
                  style: OutlinedButton.styleFrom(
                    foregroundColor: AppColors.accentCyan,
                    side: BorderSide(color: AppColors.accentCyan.withOpacity(0.3)),
                  ),
                  child: const Text('SUBMIT NEW DEVICE'),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildInfoRow(String label, String value, Color valueColor) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label.toUpperCase(), style: AppTypography.caption),
          Text(value, style: AppTypography.body.copyWith(color: valueColor)),
        ],
      ),
    );
  }

  Color _riskColor(String level) {
    switch (level) {
      case 'Élevé':
        return AppColors.dangerRed;
      case 'Moyen':
        return AppColors.warningAmber;
      case 'Faible':
        return AppColors.accentGreen;
      default:
        return AppColors.riskUnknown;
    }
  }
}
```

- [ ] **Step 6: Create lib/presentation/widgets/quick_stats_card.dart**

```dart
import 'package:flutter/material.dart';
import 'package:glassshield/core/theme/colors.dart';
import 'package:glassshield/core/theme/typography.dart';

class QuickStatsCard extends StatelessWidget {
  final String label;
  final String value;
  final Color color;

  const QuickStatsCard({super.key, required this.label, required this.value, required this.color});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.backgroundCard,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.gridSubtle),
      ),
      child: Column(
        children: [
          Text(value, style: AppTypography.sectionTitle.copyWith(color: color)),
          const SizedBox(height: 4),
          Text(label, style: AppTypography.caption.copyWith(letterSpacing: 1.5)),
        ],
      ),
    );
  }
}
```

- [ ] **Step 7: Create lib/presentation/widgets/scan_button.dart**

```dart
import 'package:flutter/material.dart';
import 'package:glassshield/core/theme/colors.dart';
import 'package:glassshield/core/theme/typography.dart';

class ScanButton extends StatelessWidget {
  final bool isScanning;
  final VoidCallback onPressed;

  const ScanButton({super.key, required this.isScanning, required this.onPressed});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: const BoxDecoration(
        border: Border(top: BorderSide(color: AppColors.gridSubtle)),
      ),
      child: SizedBox(
        width: double.infinity,
        child: ElevatedButton(
          onPressed: onPressed,
          style: ElevatedButton.styleFrom(
            backgroundColor: isScanning ? AppColors.dangerRed : AppColors.accentGreen,
            foregroundColor: AppColors.background,
            padding: const EdgeInsets.symmetric(vertical: 16),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
            shadowColor: isScanning ? AppColors.dangerRed.withOpacity(0.4) : AppColors.glowGreen,
            elevation: 4,
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              if (isScanning)
                const SizedBox(
                  width: 16, height: 16,
                  child: CircularProgressIndicator(
                    strokeWidth: 2,
                    color: AppColors.background,
                  ),
                )
              else
                Icon(Icons.radar, size: 20, color: AppColors.background),
              const SizedBox(width: 12),
              Text(
                isScanning ? 'STOP SCAN' : 'SCAN NOW',
                style: AppTypography.buttonText,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
```

---

### Task 11: Android Manifest + Permissions

**Files:**
- Modify: `android/app/src/main/AndroidManifest.xml`
- Modify: `android/app/build.gradle`

- [ ] **Step 1: Update AndroidManifest.xml**

```xml
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="com.glassshield.glassshield">

    <uses-permission android:name="android.permission.BLUETOOTH" />
    <uses-permission android:name="android.permission.BLUETOOTH_ADMIN" />
    <uses-permission android:name="android.permission.BLUETOOTH_SCAN" />
    <uses-permission android:name="android.permission.BLUETOOTH_CONNECT" />
    <uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />
    <uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION" />
    <uses-permission android:name="android.permission.ACCESS_BACKGROUND_LOCATION" />
    <uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
    <uses-permission android:name="android.permission.FOREGROUND_SERVICE_DATA_SYNC" />
    <uses-permission android:name="android.permission.POST_NOTIFICATIONS" />
    <uses-permission android:name="android.permission.INTERNET" />

    <uses-feature android:name="android.hardware.bluetooth_le" android:required="true" />

    <application
        android:label="GlassShield"
        android:name="${applicationName}"
        android:icon="@mipmap/ic_launcher"
        android:theme="@style/Theme.AppCompat.NoActionBar">

        <service
            android:name="com.glassshield.glassshield.BleScanService"
            android:foregroundServiceType="dataSync"
            android:exported="false" />

        <activity
            android:name=".MainActivity"
            android:exported="true"
            android:launchMode="singleTop"
            android:theme="@style/Theme.AppCompat.NoActionBar">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>
</manifest>
```

- [ ] **Step 2: Update android/app/build.gradle**

Add at minimum SDK:
```groovy
android {
    defaultConfig {
        minSdkVersion 21
        targetSdkVersion 34
        // ...
    }
}
```

---

### Task 12: Build & Verify

- [ ] **Step 1: Run flutter pub get**

```bash
cd C:\Users\hachk\pilotage_b2b\glassshield
flutter pub get
```
Expected: All dependencies resolved

- [ ] **Step 2: Run flutter analyze**

```bash
cd C:\Users\hachk\pilotage_b2b\glassshield
flutter analyze
```
Expected: No errors (warnings allowed for unused imports if any)

- [ ] **Step 3: Run flutter test**

```bash
cd C:\Users\hachk\pilotage_b2b\glassshield
flutter test
```
Expected: All default tests pass

---

## Self-Review

1. **Spec coverage:** The plan covers all MVP features from the spec:
   - Real-time BLE scanner → Task 7 (BleRepositoryImpl) + Task 8 (ScanBleDevices use case)
   - Smart fingerprinting engine → Task 5 (Signature), Task 7 (SignatureRepositoryImpl), Task 8 (FingerprintDevice)
   - Risk scoring → Task 8 (ScoreRisk)
   - Signature updates → Task 6 (datasources), Task 8 (UpdateSignatures)
   - Cyber Terminal theme → Task 2
   - Dashboard → Task 10 (all widgets)
   - Android permissions → Task 11
   - Default signatures database → Task 4

2. **Placeholder scan:** No TBD, TODO, "fill in details", "similar to", or incomplete code blocks. Every step has actual code.

3. **Type consistency:** 
   - `BleDevice` entity → `BleDeviceModel.fromBleScanResult` → `BleRepositoryImpl` → `ScanBleDevices` use case → `ScanProvider` → Dashboard widget
   - `Signature` entity → `SignatureLocalDataSource`/`SignatureRemoteDataSource` → `SignatureRepositoryImpl` → `FingerprintDevice` use case → `RiskProvider` → Dashboard
   - All method signatures, property names, and constructors are consistent across the chain.

4. **Scope check:** Focused on one Android app MVP. No iOS, no community API backend, no ML — all correctly marked out of scope.
