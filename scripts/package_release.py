"""Build a source-and-documentation archive without caches or Git metadata."""
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {".git", "__pycache__", ".pytest_cache", "dist", ".venv"}


def package():
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    if not version or any(c not in "0123456789.-abcdefghijklmnopqrstuvwxyz" for c in version):
        raise ValueError("Invalid release version")
    docs = ROOT / "build" / "docs" / "index.html"
    if not docs.is_file():
        raise FileNotFoundError("Run scripts/build_docs.py before packaging")
    target = ROOT / "dist" / f"shop-payments-{version}.zip"
    target.parent.mkdir(exist_ok=True)
    included = []
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for source in sorted(ROOT.rglob("*")):
            rel = source.relative_to(ROOT)
            if not source.is_file() or any(part in EXCLUDED for part in rel.parts):
                continue
            if source.suffix in {".pyc", ".pyo"}:
                continue
            if rel.parts[0] == "build" and rel.parts[:2] != ("build", "docs"):
                continue
            archive.write(source, str(rel))
            included.append(str(rel))
    print("Archive:", target.relative_to(ROOT))
    print("Files:", len(included))
    for name in included:
        print("  " + name)
    return target


if __name__ == "__main__":
    package()
