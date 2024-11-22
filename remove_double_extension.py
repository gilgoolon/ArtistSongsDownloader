from glob import glob
from pathlib import Path


folder = "."


for path in glob(f"{folder}/**"):
    path = Path(path)
    if path.stem.endswith(path.suffix):
        path.rename(path.stem)
