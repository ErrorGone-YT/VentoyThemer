from __future__ import annotations

import runpy
from pathlib import Path


def main() -> None:
    script_path = Path(__file__).resolve().with_name("VentoyThemer.py")
    namespace = runpy.run_path(str(script_path), run_name="ventoythemer_entry")
    namespace["main"]()


if __name__ == "__main__":
    main()
