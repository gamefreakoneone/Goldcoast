import importlib.util
import tarfile
from pathlib import Path


def load_script(name):
    path = Path(__file__).resolve().parents[1] / "infra/lightsail" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"hosted_{name}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_configuration_preserves_password_and_omits_live_credentials(tmp_path, monkeypatch, capsys):
    module = load_script("configure")
    monkeypatch.setattr(module, "__file__", str(tmp_path / "configure.py"))
    module.main()
    first = (tmp_path / ".env").read_text()
    values = dict(line.split("=", 1) for line in first.splitlines())
    password = values["GOLDCOAST_DB_PASSWORD"]
    assert len(password) == 64 and all(char in "0123456789abcdef" for char in password)
    assert values["GOLDCOAST_OIDC_ISSUER"].endswith("us-east-1_RF0izaP9U")
    assert values["GEMINI_API_KEY"] == values["TAVILY_API_KEY"] == ""
    assert values["telegram_token"] == ""
    module.main()
    assert (tmp_path / ".env").read_text() == first
    assert password not in capsys.readouterr().out


def test_bundle_excludes_local_secrets_and_preserves_replay_bytes(tmp_path, monkeypatch):
    module = load_script("bundle")
    files = {
        "pyproject.toml": b"project",
        ".dockerignore": b"**",
        "src/app.py": b"app",
        "data/studio_demo/manifest.json": b"hashed\r\nbytes",
        "infra/lightsail/compose.yaml": b"services: {}",
        "infra/lightsail/.env": b"private-hosted-secret",
        ".env": b"private-local-secret",
        "output/private.json": b"private-recording",
    }
    for name, raw in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    monkeypatch.setattr(
        module.subprocess, "check_output", lambda *args, **kwargs: "\0".join(files).encode()
    )
    target = tmp_path / "bundle.tar.gz"
    module.bundle(tmp_path, target)
    with tarfile.open(target) as archive:
        assert set(archive.getnames()) == {
            "Goldcoast/" + name
            for name in files
            if name not in {"infra/lightsail/.env", ".env", "output/private.json"}
        }
        assert archive.extractfile("Goldcoast/data/studio_demo/manifest.json").read() == (
            b"hashed\r\nbytes"
        )
