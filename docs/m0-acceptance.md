# M0 Acceptance Criteria

M0 is complete when the device can boot as an appliance, validate its hardware,
show status locally, expose a small web dashboard, and shut down gracefully.

Supported M0 board profiles:

- Raspberry Pi Zero W with Raspberry Pi OS Lite 32-bit.
- Raspberry Pi Zero 2 W with Raspberry Pi OS Lite 64-bit.

## Required Checks

| Check | M0 Result |
| --- | --- |
| Whisplay detected | Reported in diagnostics |
| LCD initialized | Reported in diagnostics and READY renderer |
| Microphones detected | Reported in diagnostics |
| Whisplay button detected | Reported in diagnostics |
| PiSugar detected | Reported in diagnostics |
| Battery percentage readable | Reported when available |
| PiSugar button detected | Reported in diagnostics |
| HDMI detected | Reported in diagnostics |
| Web service reachable | `/healthz` and dashboard respond |
| AxiomVox starts automatically | systemd unit provided |

## M0 Screens

Whisplay shows:

- AxiomVox READY.
- Hardware health summary.
- Battery percentage when readable.
- Network/web status.

HDMI shows:

- Same shared application state.
- Expanded hardware checklist.
- Passive status only.

## M0 Web

The web configurator exposes:

- Dashboard/status.
- JSON status endpoint.
- Health endpoint.
- Graceful Shutdown action.

The following sections are placeholders for future milestones:

- Sessions
- Device
- Transcription
- Settings
- Advanced
- Development
