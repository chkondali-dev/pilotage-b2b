# GlassShield — Design Specification

## Overview

**Project:** GlassShield — Smart Wearable & Connected Glasses Detection App
**Type:** Android mobile application (Flutter, iOS-ready architecture)
**Core Function:** Detect nearby BLE smart glasses, wearable cameras, and camera-capable devices using fingerprinting and behavioral analysis.
**Important:** The app does NOT claim a person is recording — it estimates probability and classifies devices based on BLE signatures and behavior patterns.

---

## 1. Visual Design — Cyber Terminal

### Color Palette
| Role | Color | Hex |
|------|-------|-----|
| Background primary | Deep black | `#0A0F1C` |
| Background secondary | Dark navy | `#111827` |
| Background card | Slate dark | `#1A2332` |
| Accent primary | Neon green | `#00FF88` |
| Accent secondary | Cyan | `#00D4FF` |
| Warning / Medium risk | Amber | `#FFB800` |
| High risk | Red | `#FF4757` |
| Text primary | White | `#FFFFFF` |
| Text secondary | Gray muted | `#94A3B8` |
| Grid overlay | Very subtle | `#1E293B` |

### Typography
- **Primary font:** `JetBrains Mono` (monospace) for all text — reinforces terminal/hacker aesthetic
- **Fallback:** `Roboto Mono`, `monospace`
- **Hierarchy:**
  - H1 (device count / risk score): 48px bold
  - H2 (section titles): 20px semibold
  - Body: 14px regular
  - Caption: 11px regular, muted color

### Visual Elements
- **Grid overlay:** Subtle dot or line grid in background, opacity 5-10%
- **Scan lines:** Horizontal scan line animation sweeping across radar area
- **Glow effects:** Text and icons have subtle cyan/green glow (`box-shadow: 0 0 10px`)
- **Card borders:** 1px subtle glow borders on cards
- **Radar:** Circular pulsing radar animation with concentric rings, detected devices as dots positioned by estimated angle/distance

### Animations
- Radar pulse: concentric circles expanding and fading, every 2s
- Scan line sweep: horizontal line moving top to bottom, every 1.5s
- Risk indicator: color transitions smoothly on score change
- Device dot: gentle pulse when newly detected

---

## 2. Technical Stack

### Framework
- **Flutter** (Android first, iOS-ready)
- Language: Dart
- Minimum Android SDK: 21 (Android 5.0)
- Target: Android 12+ for full BLE 5.0 support

### Key Dependencies
- `flutter_blue_plus` — BLE scanning and connectivity
- `flutter_local_notifications` — push notifications for background alerts
- `android_background_service` — foreground service for continuous scanning
- `shared_preferences` / `hive` — local storage for settings and detection history
- `http` — HTTP client for OTA signature updates
- `web_scraper` / `html` — lightweight HTML parsing for web scraping
- `provider` or `riverpod` — state management
- `permission_handler` — runtime permission management (Bluetooth, Location)

### Architecture
Clean Architecture with 3 layers:
1. **Presentation** — UI widgets, screens, state management
2. **Domain** — business logic, fingerprinting engine, risk scoring, use cases
3. **Data** — repositories, BLE service wrapper, remote data sources, local DB

---

## 3. Core Features

### 3.1 Real-Time BLE Scanner
- Continuous BLE scanning via foreground service
- Auto-refresh with configurable interval (default: 3s)
- Low-latency detection (scan window optimization)
- Battery-aware scanning (adaptive interval based on battery level)
- Permissions: `BLUETOOTH_SCAN`, `BLUETOOTH_CONNECT`, `ACCESS_FINE_LOCATION`, `ACCESS_BACKGROUND_LOCATION`

**Displayed per device:**
- Device name (or "Unknown Device")
- RSSI (signal strength in dBm)
- Estimated distance (Close < 3m / Near 3-10m / Far > 10m)
- Manufacturer ID (hex)
- Advertised Service UUIDs
- Device category (smart_glasses / wearable_camera / ar_glasses / ai_wearable / unknown)
- Confidence score (0-100%)

### 3.2 Smart Device Fingerprinting Engine

**Signature Database (JSON):**
```json
{
  "signatures": [
    {
      "id": "rayban_meta_1",
      "device_name_patterns": ["RayBan", "Meta", "RBM", "EssilorLuxottica"],
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
      "service_uuids": ["FE2C", "FE3A"],
      "device_type": "wearable_camera",
      "risk_profile": "camera_capable",
      "confidence_weight": 0.80
    }
  ]
}
```

**Fingerprinting Algorithm:**
1. Extract raw BLE data (name, manufacturer ID, UUIDs, RSSI series)
2. Match against known signatures (exact match on manufacturer ID + name patterns)
3. Score based on: name pattern match (weighted), UUID match, manufacturer ID match
4. Behavioral analysis: check TX frequency, RSSI variance, advertisement regularity
5. Combine scores → final confidence (0-100%)
6. If confidence >= 60% → categorized. If < 60% → "unknown_wearable"
7. Risk profile derived from device_type: camera_capable = elevated risk, audio_only = low risk

### 3.3 Signature Update System — Hybrid

**Automatic Web Scraping:**
- App checks predefined sources on configurable schedule (default: daily)
- Sources: manufacturer BLE pages, public BLE device databases, tech news feeds
- Parses new device announcements, extracts signature patterns
- Runs in background via WorkManager

**Crowdsourced Community:**
- Users can submit new device signatures they discover
- Submission: name, RSSI series, manufacturer ID, UUIDs, device type
- Submitted via API to community backend
- Community votes / validates submissions
- Validated signatures merged into main database

**Update Flow:**
1. App starts → check if update needed (cache timestamp < 24h)
2. Fetch remote JSON from community API / GitHub raw
3. Diff with local base → merge new signatures
4. Store merged base in local JSON
5. On app update failure → use cached version

### 3.4 Risk Scoring

**Global Risk Score (0-100):**
- Based on: number of detected risky devices, their confidence, proximity, and risk profile
- Formula: weighted average of per-device risk scores, proximity boost for close devices
- Displayed as circular gauge with color gradient (green → amber → red)

**Per-Device Risk Level:**
- **Faible (Low):** audio-only devices, non-camera wearables, confidence < 40%
- **Moyen (Medium):** smart glasses without camera, or unknown devices with behavioral anomalies, confidence 40-70%
- **Élevé (High):** confirmed camera-capable devices, confidence >= 70%
- **Inconnu (Unknown):** no signature match, low behavioral score

### 3.5 Scan Modes

**Background Mode (Continuous):**
- Foreground service with persistent notification ("GlassShield is scanning")
- Scanning interval: adaptive (1s when device detected nearby, 5s idle)
- Local notification when new device detected with risk level
- Scan results stored locally for history

**Manual Mode (On-Demand):**
- User taps "Scan Now" button on dashboard
- Immediate scan for 10-15 seconds
- Results displayed in real-time on dashboard
- No background service active in this mode

### 3.6 Dashboard (Single Screen)

**Layout (top to bottom):**
1. **Status Bar** — "GlassShield" logo + scan mode toggle (BG / Manual)
2. **Global Risk Indicator** — large circular gauge (0-100), color-coded, center shows score
3. **Radar Area** — circular visual, devices shown as dots positioned by estimated distance/angle, concentric rings, scan line animation
4. **Quick Stats Row** — 3 cards: "Devices Found", "High Risk", "Last Scan"
5. **Detection List** — scrollable list of detected devices:
   - Each row: name, distance badge, risk level badge, confidence bar, chevron
   - Tap → detail bottom sheet
6. **Bottom Action Bar** — "Scan Now" button (prominent, green glow)

**Device Detail Bottom Sheet:**
- Full device name
- All technical details (RSSI, manufacturer ID, UUIDs, timestamps)
- Risk level with explanation
- Behavioral pattern graph (TX frequency over last 30s)
- "Report false positive" / "Submit new device" actions

---

## 4. Project Structure

```
glassshield/
├── lib/
│   ├── main.dart
│   ├── app.dart
│   ├── core/
│   │   ├── theme/
│   │   │   ├── app_theme.dart
│   │   │   ├── colors.dart
│   │   │   └── typography.dart
│   │   ├── constants/
│   │   │   └── app_constants.dart
│   │   └── utils/
│   │       └── distance_estimator.dart
│   ├── data/
│   │   ├── datasources/
│   │   │   ├── ble_scanner_datasource.dart
│   │   │   ├── signature_remote_datasource.dart
│   │   │   └── signature_local_datasource.dart
│   │   ├── models/
│   │   │   ├── ble_device_model.dart
│   │   │   ├── signature_model.dart
│   │   │   └── detection_record_model.dart
│   │   └── repositories/
│   │       ├── ble_repository_impl.dart
│   │       └── signature_repository_impl.dart
│   ├── domain/
│   │   ├── entities/
│   │   │   ├── ble_device.dart
│   │   │   └── signature.dart
│   │   ├── usecases/
│   │   │   ├── scan_ble_devices.dart
│   │   │   ├── fingerprint_device.dart
│   │   │   ├── score_risk.dart
│   │   │   └── update_signatures.dart
│   │   └── repositories/
│   │       ├── ble_repository.dart
│   │       └── signature_repository.dart
│   └── presentation/
│       ├── providers/
│       │   ├── scan_provider.dart
│       │   ├── signatures_provider.dart
│       │   └── risk_provider.dart
│       ├── screens/
│       │   └── dashboard_screen.dart
│       └── widgets/
│           ├── risk_gauge.dart
│           ├── radar_widget.dart
│           ├── device_list_item.dart
│           ├── device_detail_sheet.dart
│           ├── quick_stats_card.dart
│           └── scan_button.dart
├── assets/
│   └── signatures/
│       └── default_signatures.json
├── android/
│   └── app/src/main/AndroidManifest.xml
└── pubspec.yaml
```

---

## 5. Permissions Required

| Permission | Purpose |
|---|---|
| `BLUETOOTH_SCAN` | Scan for BLE devices |
| `BLUETOOTH_CONNECT` | Connect to BLE devices |
| `ACCESS_FINE_LOCATION` | Required for BLE scanning on Android |
| `ACCESS_COARSE_LOCATION` | Fallback location |
| `FOREGROUND_SERVICE` | Background scanning |
| `POST_NOTIFICATIONS` | Android 13+ notification permission |
| `INTERNET` | OTA signature updates, community API |

---

## 6. Data Models

### BLE Device
```
- id: String (MAC address or stable UUID)
- name: String?
- rssi: int
- manufacturerId: String?
- serviceUuids: List<String>
- advertisedServices: List<String>
- txPower: int?
- advertisementSize: int?
- lastSeen: DateTime
- isConnectable: bool
```

### Signature
```
- id: String
- deviceNamePatterns: List<String>
- manufacturerId: String?
- serviceUuids: List<String>
- advertisedServices: List<String>
- deviceType: String (smart_glasses | wearable_camera | ar_glasses | ai_wearable | unknown)
- riskProfile: String (camera_capable | audio_only | ambient | unknown)
- confidenceWeight: double
- behaviorPatterns: BehaviorPattern?
```

### Detection Record
```
- deviceId: String
- deviceName: String
- category: String
- riskLevel: String
- confidence: double
- firstDetected: DateTime
- lastDetected: DateTime
- detectionCount: int
- avgRssi: double
```

---

## 7. Scoping Notes

**In Scope (MVP):**
- Android BLE scanning (foreground service)
- Local signature database (bundled JSON)
- Fingerprinting engine (exact + heuristic match)
- Single dashboard UI
- Risk scoring
- Manual scan + background scan toggle
- OTA signature update check (basic HTTP fetch)

**Out of Scope (Post-MVP):**
- iOS build
- Community submission API (requires backend)
- Web scraping engine (requires server-side)
- ML-based fingerprinting
- Detection history persistence (full DB)
- Widget / quick settings tile
- Multiple language support
