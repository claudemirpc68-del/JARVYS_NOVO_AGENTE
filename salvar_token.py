from pathlib import Path
import sys

code = input("Cole o CODIGO da URL (depois de ?code=): ").strip()

if not code:
    print("Codigo vazio!")
    sys.exit(1)

from google_auth_oauthlib.flow import Flow

SCOPES = ['https://www.googleapis.com/auth/gmail.send', 'https://www.googleapis.com/auth/gmail.modify', 'https://www.googleapis.com/auth/gmail.compose']

flow = Flow.from_client_secrets_file(
    str(Path(__file__).parent / "credentials.json"),
    SCOPES,
    redirect_uri="http://localhost:8000"
)

flow.fetch_token(code=code)
Path(__file__).parent.joinpath("token.json").write_text(flow.credentials.to_json())
print("GMAIL AUTENTICADO COM SUCESSO!")