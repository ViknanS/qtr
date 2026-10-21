"""Static checks over the whole repository (no heavy imports)."""

import ast
import json
import os
import pathlib
import shutil
import stat
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PKG = ROOT / "qqr"


def _py_files():
    return sorted(p for p in PKG.rglob("*.py") if "__pycache__" not in p.parts)


def test_every_module_compiles():
    for path in _py_files():
        compile(path.read_text(encoding="utf-8"), str(path), "exec")


@pytest.mark.parametrize("config", sorted(PKG.glob("examples/**/config.py")), ids=lambda p: str(p.relative_to(PKG)))
def test_config_all_exports_exist(config):
    """``__all__`` must only name symbols the module defines (a stale name
    makes ``from config import *`` raise AttributeError)."""
    tree = ast.parse(config.read_text(encoding="utf-8"))
    defined, exported = set(), []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            defined.add(node.name)
        elif isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for t in targets:
                for n in ast.walk(t):
                    if isinstance(n, ast.Name):
                        defined.add(n.id)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            defined.update((a.asname or a.name).split(".")[0] for a in node.names)
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "__all__" for t in node.targets):
            exported = [e.value for e in node.value.elts]
    missing = [name for name in exported if name not in defined]
    assert not missing, f"{config}: __all__ names undefined symbols {missing}"


def test_no_lfs_pointer_files_in_data():
    """The upstream archive shipped Git-LFS pointer stubs instead of data."""
    pointers = []
    for path in list((ROOT / "data").rglob("*.jsonl")) + list(ROOT.glob("assets/*.png")):
        with open(path, "rb") as fh:
            if fh.read(40).startswith(b"version https://git-lfs"):
                pointers.append(str(path.relative_to(ROOT)))
    assert not pointers, f"LFS pointers instead of content: {pointers}"


def test_train_jsonl_rows_parse():
    path = ROOT / "data" / "travel" / "train.jsonl"
    with open(path, encoding="utf-8") as fh:
        rows = [json.loads(line) for line in fh if line.strip()]
    assert rows and all("query" in r for r in rows)


# ------------------------------------------------------------- script guard
GUARDED = sorted(p for p in (ROOT / "scripts").rglob("*.sh") if "qqr platform guard" in p.read_text())


def test_all_gpu_launchers_are_guarded():
    launchers = [
        p for p in (ROOT / "scripts").rglob("*.sh")
        if p.parent.name not in {"models", "secrespond"}
    ]
    assert launchers and set(launchers) == set(GUARDED)
    for p in launchers:
        assert "pkill -9 python\n" not in p.read_text(), f"blanket python kill in {p}"


def _guard_prefix(script: pathlib.Path, tmp_path: pathlib.Path) -> pathlib.Path:
    lines = script.read_text().splitlines()
    end = max(i for i, line in enumerate(lines) if line.startswith("# -----------"))
    out = tmp_path / "guard.sh"
    out.write_text("\n".join(lines[: end + 1]) + "\necho PASSED_GUARD\n")
    return out


def _fake_bin(tmp_path, uname, with_gpu):
    d = tmp_path / f"bin-{uname}-{with_gpu}"
    d.mkdir()
    tools = {"uname": f"#!/bin/sh\necho {uname}\n"}
    if with_gpu:
        tools["nvidia-smi"] = "#!/bin/sh\nexit 0\n"
    for name, body in tools.items():
        f = d / name
        f.write_text(body)
        f.chmod(f.stat().st_mode | stat.S_IEXEC)
    return d


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash not available")
@pytest.mark.parametrize("script", GUARDED, ids=lambda p: str(p.relative_to(ROOT)))
def test_guard_blocks_non_gpu_hosts(script, tmp_path):
    guard = _guard_prefix(script, tmp_path)

    def run(uname, gpu, force=False):
        env = {"PATH": f"{_fake_bin(tmp_path, uname, gpu)}:/usr/bin:/bin"}
        if force:
            env["QQR_FORCE_RUN"] = "1"
        return subprocess.run(["bash", str(guard)], env=env, capture_output=True, text=True)

    mac = run("Darwin", gpu=True)
    assert mac.returncode == 1 and "Refusing to start" in mac.stderr
    if shutil.which("nvidia-smi", path="/usr/bin:/bin") is None:
        no_gpu = run("Linux", gpu=False)
        assert no_gpu.returncode == 1
    gpu_node = run("Linux", gpu=True)
    assert gpu_node.returncode == 0 and "PASSED_GUARD" in gpu_node.stdout
    assert "PASSED_GUARD" in run("Darwin", gpu=False, force=True).stdout


# -------------------------------------------------------------- demo / doctor
def test_demo_cli_json():
    out = subprocess.run(
        [sys.executable, "-m", "qqr.demo", "--json"],
        capture_output=True, text=True, cwd=ROOT, check=True,
        env={**os.environ, "PYTHONPATH": str(ROOT)},
    )
    report = json.loads(out.stdout)
    assert set(report["results"]) == {"anchor", "round_robin", "swiss", "double_elimination", "single_elimination"}
    assert report["results"]["round_robin"]["judge_calls"] == 28
    assert "mock" in report["judge"]


def test_doctor_runs():
    out = subprocess.run(
        [sys.executable, "-m", "qqr.doctor"], capture_output=True, text=True, cwd=ROOT,
        env={**os.environ, "PYTHONPATH": str(ROOT), "OPENAI_API_KEY": "sk-should-not-leak"},
    )
    assert out.returncode == 0, out.stderr
    assert "import qqr" in out.stdout
    assert "sk-should-not-leak" not in out.stdout


# --------------------------------------------------------- secret scanning
# High-confidence provider formats that GitHub push protection blocks. The
# Claw-Eval-Hard fixtures use deliberately fake credentials; they are written
# with a ``FIXTURE-`` prefix so they never match these formats (see CHANGES.md).
PROVIDER_PATTERNS = {
    "stripe": r"\b(?:sk|rk|pk)_live_[0-9A-Za-z]{10,}",
    "stripe_webhook": r"\bwhsec_[0-9A-Za-z]{10,}",
    "slack": r"\bxox[abposr]-[0-9A-Za-z-]{8,}",
    "mailgun": r"\bkey-[0-9a-z]{32}",
    "twilio": r"\b(?:AC|SK)[0-9a-f]{32}\b",
    "aws_access_key": r"(?:AKIA|ASIA)[0-9A-Z]{16}",
    "github": r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})",
    "gitlab": r"\bglpat-[0-9A-Za-z_-]{10,}",
    "anthropic": r"\bsk-ant-[A-Za-z0-9_-]{8,}",
    "openai_project": r"\bsk-proj-[A-Za-z0-9_-]{10,}",
    "google": r"\bAIza[0-9A-Za-z_-]{20,}",
    "sendgrid": r"\bSG\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}",
    "private_key": r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
}
_TEXT_SUFFIXES = {".py", ".json", ".jsonl", ".yaml", ".yml", ".md", ".txt", ".csv", ".toml", ".sh", ".html", ".js", ".css", ".cfg", ".ini", ""}


def test_no_provider_format_credentials_in_repo():
    import re

    compiled = {k: re.compile(v) for k, v in PROVIDER_PATTERNS.items()}
    hits = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix not in _TEXT_SUFFIXES:
            continue
        if any(part in {".git", ".venv", "node_modules", "__pycache__"} for part in path.parts):
            continue
        if path == pathlib.Path(__file__).resolve():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for name, rx in compiled.items():
            for m in rx.finditer(text):
                hits.append(f"{path.relative_to(ROOT)}: {name}: {m.group(0)[:24]}")
    assert not hits, "credential-shaped strings found:\n" + "\n".join(hits[:20])
