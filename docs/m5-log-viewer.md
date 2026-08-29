# M5 Log Viewer

M5 adds a read-only log viewer under the Settings section of the web dashboard.
It is intended for appliance diagnostics while the device is still headless or
semi-headless.

## Web UI

The log page lives at:

```text
/settings/logs
```

It supports:

- AxiomVox service logs
- System logs
- Text search/filtering
- Configurable line count from 20 to 1000 lines
- Watch mode, refreshed by browser polling every two seconds

The supporting API is:

```text
GET /api/logs?kind=axiomvox&lines=200&q=button
GET /api/logs?kind=system&lines=200&q=i2c
```

`kind` is intentionally limited to `axiomvox` and `system`.

## Physical Menu

The PiSugar Settings menu now includes:

```text
Display
Power
Logs
Back
```

Selecting Logs on the Whisplay LCD points the user to the web console. The LCD
does not attempt to render scrollable logs.

## Permissions

The installer and updater add the service user to common journal-reading groups
when they exist:

```text
adm
systemd-journal
```

If group membership changes during install/update, a logout or reboot may be
needed before the running service receives the new journal permissions.
