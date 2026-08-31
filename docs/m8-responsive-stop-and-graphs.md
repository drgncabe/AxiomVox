# M8 Responsive Stop And Graphs

M8 improves the appliance feel during recording stop and adds simple runtime
graphs to the web dashboard.

## Responsive Stop

Whisplay long press now acknowledges stop immediately:

```text
AxiomVox STOP
Stopping...
Saving WAV
Please wait
```

The stop chime plays as soon as the stop request is accepted. WAV finalization,
audio validation, metadata updates, and recent-session updates continue in the
background. When finalization completes, the device returns to READY.

The synchronous stop path remains available for service shutdown and direct
session tests.

## CPU And RAM Graphs

The dashboard records a bounded in-memory history of recent system samples and
renders lightweight canvas graphs for:

- CPU usage
- RAM usage

The dashboard refreshes graph data from `/api/status` every five seconds.

## Brightness Note

AxiomVox now tries several Whisplay runtime brightness methods/properties and
reports the method used. On hardware detected as `Simple Switch`, the backlight
may only support off/on behavior; nonzero brightness levels can look identical.
