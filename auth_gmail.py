"""
Autenticador Gmail - Versão simples
1. Rode: python auth_gmail.py
2. Abra o link que aparecer
3. Autorize
4. Copie o CODIGO da URL (depois de ?code=)
5. Cole no terminal
"""

from pathlib import Path
from google_auth_oauthlib.flow import Flow

SCOPES = ['https://www.googleapis.com/auth/gmail.send', 'https://www.googleapis.com/auth/gmail.modify', 'https://www.googleapis.com/auth/gmail.compose']
CREDS = Path(__file__).parent / "credentials.json"
TOKEN = Path(__file__).parent / "token.json"

flow = Flow.from_client_secrets_file(str(CREDS), SCOPES, redirect_uri="http://localhost:8000")
auth_url, _ = flow.authorization_url(access_type='offline', prompt='consent')

print("\n1. ABRA ESTE LINK NO NAVEGADOR:\n")
print(auth_url)
print("\n2. AUTORIZE O ACESSO")
print("3. COPIE O CODIGO DA URL (ex: http://localhost:8000/?code=ABC123... -> copie ABC123)")
print("4. DIGITE O CODIGO ABAIXO\n")

code = input("CODIGO: ").strip()

if code:
    flow.fetch_token(code=code)
    TOKEN.write_text(flow.credentials.to_json())
    print("\nGMAIL AUTENTICADO COM SUCESSO!")
else:
    print("Codigo invalido!")