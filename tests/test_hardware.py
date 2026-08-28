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
