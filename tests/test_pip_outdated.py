import json
import subprocess


def test_pip_outdated_runs():
    result = subprocess.run(
        ["pip", "list", "--outdated", "--format=json"],
        capture_output=True,
        text=True,
        check=True,
    )
    data = json.loads(result.stdout)
    assert isinstance(data, list)
