from device.axiomvox_device.main import _lcd_render_ok, _lcd_resource_busy


def test_lcd_render_ok_matches_success_text() -> None:
    assert _lcd_render_ok("Whisplay LCD updated via draw_image") is True
    assert _lcd_render_ok("Whisplay runtime load failed") is False


def test_lcd_resource_busy_detects_errno_16() -> None:
    assert _lcd_resource_busy("Whisplay runtime load failed: [Errno 16] Device or resource busy")
    assert _lcd_resource_busy("Whisplay runtime load failed: missing spidev") is False
