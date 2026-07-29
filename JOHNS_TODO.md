# John's setup tasks

## Admin login

- Set `GRACE_ADMIN_USERNAME` in `.env`.
- Generate and save a PBKDF2 password hash with the helper script (the password is never printed):

```powershell
py -3.11 scripts/set_admin_password.py
```

Alternatively, generate a hash manually without storing the password in the repository:

```powershell
py -3.11 -c "import base64,hashlib,secrets,getpass; p=getpass.getpass(); s=secrets.token_urlsafe(16); h=base64.urlsafe_b64encode(hashlib.pbkdf2_hmac('sha256',p.encode(),s.encode(),200000)).decode(); print(f'pbkdf2_sha256$200000${s}${h}')"
```

- Put the generated value in `.env` as `GRACE_ADMIN_PASSWORD_HASH`.
- Restart Grace after changing `.env`.

The login session is local to the running server and expires after 24 hours. Chat and Grace settings require the admin session; weather and network diagnostics remain available locally without login.
