# M1 Appliance Loop

M1 turns the M0 status shell into the first real appliance loop. It still does
not implement recording or transcription.

## Scope

- Render the READY/menu/shutdown-confirm state through shared display renderers.
- Attempt Whisplay LCD updates through the vendor runtime when present.
- Poll early Whisplay and PiSugar button sources.
- Keep Whisplay button gestures reserved for recording controls.
- Use PiSugar button gestures for system/menu controls.
- Provide a self-test command for fast bench diagnostics.

## Control Map

| Control | Gesture | M1 behavior |
| --- | --- | --- |
| Whisplay button | short | Reserved for future start/bookmark |
| Whisplay button | long | Reserved for future stop |
| PiSugar button | short | Open/advance system menu |
| PiSugar button | long | Select menu item |
| PiSugar button | very long | Open shutdown confirmation |

## Self-Test

```bash
axiomvox-device --self-test --no-lcd
```

On hardware with the Whisplay runtime and `python3-pil` installed, omit
`--no-lcd` to include LCD rendering in the self-test.

To test only the Whisplay LCD backlight:

```bash
axiomvox-device --lcd-on
```

If the LCD-inclusive self-test reports `Device or resource busy`, the running
`axiomvox.service` probably already owns the Whisplay SPI/GPIO device. Stop the
service before running that test:

```bash
sudo systemctl stop axiomvox.service
axiomvox-device --self-test
sudo systemctl start axiomvox.service
```

## Notes

PiSugar Server is still useful when it runs cleanly, but AxiomVox keeps direct
PiSugar 3 I2C fallbacks for Zero W systems where the vendor server binary is
not stable.
