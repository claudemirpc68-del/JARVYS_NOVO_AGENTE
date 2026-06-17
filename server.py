"""
JARVIS 2.0 - Servidor Simplificado
Servidor FastAPI que não bloqueia na inicialização
"""

import os
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import FastAPI
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel
import httpx
from config import config

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Models
class EmailRequest(BaseModel):
    query: str
    user_id: str

class TelegramCommand(BaseModel):
    chat_id: str
    text: str

# FastAPI App
app = FastAPI(title="JARVIS 2.0")

# Carregar config do .env
def load_env():
    env_path = Path(".env")
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()

load_env()

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
GOOGLE_CREDS = Path("credentials.json")
GOOGLE_TOKEN = Path("token.json")

# Gmail service (lazy init)
gmail_service = None

def get_gmail_service():
    global gmail_service
    if gmail_service is not None:
        return gmail_service
    
    if not GOOGLE_TOKEN.exists():
        return None
    
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        
        creds = Credentials.from_authorized_user_file(str(GOOGLE_TOKEN), config.google.scopes)
        
        gmail_service = build('gmail', 'v1', credentials=creds)
        logger.info("Gmail conectado!")
        return gmail_service
    except Exception as e:
        logger.warning(f"Gmail error: {e}")
        return None

# Groq AI
async def groq_chat(query: str) -> Dict:
    system_prompt = f"""Voce e um assistente de email do JARVIS 2.0. Analise a mensagem do usuario e responda em JSON.

Se o usuario quer ENVIAR email mas faltam dados (destinatario, assunto ou corpo), responda SEMPRE com:
{{
    "action": "ask_missing",
    "response": "Para enviar o email, preciso de:\\n- Para quem? (email)\\n- Assunto?\\n- Mensagem?"
}}

Se o usuario forneceu TODOS os dados, responda com:
{{
    "action": "sendEmail",
    "parameters": {{"to": "email@exemplo.com", "subject": "assunto", "body": "corpo do email"}},
    "response": "Enviando email..."
}}

Se o usuario quer VER emails:
{{
    "action": "getEmails",
    "parameters": {{"limit": 5}},
    "response": "Buscando seus emails..."
}}

Se e uma PERGUNTA geral (saudacao, duvida, etc):
{{
    "action": "chat",
    "response": "sua resposta"
}}

Data atual: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

IMPORTANTE: Responda SEMPRE em JSON, sem texto antes ou depois."""

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json={"model": "llama-3.3-70b-versatile", "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ], "temperature": 0.7}
        )
        
        if resp.status_code == 200:
            content = resp.json()["choices"][0]["message"]["content"]
            # Try to extract JSON from response (handle markdown code blocks)
            try:
                # Remove markdown code blocks if present
                if "```" in content:
                    # Extract JSON from between code blocks
                    import re
                    json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', content, re.DOTALL)
                    if json_match:
                        content = json_match.group(1)
                return json.loads(content)
            except:
                return {"action": "error", "response": content}
        else:
            return {"action": "error", "response": f"Erro Groq: {resp.status_code}"}

# Gmail actions
def send_email(params: Dict) -> str:
    svc = get_gmail_service()
    if not svc:
        return "Gmail não autenticado. Acesse /api/gmail/auth-url"
    
    import base64
    to = params.get('to') or params.get('emailAddress', '')
    subject = params.get('subject', '')
    body = params.get('body') or params.get('emailBody', '')
    
    message = f"From: me\nTo: {to}\nSubject: {subject}\nContent-Type: text/html; charset=UTF-8\n\n{body}"
    raw = base64.urlsafe_b64encode(message.encode()).decode()
    
    result = svc.users().messages().send(userId="me", body={"raw": raw}).execute()
    return f"Email enviado para {to}! ID: {result['id']}"

def get_emails(params: Dict) -> str:
    svc = get_gmail_service()
    if not svc:
        return "Gmail não autenticado"
    
    results = svc.users().messages().list(userId="me", maxResults=params.get("limit", 5)).execute()
    msgs = results.get("messages", [])
    return f"Encontrados {len(msgs)} emails" if msgs else "Nenhum email encontrado"

# API Endpoints
@app.get("/")
async def root():
    return HTMLResponse("<h1>JARVIS 2.0</h1><p><a href='/docs'>API Docs</a></p>")

@app.get("/api/status")
async def status():
    return {
        "status": "running",
        "groq": "configured" if GROQ_API_KEY else "missing",
        "gmail": "connected" if get_gmail_service() else "not authenticated",
        "telegram": "configured" if TELEGRAM_TOKEN else "missing"
    }

@app.post("/api/chat")
async def chat(request: EmailRequest):
    result = await groq_chat(request.query)
    action = result.get("action", "error")
    params = result.get("parameters", {})
    
    if action == "sendEmail":
        response = send_email(params)
    elif action == "getEmails":
        response = get_emails(params)
    elif action == "ask_missing":
        response = result.get("response", "Preciso de mais informações.")
    elif action == "chat":
        response = result.get("response", "Como posso ajudar?")
    else:
        response = result.get("response", "Ação não reconhecida.")
    
    return {"response": response}

@app.get("/api/gmail/auth-url")
async def gmail_auth_url():
    if not GOOGLE_CREDS.exists():
        return JSONResponse(status_code=500, content={"error": "credentials.json não encontrado"})
    
    from google_auth_oauthlib.flow import Flow
    
    flow = Flow.from_client_secrets_file(
        str(GOOGLE_CREDS),
        scopes=config.google.scopes,
        redirect_uri="http://localhost:8000/api/gmail/callback"
    )
    
    auth_url, _ = flow.authorization_url(access_type='offline', prompt='consent')
    
    # Salvar state do flow
    Path("/tmp/gmail_flow.json").write_text(json.dumps({
        "client_id": flow.client_config["client_id"],
        "client_secret": flow.client_config["client_secret"],
        "auth_uri": flow.client_config["auth_uri"],
        "token_uri": flow.client_config["token_uri"],
        "redirect_uris": [flow.redirect_uri]
    }))
    
    return {"auth_url": auth_url}

@app.get("/api/gmail/callback")
async def gmail_callback(code: str = None, state: str = None):
    if not code:
        return JSONResponse(status_code=400, content={"error": "Código não fornecido"})
    
    try:
        flow_file = Path("/tmp/gmail_flow.json")
        if not flow_file.exists():
            return JSONResponse(status_code=500, content={"error": "Flow não encontrado"})
        
        flow_data = json.loads(flow_file.read_text())
        
        from google_auth_oauthlib.flow import Flow
        
        flow = Flow.from_client_config(
            {"web": flow_data},
            scopes=config.google.scopes,
            redirect_uri="http://localhost:8000/api/gmail/callback"
        )
        
        flow.fetch_token(code=code)
        
        with open(GOOGLE_TOKEN, 'w') as f:
            f.write(flow.credentials.to_json())
        
        # Reset gmail_service to force reconnect
        global gmail_service
        gmail_service = None
        get_gmail_service()
        
        return {"status": "success", "message": "Gmail autenticado!"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)