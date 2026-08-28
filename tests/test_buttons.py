from device.axiomvox_device.buttons import _gesture_from_text


def test_gesture_from_text_maps_common_button_words() -> None:
    assert _gesture_from_text("single true") == "short"
    assert _gesture_from_text("double") == "double"
    assert _gesture_from_text("long") == "long"
    assert _gesture_from_text("very long") == "very_long"
