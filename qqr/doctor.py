"""Environment check: which parts of qqr can run on this machine?

    python -m qqr.doctor

Reports the Python version, installed optional dependencies, GPU/CUDA
availability and which credentials are set (values are never printed), then
summarises which components are runnable. Exit code is 0 unless the core
package itself cannot be imported.
"""

from __future__ import annotations

import importlib.util
import os
import platform
import shutil
import sys

CORE = ["agents", "mcp", "openai", "httpx", "numpy", "cachetools"]
GROUPS = {
    "MCP tool servers  (pip install -e '.[tools]')": ["click", "requests", "trafilatura", "pypdf"],
    "tau2-bench env    (pip install -e '.[tau2]')": ["pandas", "litellm", "loguru", "deepdiff", "toml"],
    "Training stack    (slime, Linux + NVIDIA)": ["slime", "torch", "sglang_router", "ray", "megatron"],
}
CREDENTIALS = [
    "LLM_JUDGE_API_KEY",
    "DASHSCOPE_API_KEY",
    "OPENAI_API_KEY",
    "AMAP_MAPS_API_KEY",
    "BAILIAN_WEB_SEARCH_API_KEY",
    "SEARCH_API_KEY",
    "INSPECTOR_OPENAI_BASE_URL",
    "USER_SIM_BASE_URL",
    "E2B_API_KEY",
    "IDEALAB_API_KEY",
]


def _has(module: str) -> bool:
    try:
        return importlib.util.find_spec(module) is not None
    except (ImportError, ValueError):
        return False


def _mark(ok: bool) -> str:
    return "ok " if ok else "-- "


def main() -> int:
    print(f"qqr doctor  |  Python {platform.python_version()}  |  {platform.system()} {platform.machine()}\n")

    py_ok = sys.version_info >= (3, 11)
    print(f"[{_mark(py_ok)}] Python >= 3.11 (asyncio.TaskGroup)")

    core_missing = [m for m in CORE if not _has(m)]
    print(f"[{_mark(not core_missing)}] core dependencies" + (f"  missing: {core_missing}" if core_missing else ""))

    try:
        import qqr  # noqa: F401  (registers reward models / prompts / llms)
        from qqr import registers

        methods = sorted(registers.reward_model.keys)
        import_ok = True
        print(f"[ok ] import qqr  -> tournaments: {', '.join(methods)}")
    except Exception as exc:  # pragma: no cover - surfaced to the user
        import_ok = False
        print(f"[-- ] import qqr failed: {type(exc).__name__}: {exc}")

    print()
    for title, modules in GROUPS.items():
        present = [m for m in modules if _has(m)]
        print(f"[{_mark(len(present) == len(modules))}] {title}: {len(present)}/{len(modules)} installed")

    gpu = shutil.which("nvidia-smi") is not None
    linux = platform.system() == "Linux"
    print(f"\n[{_mark(linux)}] Linux (training scripts refuse to start elsewhere)")
    print(f"[{_mark(gpu)}] nvidia-smi on PATH (NVIDIA GPU)")

    print("\nCredentials (values hidden):")
    for name in CREDENTIALS:
        print(f"  [{_mark(bool(os.getenv(name)))}] {name}")

    print("\nRunnable here:")
    print(f"  {'yes' if import_ok else 'no '}  ArenaRL tournaments + offline demo   (python -m qqr.demo)")
    print(f"  {'yes' if import_ok else 'no '}  unit / integration tests            (pytest)")
    train_ok = linux and gpu and _has("slime") and _has("torch")
    print(f"  {'yes' if train_ok else 'no '}  RL training scripts                 (bash scripts/...; needs slime v0.3.1 + 8x GPUs)")
    return 0 if import_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
