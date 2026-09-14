import os
import secrets
from pathlib import Path


def main():
    target = Path(__file__).resolve().parent / ".env"
    values = {
        "GOLDCOAST_DOMAIN": "goldcoast-amogh.duckdns.org",
        "GOLDCOAST_OIDC_ISSUER": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_RF0izaP9U",
        "GOLDCOAST_OIDC_CLIENT_ID": "64q06mij5rqu8t993q26dgk968",
        "GOLDCOAST_COGNITO_DOMAIN": "https://us-east-1rf0izap9u.auth.us-east-1.amazoncognito.com",
        "GOLDCOAST_DB_PASSWORD": secrets.token_hex(32),
        "GEMINI_API_KEY": "",
        "TAVILY_API_KEY": "",
        "TICKETMASTER_API_KEY": "",
        "telegram_token": "",
        "telegram_bot_link": "",
    }
    try:
        descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        print("Existing configuration preserved; no passwords changed.")
        return
    with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
        stream.write("".join(f"{key}={value}\n" for key, value in values.items()))
    print("Private configuration created. Live providers and Telegram remain unconfigured.")


if __name__ == "__main__":
    main()
