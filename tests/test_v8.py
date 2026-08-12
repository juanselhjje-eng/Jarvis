from tools.registry import list_tools, execute_tool
from core.orchestrator import Orchestrator

def main():
    tools = list_tools()
    required = {
        "open_application", "open_url", "open_folder", "open_file",
        "create_folder", "create_file", "append_file", "list_folder",
        "read_file", "delete_file", "system_info",
        "scan_local_music", "play_local_music",
    }
    missing = required - set(tools)
    assert not missing, f"Faltan herramientas: {missing}"

    assert isinstance(execute_tool("system_info"), str)

    jarvis = Orchestrator()
    assert jarvis._music_query("Jarvis, reproduce Mil Vidas") == "Mil Vidas"
    assert jarvis._app_query("Abre Unity") == "Unity"

    # File tool round-trip inside workspace.
    execute_tool("create_file", path="__test_v8.txt", content="JARVIS V8 OK")
    assert "JARVIS V8 OK" in execute_tool("read_file", path="__test_v8.txt")
    execute_tool("delete_file", path="__test_v8.txt")

    print("JARVIS V8 TESTS: OK")

if __name__ == "__main__":
    main()
