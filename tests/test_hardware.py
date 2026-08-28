from device.axiomvox_device.hardware import HardwareProbe


def test_pisugar_battery_parses_key_value_response() -> None:
    probe = HardwareProbe()
    probe._query_pisugar = lambda command: "battery: 74.6" if command == "get battery" else None

    assert probe._read_battery_percentage() == 75


def test_pisugar_button_uses_button_api() -> None:
    probe = HardwareProbe()

    def fake_query(command: str) -> str | None:
        if command == "get button_enable single":
            return "button_enable: single true"
        return None

    probe._query_pisugar = fake_query

    result = probe._probe_pisugar_button()

    assert result.ok is True
    assert "single=true" in result.detail


def test_pisugar_query_falls_back_to_tcp() -> None:
    probe = HardwareProbe()
    probe._query_unix_socket = lambda socket_path, command: None
    probe._query_tcp_socket = lambda host, port, command: "battery: 83"

    assert probe._query_pisugar("get battery") == "battery: 83"


def test_pisugar_probe_reports_active_service_without_api() -> None:
    probe = HardwareProbe()
    probe._query_pisugar = lambda command: None
    probe._systemctl_is_active = lambda service: type("Result", (), {
        "ok": True,
        "detail": "pisugar-server status: active",
    })()

    result = probe._probe_pisugar()

    assert result.ok is True
    assert "API did not respond" in result.detail
