from __future__ import annotations

import ctypes
import json
import os
import platform
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import psutil


class SystemControl:
    """Herramientas locales explícitas para inspeccionar y modificar Windows."""

    def _powershell(self, command: str, timeout: int = 10) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
            capture_output=True,
            text=True,
            timeout=timeout,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )

    def pc_status(self) -> str:
        vm = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=0.5)
        disk = psutil.disk_usage(os.environ.get("SystemDrive", "C:") + "\\")
        lines = [
            f"Windows: {platform.system()} {platform.release()}",
            f"Equipo: {platform.node()}",
            f"CPU: {platform.processor() or 'No disponible'}",
            f"Uso de CPU: {cpu:.0f}%",
            f"RAM: {vm.percent:.0f}% ({vm.used / 2**30:.1f} GB / {vm.total / 2**30:.1f} GB)",
            f"Disco C: {disk.percent:.0f}% ({disk.used / 2**30:.1f} GB / {disk.total / 2**30:.1f} GB)",
            f"Procesos: {len(psutil.pids())}",
        ]
        gpu = self._powershell("Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name", 5)
        gpus = [x.strip() for x in gpu.stdout.splitlines() if x.strip()]
        if gpus:
            lines.append("GPU: " + "; ".join(gpus))
        lines.append(f"Temperatura: {self.cpu_temperature()}")
        return "\n".join(lines)

    def cpu_temperature(self) -> str:
        # Muchos equipos no exponen el sensor real de CPU por WMI. Nunca inventamos el valor.
        result = self._powershell(
            "Get-CimInstance -Namespace root/wmi -ClassName MSAcpi_ThermalZoneTemperature "
            "-ErrorAction SilentlyContinue | Select-Object -ExpandProperty CurrentTemperature",
            5,
        )
        values: list[float] = []
        for line in result.stdout.splitlines():
            try:
                raw = float(line.strip())
                if raw > 200:
                    values.append(raw / 10.0 - 273.15)
            except ValueError:
                continue
        if values:
            return ", ".join(f"{value:.1f} °C" for value in values[:4]) + " (sensor ACPI disponible)"
        return "no disponible mediante los sensores de Windows"

    def open_application(self, name: str) -> str:
        aliases = {
            "calculadora": "calc.exe", "calc": "calc.exe",
            "bloc de notas": "notepad.exe", "notepad": "notepad.exe",
            "explorador": "explorer.exe", "explorador de archivos": "explorer.exe",
            "administrador de tareas": "taskmgr.exe", "configuración": "ms-settings:",
            "configuracion": "ms-settings:", "settings": "ms-settings:",
            "panel de control": "control.exe", "cmd": "cmd.exe", "powershell": "powershell.exe",
        }
        clean_name = name.lower().strip()
        target = aliases.get(clean_name)

        if target is None:
            # Permite "abre Spotify", "abre Discord", etc. si Windows lo tiene
            # registrado en el menú Inicio, sin ejecutar comandos arbitrarios.
            result = self._powershell(
                "$n=$args[0]; Get-StartApps | Where-Object {$_.Name -like ('*'+$n+'*')} | Select-Object -First 1 -ExpandProperty AppID",
                8,
            )
            # PowerShell no recibe $args con -Command de forma consistente en todas
            # las versiones, así que hacemos una búsqueda segura con texto escapado.
            safe = clean_name.replace("'", "''")
            result = self._powershell(
                f"Get-StartApps | Where-Object {{$_.Name -like '*{safe}*'}} | Select-Object -First 1 -ExpandProperty AppID",
                8,
            )
            app_id = result.stdout.strip()
            if app_id:
                subprocess.Popen(["explorer.exe", f"shell:AppsFolder\\{app_id}"], shell=False)
                return f"Aplicación abierta: {name}."
            target = shutil.which(name.strip()) or name.strip()

        if target.startswith("ms-"):
            os.startfile(target)  # type: ignore[attr-defined]
        else:
            executable = shutil.which(target) or target
            subprocess.Popen([executable], shell=False)
        return f"Aplicación abierta: {name}."

    def set_wallpaper(self, image_path: str) -> str:
        path = Path(os.path.expandvars(os.path.expanduser(image_path.strip().strip('"'))).resolve())
        if not path.is_file():
            return f"No encontré la imagen: {path}"
        if path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".bmp"}:
            return "El fondo debe ser una imagen JPG, JPEG, PNG o BMP."
        ctypes.windll.user32.SystemParametersInfoW(20, 0, str(path), 3)
        return f"Fondo de pantalla cambiado a {path.name}."

    def optimization_report(self) -> str:
        vm = psutil.virtual_memory()
        disk = psutil.disk_usage(os.environ.get("SystemDrive", "C:") + "\\")
        temp = Path(tempfile.gettempdir())
        temp_size = self._directory_size(temp)
        startup = self._powershell(
            "Get-CimInstance Win32_StartupCommand | Select-Object Name,Command | ConvertTo-Json -Compress",
            8,
        )
        startup_count = 0
        if startup.stdout.strip():
            try:
                data: Any = json.loads(startup.stdout)
                startup_count = len(data) if isinstance(data, list) else 1
            except Exception:
                pass
        return (
            "No voy a cambiar nada todavía. Este es el plan que revisaría:\n"
            f"- Liberar archivos temporales de usuario: aproximadamente {temp_size / 2**20:.0f} MB detectados.\n"
            "- Vaciar la Papelera de reciclaje solo si lo autorizas.\n"
            f"- Revisar programas de inicio: {startup_count} entradas detectadas; no deshabilitaré ninguna sin decirte cuál y por qué.\n"
            f"- Revisar espacio del disco C: {disk.percent:.0f}% usado.\n"
            f"- Revisar memoria: {vm.percent:.0f}% en uso.\n"
            "- Revisar procesos que consumen CPU/RAM y proponerte cuáles cerrar.\n"
            "- Buscar actualizaciones de Windows mediante sus mecanismos normales.\n"
            "- No instalar software ni borrar archivos personales automáticamente.\n"
            "Para ejecutar una optimización, primero te mostraré las acciones concretas y pediré confirmación."
        )

    def optimize_safe(self) -> str:
        removed = 0
        temp = Path(tempfile.gettempdir())
        try:
            items = list(temp.iterdir())
        except OSError:
            items = []
        for item in items:
            try:
                if item.is_file() or item.is_symlink():
                    item.unlink()
                    removed += 1
                elif item.is_dir():
                    shutil.rmtree(item, ignore_errors=True)
                    removed += 1
            except OSError:
                continue
        return f"Optimización básica completada. Intenté limpiar {removed} elementos temporales; los que estaban en uso se dejaron intactos. No eliminé archivos personales ni instalé software."

    @staticmethod
    def _directory_size(path: Path) -> int:
        total = 0
        try:
            for item in path.rglob("*"):
                try:
                    if item.is_file():
                        total += item.stat().st_size
                except OSError:
                    continue
        except OSError:
            pass
        return total
