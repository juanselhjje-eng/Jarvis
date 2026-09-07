from __future__ import annotations

import ctypes
import json
import os
import platform
import shutil
import subprocess
import tempfile
import webbrowser
from pathlib import Path
from typing import Any

import psutil


class SystemControl:
    """Herramientas locales explícitas para inspeccionar y modificar Windows."""

    def _powershell(self, command: str, timeout: int = 10) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command], capture_output=True, text=True, timeout=timeout, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))

    def pc_status(self) -> str:
        vm = psutil.virtual_memory(); cpu = psutil.cpu_percent(interval=0.5); disk = psutil.disk_usage(os.environ.get("SystemDrive", "C:") + "\\")
        lines = [f"Windows: {platform.system()} {platform.release()}", f"Equipo: {platform.node()}", f"CPU: {platform.processor() or 'No disponible'}", f"Uso de CPU: {cpu:.0f}%", f"RAM: {vm.percent:.0f}% ({vm.used / 2**30:.1f} GB / {vm.total / 2**30:.1f} GB)", f"Disco C: {disk.percent:.0f}% ({disk.used / 2**30:.1f} GB / {disk.total / 2**30:.1f} GB)", f"Procesos: {len(psutil.pids())}"]
        gpu = self._powershell("Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name", 5); gpus = [x.strip() for x in gpu.stdout.splitlines() if x.strip()]
        if gpus: lines.append("GPU: " + "; ".join(gpus))
        lines.append(f"Temperatura: {self.cpu_temperature()}"); return "\n".join(lines)

    def cpu_temperature(self) -> str:
        result = self._powershell("Get-CimInstance -Namespace root/wmi -ClassName MSAcpi_ThermalZoneTemperature -ErrorAction SilentlyContinue | Select-Object -ExpandProperty CurrentTemperature", 5)
        values=[]
        for line in result.stdout.splitlines():
            try:
                raw=float(line.strip())
                if raw>200: values.append(raw/10.0-273.15)
            except ValueError: pass
        return ", ".join(f"{v:.1f} °C" for v in values[:4]) + " (sensor ACPI disponible)" if values else "no disponible mediante los sensores de Windows"

    def open_application(self, name: str) -> str:
        clean = name.strip().lower()
        aliases = {
            "calculadora":"calc.exe","calc":"calc.exe","bloc de notas":"notepad.exe","notepad":"notepad.exe",
            "explorador":"explorer.exe","explorador de archivos":"explorer.exe","administrador de tareas":"taskmgr.exe",
            "configuración":"ms-settings:","configuracion":"ms-settings:","settings":"ms-settings:","panel de control":"control.exe",
            "cmd":"cmd.exe","powershell":"powershell.exe",
        }
        web_services = {
            "teams":"https://teams.live.com/v2/","teams personal":"https://teams.live.com/v2/","teams educativo":"https://teams.microsoft.com/",
            "microsoft teams":"https://teams.live.com/v2/","gmail":"https://mail.google.com/","calendar":"https://calendar.google.com/",
            "google calendar":"https://calendar.google.com/","telegram":"https://web.telegram.org/","github":"https://github.com/",
            "youtube":"https://www.youtube.com/","google":"https://www.google.com/","spotify":"https://open.spotify.com/",
            "discord":"https://discord.com/app/","chrome":"https://www.google.com/","edge":"https://www.microsoft.com/edge/",
        }
        if clean in web_services:
            webbrowser.open(web_services[clean], new=2); return f"Abierto: {name}."
        target = aliases.get(clean)
        if target is None:
            safe = clean.replace("'", "''")
            result = self._powershell(f"Get-StartApps | Where-Object {{$_.Name -like '*{safe}*'}} | Select-Object -First 1 -ExpandProperty AppID", 8)
            app_id = result.stdout.strip()
            if app_id:
                subprocess.Popen(["explorer.exe", f"shell:AppsFolder\\{app_id}"], shell=False); return f"Aplicación abierta: {name}."
            return f"No encontré '{name}' entre las aplicaciones registradas de Windows."
        if target.startswith("ms-"): os.startfile(target)  # type: ignore[attr-defined]
        else: subprocess.Popen([shutil.which(target) or target], shell=False)
        return f"Aplicación abierta: {name}."

    def set_wallpaper(self, image_path: str) -> str:
        path=Path(os.path.expandvars(os.path.expanduser(image_path.strip().strip('"'))).resolve())
        if not path.is_file(): return f"No encontré la imagen: {path}"
        if path.suffix.lower() not in {".jpg",".jpeg",".png",".bmp"}: return "El fondo debe ser JPG, JPEG, PNG o BMP."
        ctypes.windll.user32.SystemParametersInfoW(20,0,str(path),3); return f"Fondo de pantalla cambiado a {path.name}."

    def optimization_report(self) -> str:
        vm=psutil.virtual_memory(); disk=psutil.disk_usage(os.environ.get("SystemDrive","C:")+"\\"); temp=Path(tempfile.gettempdir()); temp_size=self._directory_size(temp)
        startup=self._powershell("Get-CimInstance Win32_StartupCommand | Select-Object Name,Command | ConvertTo-Json -Compress",8); count=0
        if startup.stdout.strip():
            try: data:Any=json.loads(startup.stdout); count=len(data) if isinstance(data,list) else 1
            except Exception: pass
        return ("No voy a cambiar nada todavía. Este es el plan que revisaría:\n" f"- Temporales: aproximadamente {temp_size/2**20:.0f} MB.\n" "- Papelera: solo con autorización.\n" f"- Inicio: {count} entradas; no deshabilitaré ninguna sin explicarlo.\n" f"- Disco C: {disk.percent:.0f}% usado.\n" f"- RAM: {vm.percent:.0f}% en uso.\n" "- Revisar procesos y actualizaciones de Windows.\n" "- No borraré archivos personales ni instalaré software automáticamente.\n" "Para ejecutar una optimización pediré confirmación.")

    def optimize_safe(self) -> str:
        removed=0; temp=Path(tempfile.gettempdir())
        try: items=list(temp.iterdir())
        except OSError: items=[]
        for item in items:
            try:
                if item.is_file() or item.is_symlink(): item.unlink(); removed+=1
                elif item.is_dir(): shutil.rmtree(item,ignore_errors=True); removed+=1
            except OSError: pass
        return f"Optimización básica completada. Intenté limpiar {removed} elementos temporales; los que estaban en uso se dejaron intactos."

    @staticmethod
    def _directory_size(path: Path) -> int:
        total=0
        try:
            for item in path.rglob("*"):
                try:
                    if item.is_file(): total+=item.stat().st_size
                except OSError: pass
        except OSError: pass
        return total
