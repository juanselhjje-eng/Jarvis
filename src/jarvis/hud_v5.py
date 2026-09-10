from __future__ import annotations

from .hud_v6 import JarvisHUDv6
from .subagents import SubagentTeam


class JarvisHUDv5(JarvisHUDv6):
    """Compatibilidad con el runtime anterior usando el nuevo Mission Control v6."""

    def __init__(self, brain, voice, process_command, shutdown, neural=None, stop_mission=None):
        self.subagents = SubagentTeam()
        super().__init__(
            brain=brain,
            voice=voice,
            process_command=process_command,
            shutdown=shutdown,
            neural=neural,
            stop_mission=stop_mission,
            subagents=self.subagents,
        )

    def set_mission(self, text):
        agents = self.subagents.activate_for(text)
        super().set_mission(text)
        self.update_subagents(agents)
        self.add_message("SUBAGENTS", self.subagents.event_text())
