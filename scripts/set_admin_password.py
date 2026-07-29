"""Set the local Grace admin password hash in .env."""

import base64
import hashlib
import getpass
import secrets
from pathlib import Path


ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


def make_hash(password: str) -> str:
    salt = secrets.token_urlsafe(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000)
    encoded = base64.urlsafe_b64encode(digest).decode()
    return f"pbkdf2_sha256$200000${salt}${encoded}"


def main() -> None:
    password = getpass.getpass("New Grace admin password: ")
    confirmation = getpass.getpass("Confirm password: ")
    if not password:
        raise SystemExit("Password cannot be empty.")
    if password != confirmation:
        raise SystemExit("Passwords do not match.")

    lines = ENV_FILE.read_text(encoding="utf-8").splitlines() if ENV_FILE.exists() else []
    setting = f"GRACE_ADMIN_PASSWORD_HASH={make_hash(password)}"
    replaced = False
    output: list[str] = []
    for line in lines:
        if line.startswith("GRACE_ADMIN_PASSWORD_HASH="):
            output.append(setting)
            replaced = True
        else:
            output.append(line)
    if not replaced:
        if output and output[-1] != "":
            output.append("")
        output.append(setting)
    ENV_FILE.write_text("\n".join(output) + "\n", encoding="utf-8")
    print(f"Updated {ENV_FILE} with a password hash. Restart Grace to apply it.")


if __name__ == "__main__":
    main()
