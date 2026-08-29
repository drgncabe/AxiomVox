from pathlib import Path

from shared.axiomvox_shared import AppState
from device.axiomvox_device.main import _write_status_file


def test_status_file_write_failure_is_non_fatal(capsys) -> None:
    _write_status_file(Path("\0/status.json"), AppState())

    captured = capsys.readouterr()

    assert "Status file unavailable" in captured.err
