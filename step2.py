"""
Step 2: Trocar codigo por token
Uso: python step2.py CODIGO_AQUI
"""

import sys
import json
from pathlib import Path
import requests

code = sys.argv[1] if len(sys.argv) > 1 else input("Cole o codigo: ").strip()

flow_data = json.loads(Path("flow_state.json").read_text())

# Trocar codigo por token
data = {
    "code": code,
    "client_id": flow_data["client_id"],
    "client_secret": flow_data["client_secret"],
    "redirect_uri": "http://localhost:8000/",
    "grant_type": "authorization_code"
}

resp = requests.post("https://oauth2.googleapis.com/token", data=data)

if resp.status_code == 200:
    token = resp.json()
    # Salvar token no formato correto
    token_data = {
        "token": token.get("access_token"),
        "refresh_token": token.get("refresh_token"),
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": flow_data["client_id"],
        "client_secret": flow_data["client_secret"],
        "scopes": ["https://www.googleapis.com/auth/gmail.send", "https://www.googleapis.com/auth/gmail.modify", "https://www.googleapis.com/auth/gmail.compose"]
    }
    Path("token.json").write_text(json.dumps(token_data, indent=2))
    print("\nGMAIL AUTENTICADO COM SUCESSO!")
else:
    print(f"\nErro: {resp.status_code} - {resp.text}")