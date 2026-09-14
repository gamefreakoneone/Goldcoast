import subprocess
import tarfile
from pathlib import Path


def bundle(root: Path, target: Path):
    tracked = (
        subprocess.check_output(
            ["git", "-c", f"safe.directory={root.as_posix()}", "ls-files", "-z"], cwd=root
        )
        .decode()
        .split("\0")
    )
    exact = {"pyproject.toml", "README.md", "alembic.ini", ".dockerignore"}
    prefixes = ("src/", "migrations/", "data/studio_demo/", "web/")
    paths = {name for name in tracked if name in exact or name.startswith(prefixes)}
    paths.add(".dockerignore")
    paths.update(
        file.relative_to(root).as_posix()
        for file in (root / "infra/lightsail").iterdir()
        if file.is_file() and file.name != ".env" and not file.name.startswith(".env.")
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(target, "w:gz") as archive:
        for name in sorted(paths):
            path = root / name
            if path.is_symlink() or any(part.startswith(".env") for part in path.parts):
                raise ValueError(f"Unsafe deployment input: {name}")
            archive.add(path, arcname="Goldcoast/" + name, recursive=False)
    return len(paths)


def main():
    root = Path(__file__).resolve().parents[2]
    target = root / "output/deploy/goldcoast-lightsail.tar.gz"
    count = bundle(root, target)
    print(f"Packaged {count} files: {target}")
    print("No local .env, output, .git, or local accounts included.")


if __name__ == "__main__":
    main()
