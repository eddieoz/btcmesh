# Mobile Platform Analysis for BTCMesh

**Date:** December 2025
**Status:** Research findings for future reference

## Executive Summary

This document captures the findings from investigating iOS support for the BTCMesh client application. The current Kivy-based GUI cannot be practically deployed to iOS due to Bluetooth Low Energy (BLE) library limitations, not Kivy itself.

---

## Current Architecture

```
BTCMesh Client (Kivy/Python)
         │
         ├── USB Serial ──► Meshtastic Device
         └── BLE (Bleak) ──► Meshtastic Device
                              │
                              │ LoRa Radio
                              ▼
                     BTCMesh Server (Python)
                              │
                              ▼
                     Bitcoin Core RPC
```

### Technology Stack
- **GUI Framework:** Kivy (Python)
- **Meshtastic Communication:** `meshtastic` Python library
- **BLE Backend:** Bleak library
- **Platforms Supported:** Windows, macOS, Linux

---

## iOS Deployment Analysis

### Why Kivy Was Chosen
Kivy was selected because it advertises cross-platform support including iOS and Android, allowing a single Python codebase to target all platforms.

### The Blocker: BLE on iOS

The issue is **not Kivy** but the **Meshtastic Python library's BLE dependency**:

| Component | iOS Support |
|-----------|-------------|
| Kivy GUI | ✅ Works via kivy-ios toolchain |
| Python Core | ✅ Works via kivy-ios |
| USB Serial | ❌ Not available on iOS |
| Bleak (BLE) | ⚠️ Partial - requires Pythonista app, not kivy-ios |

#### Bleak iOS Limitations
- Bleak's iOS support is via a 3rd-party module (`bleak-pythonista`)
- Designed for the Pythonista iOS app, NOT kivy-ios builds
- CoreBluetooth on iOS doesn't expose MAC addresses (uses UUIDs instead)
- Integrating Bleak into kivy-ios would require significant custom work

### Android Viability
Android is more feasible with Kivy:
- kivy-ios equivalent: Buildozer/python-for-android
- Bleak has a python-for-android backend
- USB OTG serial possible on some devices
- However, BLE support is marked as "not fully tested"

---

## Alternative Approaches Evaluated

### Option 1: Flutter (Recommended for Mobile)

| Aspect | Details |
|--------|---------|
| Language | Dart |
| iOS Support | ✅ Excellent, native CoreBluetooth |
| Android Support | ✅ Excellent |
| BLE Library | flutter_blue_plus (mature, well-maintained) |
| Desktop Support | ✅ Windows, macOS, Linux |
| Learning Curve | Moderate (Dart is similar to JS/Java) |
| Code Reuse | None from Python codebase |

**Effort Estimate:** 2-4 weeks for experienced Flutter developer

### Option 2: React Native

| Aspect | Details |
|--------|---------|
| Language | JavaScript/TypeScript |
| iOS Support | ✅ Good |
| Android Support | ✅ Good |
| BLE Library | react-native-ble-plx |
| Desktop Support | ⚠️ Limited (Electron wrapper) |
| Code Reuse | None from Python codebase |

### Option 3: Native Development (Swift + Kotlin) ⭐ RECOMMENDED

| Aspect | Details |
|--------|---------|
| Languages | Swift (iOS), Kotlin (Android) |
| BLE Support | ✅ Best possible (native APIs) |
| Maintenance | Two separate codebases |
| Code Reuse | None, but Meshtastic has reference implementations |
| Team Fit | ✅ Swift developer available on team |

**Key Advantage:** The official Meshtastic iOS app is written in Swift/SwiftUI, providing direct reference code for BLE communication patterns.

### Option 4: Keep Desktop-Only + Web Companion

| Aspect | Details |
|--------|---------|
| Approach | Users use official Meshtastic mobile app |
| BTCMesh Role | Simple web form to format transactions |
| Effort | Minimal |
| User Experience | Degraded (two apps needed) |

---

## Recommended Strategy

### Team Considerations

With a **Swift developer already on the team**, native iOS development becomes the preferred approach:

| Factor | Native Swift | Flutter |
|--------|--------------|---------|
| iOS development | ✅ Ready now | ⏳ Learn Dart first |
| Reference code | ✅ Meshtastic-Apple (Swift) | 🔄 Must translate |
| BLE reliability | ✅ Best possible | Very good |
| Android later | Need Kotlin dev or learn Flutter | Same codebase |

### Recommended Approach

1. **Keep Kivy for Desktop/Server** - Works perfectly, well-tested
2. **Keep Python CLI** - Power users, scripting
3. **Build native Swift iOS app** - Leverage existing team expertise
4. **Decide on Android later** - Either find Kotlin dev, or have Swift dev learn Flutter for unified v2

**Note:** The Meshtastic team maintains both native apps separately (Swift + Kotlin), validating this as a viable approach for BLE-heavy applications.

### Hybrid Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Desktop App    │     │   iOS App       │     │  Android App    │
│  (Kivy/Python)  │     │   (Swift)       │     │  (TBD)          │
│                 │     │                 │     │                 │
│  ✅ KEEP        │     │  🆕 NEW         │     │  📋 FUTURE      │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         │ USB/Serial            │ BLE                   │ BLE/USB
         ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Meshtastic Device                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ LoRa
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              BTCMesh Server (Python - unchanged)                │
└─────────────────────────────────────────────────────────────────┘
```

---

## What Would Need Implementing in Swift

### Core Protocol (Simple)
- Transaction hex chunking (`BTC_TX|session|chunk/total|payload`)
- ACK/NACK message parsing
- Session ID generation

### BLE Communication
- Meshtastic service/characteristic UUIDs (reference: Meshtastic-Apple)
- CoreBluetooth integration for read/write
- Connection state management
- Handle iOS UUID-based device identification (no MAC addresses)

### UI Components (SwiftUI)
- Transaction input (paste from clipboard)
- QR code scanner (native iOS AVFoundation)
- Destination node selection
- Connection status display
- Activity log

### Reference Resources
- **Meshtastic iOS app (Swift):** https://github.com/meshtastic/Meshtastic-Apple
  - Primary reference for BLE communication patterns
  - Shows how to handle CoreBluetooth on iOS
- Meshtastic Android app (Kotlin): https://github.com/meshtastic/Meshtastic-Android
- Meshtastic protobuf definitions: https://github.com/meshtastic/protobufs

---

## Lessons Learned

1. **BLE + Python + iOS = Problematic**
   When hardware communication (BLE, USB) is required on mobile, Python frameworks are not the right choice.

2. **"Cross-platform" Has Limits**
   Kivy is cross-platform for the GUI layer, but dependencies may not be.

3. **Validate Dependencies Early**
   Before choosing a framework, verify ALL critical dependencies work on target platforms.

4. **Native or Flutter/React Native for Mobile Hardware**
   These frameworks have mature, native BLE libraries that work reliably on iOS and Android.

5. **Consider Team Expertise**
   When choosing between frameworks, existing team skills can outweigh theoretical advantages. A Swift developer can ship native iOS faster than learning Flutter.

6. **Desktop GUI: Kivy vs Qt**
   If starting fresh for desktop-only, **PySide6 (Qt)** would be preferred over Kivy:
   - Native look and feel on each OS
   - Better text input handling (OS-native behavior)
   - Larger community and documentation
   - Qt Designer for visual layout
   - No false mobile promises

   However, Kivy works fine for desktop. The issue wasn't Kivy itself—it was choosing Kivy *for the wrong reason* (mobile promise that didn't deliver due to BLE limitations).

---

## Decision Record

| Date | Decision | Rationale |
|------|----------|-----------|
| 2025-12 | Keep Kivy for desktop | Works well, significant investment |
| 2025-12 | Server remains Python | No mobile requirement |
| 2025-12 | iOS: Native Swift over Flutter | Swift developer on team, direct Meshtastic-Apple reference |
| 2025-12 | Android: Defer decision | Evaluate Kotlin vs Flutter after iOS ships |

---

## References

- Kivy iOS Toolchain: https://github.com/kivy/kivy-ios
- Bleak BLE Library: https://github.com/hbldh/bleak
- Bleak Backend Documentation: https://bleak.readthedocs.io/en/latest/backends/index.html
- Flutter Blue Plus: https://pub.dev/packages/flutter_blue_plus
- Meshtastic Python Library: https://github.com/meshtastic/python
