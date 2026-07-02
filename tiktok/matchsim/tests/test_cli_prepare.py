import json
import subprocess
import sys
from pathlib import Path

CLI = str(Path(__file__).resolve().parents[1] / "cli.py")


def test_cli_prepare_writes_bundle(tmp_path):
    out = tmp_path / "bundle.json"
    r = subprocess.run(
        [sys.executable, CLI, "prepare", "--home", "MUN", "--away", "RMA",
         "--competition", "ucl", "--seed", "21", "--frames", "60",
         "--out", str(out)],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    data = json.loads(out.read_text(encoding="utf-8"))
    assert set(data) == {"match", "theme", "motion"}
    assert data["theme"]["key"] == "ucl"
    assert data["theme"]["united_home"] is True
    assert len(data["motion"]) == 60
    assert data["match"]["events"][-1]["type"] == "full_time"


def test_cli_simulate_still_works(tmp_path):
    r = subprocess.run(
        [sys.executable, CLI, "simulate", "--home", "MUN", "--away", "RMA",
         "--seed", "21"],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout)["fixture"]["home"]["abbr"] == "MUN"
