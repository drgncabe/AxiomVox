# Product Decisions

This document records the V1 decisions established before implementation.

## Product Shape

AxiomVox is an appliance first. M0 prioritizes reliable boot, clear status,
hardware validation, and safe shutdown before any recording or transcription
features are implemented.

The user experience should keep common actions visible and simple while placing
deeper configuration under Settings, Advanced, and Development areas.

## Target Hardware

V1/M0 supports two device profiles:

- Raspberry Pi Zero W with Raspberry Pi OS Lite 32-bit.
- Raspberry Pi Zero 2 W with Raspberry Pi OS Lite 64-bit.
- PiSugar Whisplay HAT
- PiSugar 3 UPS
- HDMI as a passive secondary display

The Zero W profile is the most constrained target and should be treated as the
minimum viable appliance hardware. The Zero 2 W profile is preferred when more
headroom is available.

Other Raspberry Pi boards and displays are deferred until after V1.

## Physical Controls

The Whisplay and PiSugar buttons have separate responsibilities:

- Whisplay button: recording controls.
- PiSugar button: system menu controls and graceful shutdown.

For M0, buttons are detected and reported only. Recording and menu navigation
are future work.

## Display Behavior

The Whisplay LCD shows an appliance-style READY screen that is useful at a
glance. HDMI mirrors the same shared application state in a larger passive
status view. HDMI does not introduce a separate control surface in M0.

## Web Configurator

The M0 web configurator exposes:

- Dashboard/status shell.
- Graceful Shutdown action.

Future sections are documented but not implemented:

- Sessions
- Device
- Transcription
- Settings
- Advanced
- Development

## Shutdown

Shutdown must be graceful. The application should update device state, stop
services cleanly, and then request the operating system shutdown path. Recording
flush/close behavior will be added when recording exists.
