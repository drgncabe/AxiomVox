from __future__ import annotations

import argparse
import json
import signal
import sys
import time
from pathlib import Path

from shared.axiomvox_shared import AppState

from .buttons import PiSugarButtonPoller, WhisplayButtonPoller
from .config import DeviceConfig
from .controls import ApplianceController
from .display import HdmiRenderer, WhisplayRenderer
from .hardware import HardwareProbe
from .lcd import WhisplayLcdDriver
from .sessions import SessionManager
from .web import StatusServer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the AxiomVox M0 device app")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--allow-shutdown", action="store_true")
    parser.add_argument("--simulate-hardware", action="store_true")
    parser.add_argument("--once", action="store_true", help="Probe and render status once")
    parser.add_argument("--self-test", action="store_true", help="Run M1 diagnostics and exit")
    parser.add_argument("--no-lcd", action="store_true", help="Do not attempt Whisplay LCD hardware updates")
    parser.add_argument("--status-file", type=Path)
    parser.add_argument("--session-dir", type=Path, default=Path("/var/lib/axiomvox/sessions"))
    parser.add_argument("--metadata-only", action="store_true", help="Do not launch ALSA capture")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = DeviceConfig(
        host=args.host,
        port=args.port,
        allow_shutdown=args.allow_shutdown,
        simulate_hardware=args.simulate_hardware,
        status_file=args.status_file,
        session_dir=args.session_dir,
        capture_enabled=not args.metadata_only,
    )
    state = AppState()
    probe = HardwareProbe(simulate=config.simulate_hardware)
    sessions = SessionManager(config)
    controller = ApplianceController(sessions)
    pollers = [WhisplayButtonPoller(probe), PiSugarButtonPoller(probe)]
    whisplay = WhisplayRenderer()
    hdmi = HdmiRenderer()
    lcd = None if args.no_lcd else WhisplayLcdDriver()

    state.hardware = probe.collect()
    state.touch()

    if args.self_test:
        return _run_self_test(state, whisplay, hdmi, lcd)

    if args.once:
        _publish_status(state, whisplay, hdmi, lcd, config.status_file)
        return 0

    server = StatusServer(state, config, controller)
    stop = False

    def request_stop(signum: int, frame: object) -> None:
        nonlocal stop
        stop = True

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)

    server.start()
    next_hardware_refresh = 0.0
    next_display_refresh = 0.0
    try:
        while not stop:
            now = time.monotonic()
            if now >= next_hardware_refresh:
                state.hardware = probe.collect()
                state.touch()
                next_hardware_refresh = now + 10

            display_dirty = False
            for poller in pollers:
                for event in poller.poll():
                    controller.handle_button(event, state)
                    display_dirty = True

            if display_dirty or now >= next_display_refresh:
                _publish_status(state, whisplay, hdmi, lcd, config.status_file)
                next_display_refresh = now + 2

            time.sleep(0.2)
    finally:
        if state.current_session is not None:
            sessions.stop(state)
        server.stop()

    return 0


def _publish_status(
    state: AppState,
    whisplay: WhisplayRenderer,
    hdmi: HdmiRenderer,
    lcd: WhisplayLcdDriver | None,
    status_file: Path | None,
) -> None:
    print(whisplay.render(state), file=sys.stdout, flush=True)
    print("", file=sys.stdout, flush=True)
    print(hdmi.render(state), file=sys.stdout, flush=True)
    if lcd is not None:
        print(lcd.render(state), file=sys.stdout, flush=True)
    if status_file:
        status_file.parent.mkdir(parents=True, exist_ok=True)
        status_file.write_text(json.dumps(state.to_dict(), indent=2), encoding="utf-8")


def _run_self_test(
    state: AppState,
    whisplay: WhisplayRenderer,
    hdmi: HdmiRenderer,
    lcd: WhisplayLcdDriver | None,
) -> int:
    checks = [
        ("Whisplay detected", state.hardware.whisplay_detected),
        ("LCD initialized", state.hardware.lcd_initialized),
        ("Microphones detected", state.hardware.microphones_detected),
        ("Whisplay button detected", state.hardware.whisplay_button_detected),
        ("PiSugar detected", state.hardware.pisugar_detected),
        ("Battery readable", state.hardware.battery_percentage is not None),
        ("PiSugar button detected", state.hardware.pisugar_button_detected),
        ("HDMI detected", state.hardware.hdmi_detected),
    ]
    if lcd is not None:
        lcd_result = lcd.render(state)
        checks.append(("Whisplay LCD render", _lcd_render_ok(lcd_result)))
    else:
        lcd_result = "LCD self-test skipped"

    print(whisplay.render(state), file=sys.stdout)
    print("", file=sys.stdout)
    print(hdmi.render(state), file=sys.stdout)
    print("", file=sys.stdout)
    print("M1 Self-Test", file=sys.stdout)
    for name, ok in checks:
        print(f"- {name}: {'PASS' if ok else 'FAIL'}", file=sys.stdout)
    if lcd is not None:
        print(f"- Whisplay LCD detail: {lcd_result}", file=sys.stdout)
        if _lcd_resource_busy(lcd_result):
            print(
                "- Whisplay LCD hint: stop axiomvox.service before running an LCD-inclusive self-test",
                file=sys.stdout,
            )

    return 0 if all(ok for _, ok in checks) else 1


def _lcd_render_ok(result: str) -> bool:
    return "updated" in result.lower()


def _lcd_resource_busy(result: str) -> bool:
    lowered = result.lower()
    return "device or resource busy" in lowered or "errno 16" in lowered


if __name__ == "__main__":
    raise SystemExit(main())
