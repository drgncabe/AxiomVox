import subprocess

from device.axiomvox_device.config import DeviceConfig
from device.axiomvox_device.logs import LogReader, clamp_log_lines, filter_log_text, normalize_log_kind


def test_log_kind_is_limited_to_known_values() -> None:
    assert normalize_log_kind("axiomvox") == "axiomvox"
    assert normalize_log_kind("system") == "system"
    assert normalize_log_kind("shell") == "axiomvox"


def test_log_lines_are_bounded() -> None:
    assert clamp_log_lines(1) == 20
    assert clamp_log_lines(200) == 200
    assert clamp_log_lines(5000) == 1000


def test_filter_log_text_is_case_insensitive() -> None:
    text = "first line\nButton pressed\nPower requested"

    assert filter_log_text(text, "button") == "Button pressed"


def test_log_reader_uses_service_limited_journal_command() -> None:
    commands: list[list[str]] = []

    def fake_runner(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="line one\nline two\n", stderr="")

    reader = LogReader(DeviceConfig(service_name="axiomvox.service"), runner=fake_runner, command_finder=lambda _: "/bin/journalctl")

    result = reader.read(kind="axiomvox", lines=50)

    assert result.ok
    assert result.line_count == 2
    assert commands == [["journalctl", "-u", "axiomvox.service", "-n", "50", "--no-pager", "-o", "short-iso"]]


def test_log_reader_handles_missing_journalctl() -> None:
    reader = LogReader(DeviceConfig(), command_finder=lambda _: None)

    result = reader.read()

    assert not result.ok
    assert "journalctl" in result.message
