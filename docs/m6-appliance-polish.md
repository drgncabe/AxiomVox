# M6 Appliance Polish

M6 tightens the early appliance experience after hardware testing.

## Button Feel

The Whisplay button long-press threshold is now:

```text
0.8 seconds
```

Whisplay remains reserved for recording controls. The PiSugar button remains
reserved for system/menu controls.

## PiSugar Diagnostics

The web console now includes:

```text
/settings/pisugar
```

It reports:

- `pisugar-server` service state
- PiSugar API reachability
- model response
- battery response
- button/button-enable responses
- I2C fallback register readability

When the PiSugar service is unstable, use the Logs page and search for:

```text
pisugar
```
