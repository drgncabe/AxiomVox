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


def test_pisugar_battery_falls_back_to_i2c_register() -> None:
    probe = HardwareProbe()
    probe._query_pisugar = lambda command: None
    probe._read_i2c_byte = lambda address, register: 62 if (address, register) == (0x57, 0x2A) else None

    assert probe._read_battery_percentage() == 62


def test_pisugar_button_detects_readable_i2c_register() -> None:
    probe = HardwareProbe()
    probe._query_pisugar = lambda command: None
    probe._probe_input = lambda keyword: type("Result", (), {"ok": False, "detail": "missing"})()
    probe._systemctl_is_active = lambda service: type("Result", (), {
        "ok": False,
        "detail": "pisugar-server status: failed",
    })()
    probe._read_i2c_byte = lambda address, register: 0 if (address, register) == (0x57, 0x08) else None

    result = probe._probe_pisugar_button()

    assert result.ok is True
    assert "custom_register:0x00" in result.detail


def test_pisugar_diagnostics_collects_service_api_and_i2c_details() -> None:
    probe = HardwareProbe()

    def fake_query(command: str) -> str | None:
        responses = {
            "get model": "model: PiSugar 3",
            "get battery": "battery: 74.6",
            "get button": "button: short",
            "get button_enable single": "button_enable: single true",
        }
        return responses.get(command)

    probe._query_pisugar = fake_query
    probe._systemctl_is_active = lambda service: type("Result", (), {
        "ok": True,
        "detail": "pisugar-server status: active",
    })()
    probe._read_i2c_byte = lambda address, register: 74 if (address, register) == (0x57, 0x2A) else None

    diagnostics = probe.pisugar_diagnostics()

    assert [item.name for item in diagnostics] == [
        "pisugar_service",
        "pisugar_api",
        "pisugar_model",
        "pisugar_battery",
        "pisugar_button",
        "pisugar_i2c",
    ]
    assert diagnostics[0].ok is True
    assert diagnostics[2].detail == "PiSugar 3"
    assert "single" in diagnostics[4].detail
