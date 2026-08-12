from pathlib import Path
from tools.registry import list_tools, execute_tool
from core.orchestrator import Orchestrator


def main():
    tools = list_tools()
    required = {
        "open_application", "open_url", "open_folder", "open_file",
        "create_folder", "create_file", "append_file", "list_folder",
        "read_file", "delete_file", "system_info", "scan_local_music",
        "play_local_music", "type_text", "press_keys", "move_mouse", "click_mouse",
    }
    missing = required - set(tools)
    assert not missing, f"Faltan herramientas: {missing}"

    assert isinstance(execute_tool("system_info"), str)
    jarvis = Orchestrator()
    assert jarvis._deterministic("Abre Bloc de notas") is not None
    assert jarvis._deterministic("Reproduce Mil Vidas") is not None
    print("JARVIS V9 STATIC TESTS: OK")


if __name__ == "__main__":
    main()
