# M4 Settings And Power

M4 turns the PiSugar system/menu button into a useful settings surface while
keeping the Whisplay button reserved for recording.

## Physical Menu

PiSugar button behavior:

```text
Short press: move to the next item
Long press: select or go back
Very long press: open shutdown confirmation
Very long press on a confirmation screen: request shutdown/reboot
```

Top-level menu:

```text
Status
Settings
Sessions
Power
Brightness
Exit
```

## Settings

The Settings/Status screen shows:

- Uptime
- Memory use
- Load average

HDMI shows the same information passively in the expanded status view.

## Power

The Power menu contains:

```text
Shutdown
Reboot
Back
```

The web dashboard exposes real reboot/shutdown requests when the device service
is running with `--allow-shutdown`. Without that flag, power actions stay in
dry-run mode.

## Brightness

Brightness levels:

```text
20%
40%
60%
80%
100%
```

The web dashboard can set brightness directly. The physical menu cycles through
these levels with short presses on the Brightness screen.

## Known Follow-Up

Long-click recognition can feel laggy on hardware. A future input-tuning pass
should reduce perceived delay without making accidental long presses too easy.
