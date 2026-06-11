"""
Step 1: Gerar URL SEM PKCE
"""

from pathlib import Path
import json
import secrets

CLIENT_ID = "seu-client-id.apps.googleusercontent.com"
CLIENT_SECRET = "seu-client-secret"

state = secrets.token_urlsafe(16)

auth_url = (
    f"https://accounts.google.com/o/oauth2/auth"
    f"?response_type=code"
    f"&client_id={CLIENT_ID}"
    f"&redirect_uri=http%3A%2F%2Flocalhost%3A8000%2F"
    f"&scope=https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fgmail.send+https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fgmail.modify+https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fgmail.compose+https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fcontacts.readonly"
    f"&state={state}"
    f"&access_type=offline"
    f"&prompt=consent"
)

# Salvar para step2
Path("flow_state.json").write_text(json.dumps({
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "state": state
}))

print("\nABRA ESTE LINK NO NAVEGADOR:\n")
print(auth_url)
print("\nAPOS AUTORIZAR, RODE: python step2.py CODIGO_AQUI")