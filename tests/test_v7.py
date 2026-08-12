from tools.registry import list_tools, execute_tool
from core.orchestrator import Orchestrator

def main():
    tools = list_tools()
    required = {
        "open_application",
        "open_url",
        "play_local_music",
        "scan_local_music",
        "system_info",
    }
    missing = required - set(tools)
    assert not missing, f"Faltan herramientas: {missing}"

    result = execute_tool("system_info")
    assert isinstance(result, str)

    jarvis = Orchestrator()
    music_command = jarvis._music_query("Jarvis, reproduce Mil Vidas")
    assert music_command == "mil vidas"

    app_command = jarvis._app_query("Abre Unity")
    assert app_command == "Unity"

    print("JARVIS V7 TESTS: OK")

if __name__ == "__main__":
    main()
