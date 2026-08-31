from device.axiomvox_device.buttons import WhisplayButtonPoller, _gesture_from_text


class FakeWhisplayBoard:
    def __init__(self) -> None:
        self.press = None
        self.release = None

    def on_button_press(self, callback) -> None:
        self.press = callback

    def on_button_release(self, callback) -> None:
        self.release = callback


def test_gesture_from_text_maps_common_button_words() -> None:
    assert _gesture_from_text("single true") == "short"
    assert _gesture_from_text("double") == "double"
    assert _gesture_from_text("long") == "long"
    assert _gesture_from_text("very long") == "very_long"


def test_whisplay_button_poller_uses_runtime_callbacks(monkeypatch) -> None:
    board = FakeWhisplayBoard()
    times = iter([10.0, 10.2])
    monkeypatch.setattr("device.axiomvox_device.buttons.time.monotonic", lambda: next(times))

    poller = WhisplayButtonPoller(probe=None, board=board)
    board.press()
    board.release()

    events = tuple(poller.poll())

    assert poller.callback_detail == "Whisplay button callbacks attached"
    assert len(events) == 1
    assert events[0].source == "whisplay"
    assert events[0].gesture == "short"


def test_whisplay_button_poller_maps_long_press(monkeypatch) -> None:
    board = FakeWhisplayBoard()
    times = iter([10.0, 10.85])
    monkeypatch.setattr("device.axiomvox_device.buttons.time.monotonic", lambda: next(times))

    poller = WhisplayButtonPoller(probe=None, board=board)
    board.press()
    board.release()

    events = tuple(poller.poll())

    assert events[0].gesture == "long"
    assert WhisplayButtonPoller.LONG_PRESS_SECONDS == 0.8
