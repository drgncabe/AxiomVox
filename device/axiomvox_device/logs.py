from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from typing import Callable

from .config import DeviceConfig

MAX_LOG_LINES = 1000
DEFAULT_LOG_LINES = 200


Runner = Callable[..., subprocess.CompletedProcess[str]]
CommandFinder = Callable[[str], str | None]


@dataclass(frozen=True, slots=True)
class LogResult:
    ok: bool
    kind: str
    query: str
    lines: int
    text: str
    message: str = ""

    @property
    def line_count(self) -> int:
        if not self.text:
            return 0
        return len(self.text.splitlines())

    def to_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "kind": self.kind,
            "query": self.query,
            "lines": self.lines,
            "line_count": self.line_count,
            "text": self.text,
            "message": self.message,
        }


class LogReader:
    def __init__(
        self,
        config: DeviceConfig,
        runner: Runner = subprocess.run,
        command_finder: CommandFinder = shutil.which,
    ) -> None:
        self.config = config
        self.runner = runner
        self.command_finder = command_finder

    def read(self, kind: str = "axiomvox", lines: int = DEFAULT_LOG_LINES, query: str = "") -> LogResult:
        log_kind = normalize_log_kind(kind)
        line_count = clamp_log_lines(lines)
        clean_query = query.strip()

        if self.command_finder("journalctl") is None:
            return LogResult(False, log_kind, clean_query, line_count, "", "journalctl is not installed")

        command = self._command(log_kind, line_count)
        try:
            completed = self.runner(
                command,
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return LogResult(False, log_kind, clean_query, line_count, "", "journalctl timed out")
        except OSError as exc:
            return LogResult(False, log_kind, clean_query, line_count, "", str(exc))

        output = completed.stdout.strip()
        error = completed.stderr.strip()
        if clean_query:
            output = filter_log_text(output, clean_query)

        ok = completed.returncode == 0
        message = error if error else ("ok" if ok else f"journalctl exited {completed.returncode}")
        return LogResult(ok, log_kind, clean_query, line_count, output, message)

    def _command(self, kind: str, lines: int) -> list[str]:
        command = ["journalctl", "-n", str(lines), "--no-pager", "-o", "short-iso"]
        if kind == "axiomvox":
            command[1:1] = ["-u", self.config.service_name]
        return command


def normalize_log_kind(kind: str) -> str:
    return kind if kind in {"axiomvox", "system"} else "axiomvox"


def clamp_log_lines(lines: int) -> int:
    return max(20, min(MAX_LOG_LINES, lines))


def filter_log_text(text: str, query: str) -> str:
    needle = query.casefold()
    return "\n".join(line for line in text.splitlines() if needle in line.casefold())
