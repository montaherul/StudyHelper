"""
Hardware profiler and auto-tuning module for LocalStudy.
Detects CPU, RAM, and GPU capabilities to recommend optimal local processing parameters.
"""

import os
import platform
import subprocess
from typing import Dict, Any

from utils.logger import logger


class HardwareDetector:
    """Profiles system hardware and produces recommended execution presets."""

    @staticmethod
    def get_hardware_info() -> Dict[str, Any]:
        info = {
            "os": f"{platform.system()} {platform.release()}",
            "architecture": platform.machine(),
            "cpu_threads": os.cpu_count() or 4,
            "cpu_model": platform.processor() or "Multi-Core CPU",
            "ram_gb": 16.0,  # Default fallback
            "gpu_name": "Integrated Graphics",
            "has_cuda": False
        }

        # Query Windows CPU & RAM info if available
        if platform.system() == "Windows":
            try:
                # Get CPU name via registry or wmic/powershell
                import winreg
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
                cpu_name, _ = winreg.QueryValueEx(key, "ProcessorNameString")
                if cpu_name:
                    info["cpu_model"] = cpu_name.strip()
            except Exception:
                pass

            try:
                # Get RAM via ctypes GlobalMemoryStatusEx
                import ctypes

                class MEMORYSTATUSEX(ctypes.Structure):
                    _fields_ = [
                        ("dwLength", ctypes.c_ulong),
                        ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong),
                        ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong),
                        ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong),
                        ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                    ]

                stat = MEMORYSTATUSEX()
                stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
                if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
                    info["ram_gb"] = round(stat.ullTotalPhys / (1024 ** 3), 1)
                    info["avail_ram_gb"] = round(stat.ullAvailPhys / (1024 ** 3), 1)
            except Exception:
                pass

        # Check CUDA availability
        try:
            import ctranslate2
            cuda_avail = ctranslate2.get_cuda_device_count() > 0
            info["has_cuda"] = cuda_avail
            if cuda_avail:
                info["gpu_name"] = "NVIDIA CUDA Acceleration"
        except Exception:
            info["has_cuda"] = False

        return info

    @classmethod
    def get_recommended_settings(cls) -> Dict[str, Any]:
        """Calculates optimal defaults tailored to detected hardware."""
        hw = cls.get_hardware_info()
        threads = hw["cpu_threads"]
        ram = hw.get("ram_gb", 8.0)
        has_cuda = hw.get("has_cuda", False)

        # Thread reservation: Leave 2 threads for UI/OS
        worker_threads = max(1, threads - 2) if threads > 2 else 1

        # Model and quantization selection
        if has_cuda:
            recommended_model = "small"
            device = "cuda"
            compute_type = "float16"
        elif ram >= 16.0:
            recommended_model = "small"
            device = "cpu"
            compute_type = "int8"
        elif ram >= 8.0:
            recommended_model = "base"
            device = "cpu"
            compute_type = "int8"
        else:
            recommended_model = "tiny"
            device = "cpu"
            compute_type = "int8"

        return {
            "hardware": hw,
            "recommended_model": recommended_model,
            "device": device,
            "compute_type": compute_type,
            "cpu_threads": worker_threads,
            "recommended_interval": 30,
            "recommended_pdf_layout": "2-up"
        }
