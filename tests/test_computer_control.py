from tools import computer_bridge
from tools.registry import TOOLS


def test_computer_controls_registered():
    computer_bridge.install()
    expected = {
        "wait", "get_active_window", "get_mouse_position", "screenshot",
        "screen_ocr", "scroll", "drag_mouse", "double_click", "hotkey",
        "copy_selection", "paste_text", "focus_window", "computer_observe",
    }
    assert expected.issubset(TOOLS)


def test_registry_has_no_delete_tool():
    assert "delete_file" not in TOOLS
