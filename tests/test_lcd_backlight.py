from device.axiomvox_device.lcd import WhisplayLcdDriver


class FakeBoard:
    def __init__(self) -> None:
        self.backlight: int | None = None
        self.drawn = False

    def set_backlight(self, brightness: int) -> None:
        self.backlight = brightness

    def draw_image(self, x: int, y: int, width: int, height: int, image: bytes) -> None:
        self.drawn = True


def test_lcd_render_enables_backlight_once(tmp_path) -> None:
    driver = WhisplayLcdDriver(runtime_path=tmp_path / "missing.py")
    board = FakeBoard()
    driver.board = board

    driver.turn_on()

    assert board.backlight == 80
    assert driver.backlight_enabled


def test_lcd_set_brightness_clamps_value(tmp_path) -> None:
    driver = WhisplayLcdDriver(runtime_path=tmp_path / "missing.py")
    board = FakeBoard()
    driver.board = board

    driver.set_brightness(120)

    assert board.backlight == 100
    assert driver.backlight == 100
