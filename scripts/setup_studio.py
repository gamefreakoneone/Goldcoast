import re
import secrets
from pathlib import Path

from dotenv import dotenv_values


def main():
    path = Path(".env")
    if not path.exists():
        path.write_text(Path(".env.example").read_text())
    content = path.read_text()
    values = dotenv_values(path)
    for key in (
        "GOLDCOAST_DB_PASSWORD",
        "GOLDCOAST_KEYCLOAK_ADMIN_PASSWORD",
        "GOLDCOAST_LOCAL_OWNER_PASSWORD",
        "GOLDCOAST_LOCAL_DEMO_PASSWORD",
    ):
        if values.get(key):
            continue
        line = key + "=" + secrets.token_urlsafe(24)
        pattern = re.compile(r"^" + re.escape(key) + r"=.*$", re.MULTILINE)
        content = (
            pattern.sub(line, content)
            if pattern.search(content)
            else content.rstrip() + "\n" + line + "\n"
        )
    path.write_text(content)
    print("Local studio credentials are configured in .env. Existing values were preserved.")


if __name__ == "__main__":
    main()
