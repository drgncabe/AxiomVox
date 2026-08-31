from __future__ import annotations

import json
from html import escape
from dataclasses import asdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from typing import TYPE_CHECKING
from urllib.parse import parse_qs, unquote, urlparse

from shared.axiomvox_shared import AppState, ServiceStatus

from .config import DeviceConfig
from .controls import ApplianceController
from .events import ButtonEvent
from .hardware import HardwareProbe
from .logs import DEFAULT_LOG_LINES, LogReader, clamp_log_lines
from .shutdown import ShutdownController
from .sound import SoundFeedback, clamp_volume

if TYPE_CHECKING:
    from .lcd import WhisplayLcdDriver


class StatusServer:
    def __init__(
        self,
        state: AppState,
        config: DeviceConfig,
        controller: ApplianceController | None = None,
        lcd: WhisplayLcdDriver | None = None,
        sound: SoundFeedback | None = None,
    ) -> None:
        self.state = state
        self.config = config
        self.shutdown = ShutdownController(config)
        self.controller = controller or ApplianceController()
        self.lcd = lcd
        self.sound = sound or SoundFeedback(config)
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
        lcd = self.lcd
        sound = self.sound
        log_reader = LogReader(config)
        hardware_probe = HardwareProbe(simulate=config.simulate_hardware)

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                parsed = urlparse(self.path)
                path = parsed.path
                query = parse_qs(parsed.query)
                if path == "/healthz":
                    self._send_text("ok\n", HTTPStatus.OK)
                    return
                if path == "/api/status":
                    self._send_json(state.to_dict())
                    return
                if path == "/api/diagnostics":
                    self._send_json({"diagnostics": state.to_dict()["hardware"]["diagnostics"]})
                    return
                if path == "/api/sessions":
                    self._send_json(
                        {
                            "current_session": state.to_dict()["current_session"],
                            "recent_sessions": state.to_dict()["recent_sessions"],
                        }
                    )
                    return
                if path == "/api/logs":
                    self._send_json(
                        log_reader.read(
                            kind=query.get("kind", ["axiomvox"])[0],
                            lines=_int_query(query, "lines", DEFAULT_LOG_LINES),
                            query=query.get("q", [""])[0],
                        ).to_dict()
                    )
                    return
                if path == "/api/pisugar":
                    self._send_json({"diagnostics": [asdict(item) for item in hardware_probe.pisugar_diagnostics()]})
                    return
                if path.startswith("/sessions/"):
                    self._send_session_file()
                    return
                if path == "/settings/display":
                    self._send_text(render_display_settings(state), HTTPStatus.OK, "text/html; charset=utf-8")
                    return
                if path == "/settings/power":
                    self._send_text(render_power_settings(state), HTTPStatus.OK, "text/html; charset=utf-8")
                    return
                if path == "/settings/sound":
                    self._send_text(render_sound_settings(state), HTTPStatus.OK, "text/html; charset=utf-8")
                    return
                if path == "/settings/logs":
                    self._send_text(render_log_settings(), HTTPStatus.OK, "text/html; charset=utf-8")
                    return
                if path == "/settings/pisugar":
                    self._send_text(
                        render_pisugar_settings(hardware_probe.pisugar_diagnostics()),
                        HTTPStatus.OK,
                        "text/html; charset=utf-8",
                    )
                    return
                if path == "/":
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
                    state.mark_user_action()
                    if self.path == "/power":
                        self._send_text(render_power_settings(state), HTTPStatus.OK, "text/html; charset=utf-8")
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
                    state.active_screen = "display_settings"
                    state.mark_user_action()
                    if lcd is not None:
                        state.status_message = lcd.set_brightness(state.brightness)
                    if self.path == "/brightness":
                        self._send_text(render_display_settings(state), HTTPStatus.OK, "text/html; charset=utf-8")
                        return
                    self._send_json({"ok": True, "brightness": state.brightness})
                    return
                if self.path in {"/api/display-sleep", "/display-sleep"}:
                    try:
                        timeout = int(fields.get("timeout", [""])[0])
                    except ValueError:
                        self._send_json({"ok": False, "message": "invalid timeout"}, HTTPStatus.BAD_REQUEST)
                        return
                    state.display_sleep_timeout_seconds = max(0, timeout)
                    state.status_message = _sleep_timeout_message(state.display_sleep_timeout_seconds)
                    state.mark_user_action()
                    if self.path == "/display-sleep":
                        self._send_text(render_display_settings(state), HTTPStatus.OK, "text/html; charset=utf-8")
                        return
                    self._send_json({"ok": True, "timeout": state.display_sleep_timeout_seconds})
                    return
                if self.path in {"/api/sound", "/sound"}:
                    try:
                        volume = int(fields.get("volume", [str(state.chime_volume)])[0])
                    except ValueError:
                        self._send_json({"ok": False, "message": "invalid volume"}, HTTPStatus.BAD_REQUEST)
                        return
                    state.chime_volume = clamp_volume(volume)
                    state.chimes_enabled = fields.get("chimes", ["off"])[0] == "on"
                    state.status_message = sound.apply_state(state)
                    if fields.get("test", [""])[0] == "1":
                        state.status_message = sound.play("test", state)
                    state.mark_user_action()
                    if self.path == "/sound":
                        self._send_text(render_sound_settings(state), HTTPStatus.OK, "text/html; charset=utf-8")
                        return
                    self._send_json(
                        {
                            "ok": True,
                            "volume": state.chime_volume,
                            "chimes_enabled": state.chimes_enabled,
                            "message": state.status_message,
                        }
                    )
                    return
                if self.path in {"/api/button", "/button"}:
                    source = fields.get("source", [""])[0]
                    gesture = fields.get("gesture", [""])[0]
                    if source in {"whisplay", "pisugar"} and gesture in {"short", "double", "long", "very_long"}:
                        controller.handle_button(ButtonEvent(source, gesture), state)
                        state.mark_user_action()
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
                    state.mark_user_action()
                    self._send_text(render_power_settings(state), HTTPStatus.OK, "text/html; charset=utf-8")
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
    cpu = _percent_text(stats.cpu_used_percent)
    memory = _memory_text(stats.memory_available_mb, stats.memory_total_mb)
    memory_percent = _percent_text(stats.memory_used_percent)
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
    .charts {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 1rem; }}
    canvas {{ width: 100%; height: 120px; border: 1px solid #d8dee8; border-radius: 6px; background: #f8fafc; }}
    .label {{ color: #536471; font-size: .85rem; }}
    .value {{ font-size: 1.4rem; font-weight: 700; }}
    .actions {{ display: flex; flex-wrap: wrap; gap: .5rem; }}
    li {{ margin: .5rem 0; }}
    .detail {{ display: block; color: #536471; font-size: .9rem; }}
    .detail::before {{ content: "Detail: "; font-weight: 700; }}
    button {{ border: 0; border-radius: 6px; background: #155c85; color: white; padding: .7rem 1rem; font-weight: 700; }}
    .danger {{ background: #a83232; }}
    a {{ color: #155c85; }}
    .navlinks {{ display: flex; flex-wrap: wrap; gap: 1rem; }}
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
    <div class="metric"><div class="label">CPU</div><div class="value">{cpu}</div></div>
    <div class="metric"><div class="label">Memory</div><div class="value">{memory}</div></div>
    <div class="metric"><div class="label">RAM</div><div class="value">{memory_percent}</div></div>
    <div class="metric"><div class="label">Load</div><div class="value">{load}</div></div>
    <div class="metric"><div class="label">Brightness</div><div class="value">{state.brightness}%</div></div>
  </section>
  <section class="panel">
    <h2>System Graphs</h2>
    <div class="charts">
      <div>
        <div class="label">CPU usage</div>
        <canvas id="cpuChart" width="380" height="120"></canvas>
      </div>
      <div>
        <div class="label">RAM usage</div>
        <canvas id="ramChart" width="380" height="120"></canvas>
      </div>
    </div>
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
    <nav class="navlinks">
      <a href="/settings/display">Display settings</a>
      <a href="/settings/power">Power settings</a>
      <a href="/settings/sound">Sound settings</a>
      <a href="/settings/logs">Logs</a>
      <a href="/settings/pisugar">PiSugar diagnostics</a>
    </nav>
  </section>
  <section class="panel">
    <h2>M0 Diagnostics</h2>
    <ul>{diagnostics}</ul>
  </section>
  <section class="panel">
    <h2>Future Sections</h2>
    <nav>Sessions · Device · Transcription · Settings · Advanced · Development</nav>
  </section>
</main>
<script>
  const cpuChart = document.getElementById('cpuChart');
  const ramChart = document.getElementById('ramChart');

  function drawChart(canvas, values, color) {{
    const context = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;
    context.clearRect(0, 0, width, height);
    context.fillStyle = '#f8fafc';
    context.fillRect(0, 0, width, height);
    context.strokeStyle = '#d8dee8';
    context.lineWidth = 1;
    for (let idx = 0; idx <= 4; idx += 1) {{
      const y = Math.round((height - 1) * idx / 4);
      context.beginPath();
      context.moveTo(0, y);
      context.lineTo(width, y);
      context.stroke();
    }}
    const points = values.filter((value) => Number.isFinite(value));
    if (points.length === 0) {{
      context.fillStyle = '#536471';
      context.fillText('Collecting...', 12, 24);
      return;
    }}
    context.strokeStyle = color;
    context.lineWidth = 2;
    context.beginPath();
    points.forEach((value, idx) => {{
      const x = points.length === 1 ? width - 1 : idx * (width - 1) / (points.length - 1);
      const y = height - 1 - Math.max(0, Math.min(100, value)) * (height - 1) / 100;
      if (idx === 0) {{
        context.moveTo(x, y);
      }} else {{
        context.lineTo(x, y);
      }}
    }});
    context.stroke();
  }}

  async function refreshCharts() {{
    try {{
      const response = await fetch('/api/status', {{ cache: 'no-store' }});
      const appState = await response.json();
      const history = appState.system_history || [];
      drawChart(cpuChart, history.map((sample) => sample.cpu_used_percent), '#155c85');
      drawChart(ramChart, history.map((sample) => sample.memory_used_percent), '#2e7d32');
    }} catch (error) {{
      drawChart(cpuChart, [], '#155c85');
      drawChart(ramChart, [], '#2e7d32');
    }}
  }}

  refreshCharts();
  setInterval(refreshCharts, 5000);
</script>
</body>
</html>
"""


def render_display_settings(state: AppState) -> str:
    brightness_buttons = "\n".join(
        f"<form method=\"post\" action=\"/brightness\"><input type=\"hidden\" name=\"brightness\" value=\"{level}\"><button type=\"submit\">{level}%</button></form>"
        for level in state.brightness_levels
    )
    timeout_buttons = "\n".join(
        f"<form method=\"post\" action=\"/display-sleep\"><input type=\"hidden\" name=\"timeout\" value=\"{seconds}\"><button type=\"submit\">{label}</button></form>"
        for label, seconds in [
            ("Off", 0),
            ("30s", 30),
            ("1m", 60),
            ("5m", 300),
            ("10m", 600),
        ]
    )
    return _settings_page(
        "Display Settings",
        f"""
  <section class="panel">
    <h2>Brightness</h2>
    <p>Current: {state.brightness}%</p>
    <div class="actions">{brightness_buttons}</div>
  </section>
  <section class="panel">
    <h2>Screen Sleep</h2>
    <p>Current: {_sleep_timeout_text(state.display_sleep_timeout_seconds)}</p>
    <p>Screen is {'awake' if state.display_awake else 'sleeping'}.</p>
    <div class="actions">{timeout_buttons}</div>
  </section>
""",
    )


def render_power_settings(state: AppState) -> str:
    return _settings_page(
        "Power Settings",
        f"""
  <section class="panel">
    <h2>Power</h2>
    <p>{state.shutdown_message}</p>
    <div class="actions">
      <form method="post" action="/power"><input type="hidden" name="action" value="reboot"><button class="danger" type="submit">Reboot</button></form>
      <form method="post" action="/power"><input type="hidden" name="action" value="shutdown"><button class="danger" type="submit">Shutdown</button></form>
    </div>
  </section>
""",
    )


def render_sound_settings(state: AppState) -> str:
    volume_buttons = "\n".join(
        f"<form method=\"post\" action=\"/sound\"><input type=\"hidden\" name=\"volume\" value=\"{level}\">"
        f"{_chime_hidden(state)}<button type=\"submit\">{level}%</button></form>"
        for level in state.volume_levels
    )
    chime_checked = " checked" if state.chimes_enabled else ""
    return _settings_page(
        "Sound Settings",
        f"""
  <section class="panel">
    <h2>Chimes</h2>
    <p>Current volume: {state.chime_volume}%</p>
    <p>{state.status_message}</p>
    <form method="post" action="/sound">
      <input type="hidden" name="volume" value="{state.chime_volume}">
      <label class="watch"><input type="checkbox" name="chimes" value="on"{chime_checked}> Chimes enabled</label>
      <button type="submit">Save</button>
    </form>
    <div class="actions">{volume_buttons}</div>
    <form method="post" action="/sound">
      <input type="hidden" name="volume" value="{state.chime_volume}">
      {_chime_hidden(state)}
      <input type="hidden" name="test" value="1">
      <button type="submit">Play test chime</button>
    </form>
  </section>
""",
    )


def render_log_settings() -> str:
    return _settings_page(
        "Logs",
        f"""
  <section class="panel">
    <form id="logControls" class="log-controls">
      <label>Log
        <select id="kind" name="kind">
          <option value="axiomvox">AxiomVox service</option>
          <option value="system">System</option>
        </select>
      </label>
      <label>Search
        <input id="query" name="q" type="search" placeholder="filter text">
      </label>
      <label>Lines
        <input id="lines" name="lines" type="number" min="20" max="1000" value="{DEFAULT_LOG_LINES}">
      </label>
      <label class="watch"><input id="watch" type="checkbox" checked> Watch</label>
      <button type="submit">Search</button>
    </form>
    <p id="logStatus">Loading logs...</p>
    <pre id="logOutput" class="logs" aria-live="polite"></pre>
  </section>
  <script>
    const form = document.getElementById('logControls');
    const statusEl = document.getElementById('logStatus');
    const outputEl = document.getElementById('logOutput');
    const kindEl = document.getElementById('kind');
    const queryEl = document.getElementById('query');
    const linesEl = document.getElementById('lines');
    const watchEl = document.getElementById('watch');

    async function loadLogs() {{
      const params = new URLSearchParams({{
        kind: kindEl.value,
        q: queryEl.value,
        lines: linesEl.value
      }});
      try {{
        const response = await fetch('/api/logs?' + params.toString(), {{ cache: 'no-store' }});
        const data = await response.json();
        outputEl.textContent = data.text || '';
        statusEl.textContent = data.ok
          ? `${{data.kind}} logs: ${{data.line_count}} matching lines`
          : `${{data.kind}} logs unavailable: ${{data.message}}`;
        if (watchEl.checked) {{
          outputEl.scrollTop = outputEl.scrollHeight;
        }}
      }} catch (error) {{
        statusEl.textContent = 'Log refresh failed: ' + error;
      }}
    }}

    form.addEventListener('submit', (event) => {{
      event.preventDefault();
      loadLogs();
    }});
    kindEl.addEventListener('change', loadLogs);
    watchEl.addEventListener('change', loadLogs);
    setInterval(() => {{
      if (watchEl.checked) {{
        loadLogs();
      }}
    }}, 2000);
    loadLogs();
  </script>
""",
    )


def render_pisugar_settings(diagnostics: list[ServiceStatus]) -> str:
    rows = "\n".join(
        f"<li><strong>{escape(item.name)}</strong>: {'OK' if item.ok else 'Check'}"
        f"<span class=\"detail\">{escape(item.detail)}</span></li>"
        for item in diagnostics
    )
    if not rows:
        rows = "<li>No PiSugar diagnostics available.</li>"
    return _settings_page(
        "PiSugar Diagnostics",
        f"""
  <section class="panel">
    <ul>{rows}</ul>
    <p>Use Logs with search text <strong>pisugar</strong> for the running service output.</p>
    <nav><a href="/settings/logs">Open logs</a></nav>
  </section>
""",
    )


def _settings_page(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AxiomVox - {title}</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 2rem; color: #17202a; background: #f7f8fa; }}
    main {{ max-width: 880px; margin: 0 auto; }}
    section, nav {{ margin-top: 1.25rem; }}
    .panel {{ background: white; border: 1px solid #d8dee8; border-radius: 8px; padding: 1rem; }}
    .actions {{ display: flex; flex-wrap: wrap; gap: .5rem; }}
    .log-controls {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: .75rem; align-items: end; }}
    label {{ display: grid; gap: .25rem; color: #536471; font-size: .9rem; font-weight: 700; }}
    input, select {{ border: 1px solid #aeb8c6; border-radius: 6px; padding: .65rem; font: inherit; }}
    .watch {{ display: flex; gap: .5rem; align-items: center; }}
    .logs {{ min-height: 24rem; max-height: 65vh; overflow: auto; white-space: pre-wrap; background: #111827; color: #f9fafb; border-radius: 6px; padding: 1rem; font-size: .85rem; line-height: 1.4; }}
    button {{ border: 0; border-radius: 6px; background: #155c85; color: white; padding: .7rem 1rem; font-weight: 700; }}
    .danger {{ background: #a83232; }}
    a {{ color: #155c85; }}
  </style>
</head>
<body>
<main>
  <h1>{title}</h1>
  <nav><a href="/">Dashboard</a></nav>
{body}
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


def _chime_hidden(state: AppState) -> str:
    if not state.chimes_enabled:
        return ""
    return "<input type=\"hidden\" name=\"chimes\" value=\"on\">"


def _int_query(query: dict[str, list[str]], name: str, default: int) -> int:
    try:
        return clamp_log_lines(int(query.get(name, [str(default)])[0]))
    except ValueError:
        return default


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


def _percent_text(value: float | None) -> str:
    if value is None:
        return "--"
    return f"{value:.1f}%"


def _uptime_text(seconds: int | None) -> str:
    if seconds is None:
        return "--"
    if seconds < 60:
        return f"{seconds}s"
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


def _sleep_timeout_text(seconds: int) -> str:
    if seconds <= 0:
        return "Off"
    return _uptime_text(seconds)


def _sleep_timeout_message(seconds: int) -> str:
    return f"Screen sleep: {_sleep_timeout_text(seconds)}"
