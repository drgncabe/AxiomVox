from __future__ import annotations

import argparse
import json
import signal
import sys
import time
from pathlib import Path

from shared.axiomvox_shared import AppState

from .config import DeviceConfig
from .display import HdmiRenderer, WhisplayRenderer
from .hardware import HardwareProbe
from .web import StatusServer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the AxiomVox M0 device app")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--allow-shutdown", action="store_true")
    parser.add_argument("--simulate-hardware", action="store_true")
    parser.add_argument("--once", action="store_true", help="Probe and render status once")
    parser.add_argument("--status-file", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = DeviceConfig(
        host=args.host,
        port=args.port,
        allow_shutdown=args.allow_shutdown,
        simulate_hardware=args.simulate_hardware,
        status_file=args.status_file,
    )
    state = AppState()
    probe = HardwareProbe(simulate=config.simulate_hardware)
    whisplay = WhisplayRenderer()
    hdmi = HdmiRenderer()

    state.hardware = probe.collect()
    state.touch()

    if args.once:
        _publish_status(state, whisplay, hdmi, config.status_file)
        return 0

    server = StatusServer(state, config)
    stop = False

    def request_stop(signum: int, frame: object) -> None:
        nonlocal stop
        stop = True

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)

    server.start()
    try:
        while not stop:
            state.hardware = probe.collect()
            state.touch()
            _publish_status(state, whisplay, hdmi, config.status_file)
            time.sleep(10)
    finally:
        server.stop()

    return 0


def _publish_status(
    state: AppState,
    whisplay: WhisplayRenderer,
    hdmi: HdmiRenderer,
    status_file: Path | None,
) -> None:
    print(whisplay.render(state), file=sys.stdout, flush=True)
    print("", file=sys.stdout, flush=True)
    print(hdmi.render(state), file=sys.stdout, flush=True)
    if status_file:
        status_file.parent.mkdir(parents=True, exist_ok=True)
        status_file.write_text(json.dumps(state.to_dict(), indent=2), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
