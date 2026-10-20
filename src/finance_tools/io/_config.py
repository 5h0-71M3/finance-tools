"""
THIS IS WHERE WE WILL STORE OUR DIRECTORY INFORMATION

The paths come from ``finance_tools.config.json`` in the repo root (gitignored, one per
analyst; copy ``finance_tools.config.example.json`` to start). They live in their own file,
not ``pipeui.config.json``, because pipeui rewrites its config on save and drops keys it
doesn't know.
"""
import json
from pathlib import Path

CONFIG_FILENAME = "finance_tools.config.json"

DEFAULTS = {
    "downloads": "~/Downloads",
    "desktop": "~/Desktop",
}
"""keys with a sensible per-machine default; the Google Drive folders have none"""

REQUIRED = ("downloads", "desktop", "data_analysis", "account_current")


def find_config_dir(filename: str) -> Path | None:
    """The dir owning ``filename``, or None.

    Searches upward from CWD first (user standing in the repo), then from the installed
    package location (editable install -> repo src/).
    """
    for start in (Path.cwd(), Path(__file__).resolve().parent):
        for d in (start, *start.parents):
            if (d / filename).exists():
                return d
    return None


def load_directory_config() -> dict[str, str]:
    config_dir = find_config_dir(CONFIG_FILENAME)
    if config_dir is None:
        raise FileNotFoundError(
            f"Could not locate {CONFIG_FILENAME}. Copy finance_tools.config.example.json to "
            f"{CONFIG_FILENAME} in the finance-tools repo root and set your folder paths."
        )
    config = {**DEFAULTS, **json.loads((config_dir / CONFIG_FILENAME).read_text())}
    missing = [key for key in REQUIRED if not config.get(key)]
    if missing:
        raise KeyError(f"{config_dir / CONFIG_FILENAME} is missing {missing}.")
    return {key: str(Path(value).expanduser()) for key, value in config.items()}


directory_config = load_directory_config()
"""
downloads, desktop, data_analysis, account_current
"""
