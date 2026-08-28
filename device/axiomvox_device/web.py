from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from urllib.parse import parse_qs

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
    current_session = state.current_session
    if current_session is None:
        session_detail = "<p>No active recording.</p>"
    else:
        session_detail = (
            f"<p><strong>{current_session.id}</strong> started at {current_session.started_at}.</p>"
            f"<p>Bookmarks: {len(current_session.bookmarks)}</p>"
        )
    recent_sessions = "\n".join(
        f"<li><strong>{session.id}</strong><span class=\"detail\">{session.status}</span></li>"
        for session in state.recent_sessions
    )
    if not recent_sessions:
        recent_sessions = "<li>No saved sessions yet.</li>"
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
  <p>Device status shell. Recording and transcription are not implemented in M0.</p>
  <section class="panel grid">
    <div class="metric"><div class="label">Mode</div><div class="value">{state.mode}</div></div>
    <div class="metric"><div class="label">Screen</div><div class="value">{state.active_screen}</div></div>
    <div class="metric"><div class="label">Battery</div><div class="value">{battery}</div></div>
    <div class="metric"><div class="label">Web</div><div class="value">{'OK' if state.web_reachable else 'Starting'}</div></div>
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
    <form method="post" action="/shutdown"><button class="danger" type="submit">Shutdown</button></form>
  </section>
</main>
</body>
</html>
"""
