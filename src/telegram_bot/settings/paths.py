from pathlib import Path

# Detecta la raíz del proyecto automáticamente (por ejemplo buscando "requirements.txt")
def find_project_root(start_path: Path, marker_file: str = "pyproject.toml") -> Path:
    current = start_path.resolve()
    while not (current / marker_file).exists() and current != current.parent:
        current = current.parent
    return current

BASE_DIR = find_project_root(Path(__file__))

WHITELIST_PATH = BASE_DIR / "whitelist.txt"

for file in [
    WHITELIST_PATH]:
    file.touch(exist_ok=True)