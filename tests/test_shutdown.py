import subprocess

from device.axiomvox_device.config import DeviceConfig
from device.axiomvox_device.shutdown import ShutdownController


def test_power_request_is_dry_run_by_default() -> None:
    message = ShutdownController(DeviceConfig()).request_power("reboot")

    assert message == "Reboot requested. Dry-run mode is active."


def test_power_request_reports_command_failure(monkeypatch) -> None:
    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(args[0], 1, stdout="", stderr="permission denied")

    monkeypatch.setattr("device.axiomvox_device.shutdown.subprocess.run", fake_run)
    message = ShutdownController(DeviceConfig(allow_shutdown=True)).request_power("shutdown")

    assert message == "Shutdown request failed: permission denied"
