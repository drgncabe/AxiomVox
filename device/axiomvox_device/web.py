from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import parse_qs, unquote

from shared.axiomvox_shared import AppState

from .config import DeviceConfig
from .controls import ApplianceController
from .events import ButtonEvent
from .shutdown import ShutdownController


class StatusServer:
    def __init__(
        self,
        state: AppState,
        config: DeviceConfig,
        controller: ApplianceController | None = None,
    ) -> None:
        self.state = state
        self.config = config
        self.shutdown = ShutdownController(config)
        self.controller = controller or ApplianceController()
        self.httpd = ThreadingHTTPServer((config.host, config.port), self._handler())
        self.thread = Thread(target=self.httpd.serve_forever, daemon=True)

    def start(self) -> None:
        self.thread.start()
        self.state.web_reachable = True
        self.state.touch()

    def stop(self) -> None:
        self.httpd.shutdown()
        self.thread.join(timeout=2)
        self.state.web_reachable = False
        self.state.touch()

    def _handler(self) -> type[BaseHTTPRequestHandler]:
        state = self.state
        config = self.config
        shutdown = self.shutdown
        controller = self.controller

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                if self.path == "/healthz":
                    self._send_text("ok\n", HTTPStatus.OK)
                    return
                if self.path == "/api/status":
                    self._send_json(state.to_dict())
                    return
                if self.path == "/api/diagnostics":
                    self._send_json({"diagnostics": state.to_dict()["hardware"]["diagnostics"]})
                    return
                if self.path == "/api/sessions":
                    self._send_json(
                        {
                            "current_session": state.to_dict()["current_session"],
                            "recent_sessions": state.to_dict()["recent_sessions"],
                        }
                    )
                    return
                if self.path.startswith("/sessions/"):
                    self._send_session_file()
                    return
                if self.path == "/" or self.path.startswith("/?"):
                    self._send_text(render_dashboard(state), HTTPStatus.OK, "text/html; charset=utf-8")
                    return
                self._send_text("not found\n", HTTPStatus.NOT_FOUND)

            def do_POST(self) -> None:
                length = int(self.headers.get("content-length", "0"))
                body = self.rfile.read(length).decode("utf-8") if length else ""
                fields = parse_qs(body)
                if self.path == "/api/shutdown":
                    state.shutdown_requested = True
                    state.shutdown_message = shutdown.request()
                    state.touch()
                    self._send_json({"ok": True, "message": state.shutdown_message})
                    return
                if self.path in {"/api/power", "/power"}:
                    action = fields.get("action", [""])[0]
                    if action not in {"shutdown", "reboot"}:
                        self._send_json({"ok": False, "message": "invalid power action"}, HTTPStatus.BAD_REQUEST)
                        return
                    state.shutdown_requested = action == "shutdown"
                    state.shutdown_message = shutdown.request_power(action)
                    state.touch()
                    if self.path == "/power":
                        self._send_text(render_dashboard(state), HTTPStatus.OK, "text/html; charset=utf-8")
                        return
                    self._send_json({"ok": True, "message": state.shutdown_message})
                    return
                if self.path in {"/api/brightness", "/brightness"}:
                    try:
                        brightness = int(fields.get("brightness", [""])[0])
                    except ValueError:
                        self._send_json({"ok": False, "message": "invalid brightness"}, HTTPStatus.BAD_REQUEST)
                        return
                    state.brightness = max(0, min(100, brightness))
                    state.status_message = f"Brightness: {state.brightness}%"
                    state.active_screen = "brightness"
                    state.touch()
                    if self.path == "/brightness":
                        self._send_text(render_dashboard(state), HTTPStatus.OK, "text/html; charset=utf-8")
                        return
                    self._send_json({"ok": True, "brightness": state.brightness})
                    return
                if self.path in {"/api/button", "/button"}:
                    source = fields.get("source", [""])[0]
                    gesture = fields.get("gesture", [""])[0]
                    if source in {"whisplay", "pisugar"} and gesture in {"short", "double", "long", "very_long"}:
                        controller.handle_button(ButtonEvent(source, gesture), state)
                        if self.path == "/button":
                            self._send_text(render_dashboard(state), HTTPStatus.OK, "text/html; charset=utf-8")
                            return
                        self._send_json({"ok": True, "state": state.to_dict()})
                        return
                    self._send_json({"ok": False, "message": "invalid button event"}, HTTPStatus.BAD_REQUEST)
                    return
                if self.path == "/shutdown":
                    state.shutdown_requested = True
                    state.shutdown_message = shutdown.request()
                    state.touch()
                    self._send_text(render_dashboard(state), HTTPStatus.OK, "text/html; charset=utf-8")
                    return
                self._send_json({"ok": False, "fields": fields}, HTTPStatus.NOT_FOUND)

            def log_message(self, format: str, *args: object) -> None:
                return

            def _send_json(self, data: object, status: HTTPStatus = HTTPStatus.OK) -> None:
                payload = json.dumps(data, indent=2).encode("utf-8")
                self.send_response(status)
                self.send_header("content-type", "application/json")
                self.send_header("content-length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def _send_text(
                self,
                text: str,
                status: HTTPStatus = HTTPStatus.OK,
                content_type: str = "text/plain; charset=utf-8",
            ) -> None:
                payload = text.encode("utf-8")
                self.send_response(status)
                self.send_header("content-type", content_type)
                self.send_header("content-length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def _send_session_file(self) -> None:
                path = _session_file_path(config.session_dir, self.path)
                if path is None or not path.exists():
                    self._send_text("not found\n", HTTPStatus.NOT_FOUND)
                    return
                payload = path.read_bytes()
                content_type = "audio/wav" if path.name == "audio.wav" else "application/json"
                self.send_response(HTTPStatus.OK)
                self.send_header("content-type", content_type)
                self.send_header("content-length", str(len(payload)))
                self.send_header("content-disposition", f"attachment; filename={path.name}")
                self.end_headers()
                self.wfile.write(payload)

        return Handler


def render_dashboard(state: AppState) -> str:
    hardware = state.hardware
    battery = (
        f"{hardware.battery_percentage}%"
        if hardware.battery_percentage is not None
        else "Not readable"
    )
    diagnostics = "\n".join(
        f"<li><strong>{item.name}</strong>: {'OK' if item.ok else 'Missing'}"
        f"<span class=\"detail\">{item.detail}</span></li>"
        for item in hardware.diagnostics
    )
    stats = state.system
    uptime = _uptime_text(stats.uptime_seconds)
    memory = _memory_text(stats.memory_available_mb, stats.memory_total_mb)
    load = " ".join(
        [
            _load_text(stats.load_1m),
            _load_text(stats.load_5m),
            _load_text(stats.load_15m),
        ]
    )
    current_session = state.current_session
    if current_session is None:
        session_detail = "<p>No active recording.</p>"
    else:
        session_detail = (
            f"<p><strong>{current_session.id}</strong> started at {current_session.started_at}.</p>"
            f"<p>Bookmarks: {len(current_session.bookmarks)}</p>"
        )
    recent_sessions = "\n".join(
        f"<li><strong>{session.id}</strong>"
        f"<span class=\"detail\">{session.status} | audio {session.audio_status}"
        f" | {_duration_text(session.audio_duration_seconds)}"
        f" | {_size_text(session.audio_size_bytes)}"
        f" | rms {_value_text(session.audio_rms)}</span>"
        f"<a href=\"/sessions/{session.id}/audio.wav\">audio.wav</a> | "
        f"<a href=\"/sessions/{session.id}/metadata.json\">metadata.json</a></li>"
        for session in state.recent_sessions
    )
    if not recent_sessions:
        recent_sessions = "<li>No saved sessions yet.</li>"
    brightness_buttons = "\n".join(
        f"<form method=\"post\" action=\"/brightness\"><input type=\"hidden\" name=\"brightness\" value=\"{level}\"><button type=\"submit\">{level}%</button></form>"
        for level in state.brightness_levels
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AxiomVox</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 2rem; color: #17202a; background: #f7f8fa; }}
    main {{ max-width: 880px; margin: 0 auto; }}
    section, nav {{ margin-top: 1.25rem; }}
    .panel {{ background: white; border: 1px solid #d8dee8; border-radius: 8px; padding: 1rem; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: .75rem; }}
    .metric {{ background: #eef4f8; border-radius: 6px; padding: .75rem; }}
    .label {{ color: #536471; font-size: .85rem; }}
    .value {{ font-size: 1.4rem; font-weight: 700; }}
    .actions {{ display: flex; flex-wrap: wrap; gap: .5rem; }}
    li {{ margin: .5rem 0; }}
    .detail {{ display: block; color: #536471; font-size: .9rem; }}
    .detail::before {{ content: "Detail: "; font-weight: 700; }}
    button {{ border: 0; border-radius: 6px; background: #155c85; color: white; padding: .7rem 1rem; font-weight: 700; }}
    .danger {{ background: #a83232; }}
    a {{ color: #155c85; }}
  </style>
</head>
<body>
<main>
  <h1>AxiomVox</h1>
  <p>Device status shell. Local sessions are available; transcription is not implemented yet.</p>
  <section class="panel grid">
    <div class="metric"><div class="label">Mode</div><div class="value">{state.mode}</div></div>
    <div class="metric"><div class="label">Screen</div><div class="value">{state.active_screen}</div></div>
    <div class="metric"><div class="label">Battery</div><div class="value">{battery}</div></div>
    <div class="metric"><div class="label">Web</div><div class="value">{'OK' if state.web_reachable else 'Starting'}</div></div>
    <div class="metric"><div class="label">Uptime</div><div class="value">{uptime}</div></div>
    <div class="metric"><div class="label">Memory</div><div class="value">{memory}</div></div>
    <div class="metric"><div class="label">Load</div><div class="value">{load}</div></div>
    <div class="metric"><div class="label">Brightness</div><div class="value">{state.brightness}%</div></div>
  </section>
  <section class="panel">
    <h2>Controls</h2>
    <p>{state.status_message}</p>
    <p>Last button: {state.last_button_event or 'none'}</p>
    <div class="actions">
      <form method="post" action="/button"><input type="hidden" name="source" value="whisplay"><input type="hidden" name="gesture" value="short"><button type="submit">Whisplay Short</button></form>
      <form method="post" action="/button"><input type="hidden" name="source" value="whisplay"><input type="hidden" name="gesture" value="long"><button type="submit">Whisplay Long</button></form>
      <form method="post" action="/button"><input type="hidden" name="source" value="pisugar"><input type="hidden" name="gesture" value="short"><button type="submit">PiSugar Short</button></form>
      <form method="post" action="/button"><input type="hidden" name="source" value="pisugar"><input type="hidden" name="gesture" value="long"><button type="submit">PiSugar Long</button></form>
    </div>
  </section>
  <section class="panel">
    <h2>Sessions</h2>
    {session_detail}
    <ul>{recent_sessions}</ul>
  </section>
  <section class="panel">
    <h2>Settings</h2>
    <h3>Brightness</h3>
    <div class="actions">{brightness_buttons}</div>
  </section>
  <section class="panel">
    <h2>M0 Diagnostics</h2>
    <ul>{diagnostics}</ul>
  </section>
  <section class="panel">
    <h2>Future Sections</h2>
    <nav>Sessions · Device · Transcription · Settings · Advanced · Development</nav>
  </section>
  <section class="panel">
    <h2>Power</h2>
    <p>{state.shutdown_message}</p>
    <div class="actions">
      <form method="post" action="/power"><input type="hidden" name="action" value="reboot"><button class="danger" type="submit">Reboot</button></form>
      <form method="post" action="/power"><input type="hidden" name="action" value="shutdown"><button class="danger" type="submit">Shutdown</button></form>
    </div>
  </section>
</main>
</body>
</html>
"""


def _session_file_path(session_dir: Path, request_path: str) -> Path | None:
    parts = [unquote(part) for part in request_path.split("/") if part]
    if len(parts) != 3 or parts[0] != "sessions" or parts[2] not in {"audio.wav", "metadata.json"}:
        return None
    candidate = (session_dir / parts[1] / parts[2]).resolve()
    root = session_dir.resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate


def _duration_text(duration: float | None) -> str:
    if duration is None:
        return "--s"
    return f"{duration:.1f}s"


def _size_text(size_bytes: int | None) -> str:
    if size_bytes is None:
        return "--"
    if size_bytes < 1024:
        return f"{size_bytes} B"
    return f"{size_bytes / 1024:.0f} KB"


def _value_text(value: int | None) -> str:
    if value is None:
        return "--"
    return str(value)


def _uptime_text(seconds: int | None) -> str:
    if seconds is None:
        return "--"
    minutes = seconds // 60
    hours = minutes // 60
    days = hours // 24
    if days:
        return f"{days}d {hours % 24}h"
    if hours:
        return f"{hours}h {minutes % 60}m"
    return f"{minutes}m"


def _memory_text(available_mb: int | None, total_mb: int | None) -> str:
    if available_mb is None or total_mb is None:
        return "--"
    used_mb = max(0, total_mb - available_mb)
    return f"{used_mb}/{total_mb} MB"


def _load_text(load: float | None) -> str:
    if load is None:
        return "--"
    return f"{load:.2f}"
