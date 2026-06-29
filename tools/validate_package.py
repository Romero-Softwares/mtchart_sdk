from __future__ import annotations

import subprocess
import sys
import tomllib
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str]) -> None:
    print("+", " ".join(command))
    env = os.environ.copy()
    source_path = str(ROOT / "src")
    current_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = source_path if not current_pythonpath else f"{source_path}{os.pathsep}{current_pythonpath}"
    subprocess.run(command, cwd=ROOT, check=True, env=env)


def assert_metadata() -> None:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = data["project"]
    required = ["name", "version", "description", "readme", "license", "authors"]
    missing = [field for field in required if not project.get(field)]
    if missing:
        raise SystemExit(f"Campos obrigatorios ausentes no pyproject.toml: {', '.join(missing)}")
    if not (ROOT / "README.md").exists():
        raise SystemExit("README.md ausente.")
    if not (ROOT / "LICENSE.md").exists():
        raise SystemExit("LICENSE.md ausente.")
    if not (ROOT / "MANIFEST.in").exists():
        raise SystemExit("MANIFEST.in ausente.")


def main() -> int:
    assert_metadata()
    run([sys.executable, "-m", "compileall", "src", "examples", "tools"])
    run([sys.executable, "-m", "pytest"])
    run([sys.executable, "examples/basic_process.py"])
    run(
        [
            sys.executable,
            "-m",
            "mtchart_sdk.cli",
            "--catalog-db",
            ".tmp_package_validation.db",
            "--value",
            "188.7",
        ]
    )
    print("Pacote local validado com sucesso.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
