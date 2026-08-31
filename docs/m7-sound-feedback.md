# M7 Sound Feedback

M7 adds optional local chimes and volume controls.

## Behavior

- Start recording plays a short rising chime.
- Stop recording plays a short falling chime after the WAV has finalized.
- Chimes can be disabled from the web settings page.
- Chime volume can be adjusted from the web settings page.

The sound files are generated locally as tiny WAV files under:

```text
/run/axiomvox/sounds
```

## Web UI

The sound page lives at:

```text
/settings/sound
```

It exposes:

- chimes enabled/disabled
- chime volume presets
- test chime playback

## Configuration

The service defaults are:

```text
--playback-device default
--mixer-control PCM
--chime-volume 60
```

Installer/updater environment variables:

```text
AXIOMVOX_PLAYBACK_DEVICE
AXIOMVOX_MIXER_CONTROL
AXIOMVOX_CHIME_VOLUME
```

## Stop Lag Note

Long-press stop now acknowledges immediately, plays the stop chime, and shows a
Stopping screen while WAV finalization, validation, and metadata writes complete
in the background.
