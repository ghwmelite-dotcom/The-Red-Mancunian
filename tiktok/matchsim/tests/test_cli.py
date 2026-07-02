import json
import subprocess
import sys
from pathlib import Path

CLI = str(Path(__file__).resolve().parents[1] / "cli.py")


def test_cli_writes_valid_json(tmp_path):
    out = tmp_path / "match.json"
    r = subprocess.run(
        [sys.executable, CLI, "simulate", "--home", "MUN", "--away", "RMA",
         "--competition", "ucl", "--seed", "21", "--out", str(out)],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["fixture"]["home"]["abbr"] == "MUN"
    assert data["fixture"]["seed"] == 21
    assert data["events"][-1]["type"] == "full_time"


def test_cli_deterministic_stdout():
    base = [sys.executable, CLI, "simulate", "--home", "MUN", "--away", "RMA",
            "--seed", "21"]
    a = subprocess.run(base, capture_output=True, text=True)
    b = subprocess.run(base, capture_output=True, text=True)
    assert a.returncode == 0 and b.returncode == 0
    assert a.stdout == b.stdout
