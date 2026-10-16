"""Read-only metrics for this process; browser process trees are reported separately."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any


def process_resources() -> dict[str, Any]:
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        class Counters(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                        *[(name, ctypes.c_size_t) for name in (
                            "PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage",
                            "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage", "QuotaNonPagedPoolUsage",
                            "PagefileUsage", "PeakPagefileUsage", "PrivateUsage")]]
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
        kernel.GetProcessHandleCount.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        handle = kernel.GetCurrentProcess()
        counters = Counters()
        counters.cb = ctypes.sizeof(counters)
        count = wintypes.DWORD()
        if not psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb):
            return {"rss_bytes": None, "handles": None}
        counted = kernel.GetProcessHandleCount(handle, ctypes.byref(count))
        return {"rss_bytes": counters.WorkingSetSize, "peak_rss_bytes": counters.PeakWorkingSetSize,
                "handles": count.value if counted else None}
    status = Path("/proc/self/status")
    if status.is_file():
        values = {}
        for line in status.read_text().splitlines():
            if line.startswith(("VmRSS:", "VmHWM:")):
                key, value, *_ = line.split()
                values[key] = int(value) * 1024
        return {"rss_bytes": values.get("VmRSS:"), "peak_rss_bytes": values.get("VmHWM:"),
                "handles": len(list(Path("/proc/self/fd").iterdir()))}
    return {"rss_bytes": None, "handles": None}
