import os
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from config import config
from harness.orchestrator import JarvisOrchestrator

# Configuração básica de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Models Pydantic
class EmailRequest(BaseModel):
    query: str
    user_id: str

class TelegramCommand(BaseModel):
    chat_id: str
    text: str

# Inicialização FastAPI e Orquestrador
app = FastAPI(title="JARVIS 2.0 - Backend & OAuth Server")
orchestrator = JarvisOrchestrator()

# Endpoints OAuth2 do Google
@app.get("/api/gmail/auth-url")
async def get_gmail_auth_url():
    """Obter URL de autenticação do Google"""
    try:
        import tempfile
        flow = Flow.from_client_secrets_file(
            config.google.credentials_path,
            config.google.scopes,
            redirect_uri=f"http://localhost:{config.server.port}"
        )
        
        auth_url, state = flow.authorization_url(
            access_type='offline',
            prompt='consent'
        )
        
        # Salvar state para validação
        state_file = Path(tempfile.gettempdir()) / "gmail_state.txt"
        state_file.write_text(state)
        
        # Salvar flow JSON e code_verifier para usar no callback
        flow_data = json.loads(Path(config.google.credentials_path).read_text())
        flow_file = Path(tempfile.gettempdir()) / "gmail_flow.json"
        
        # Incluir code_verifier no arquivo salvo (necessário para PKCE)
        flow_state = {
            "flow_data": flow_data,
            "code_verifier": flow.code_verifier
        }
        flow_file.write_text(json.dumps(flow_state))
        
        return RedirectResponse(url=auth_url)
        
    except Exception as e:
        logger.error(f"Erro ao gerar URL do Google OAuth: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/gmail/callback")
async def gmail_callback(code: str = None, state: str = None):
    return await _handle_gmail_oauth(code)

@app.get("/")
async def root_callback(code: str = None, state: str = None):
    """Callback raiz OAuth do Google (redirect_uri cadastrado no Google Cloud)"""
    if code:
        return await _handle_gmail_oauth(code)
    return {"message": "JARVIS 2.0 - API de Email e Orquestração Inteligente. Use /docs para ver os endpoints."}

async def _handle_gmail_oauth(code: str):
    """Lógica de troca do código OAuth pelo token e salvamento do token.json"""
    if not code:
        return JSONResponse(status_code=400, content={"error": "Código não fornecido"})
    
    try:
        import tempfile
        # Recuperar dados do flow
        flow_file = Path(tempfile.gettempdir()) / "gmail_flow.json"
        if not flow_file.exists():
            return JSONResponse(status_code=500, content={"error": "Flow não encontrado. Gere a URL de auth novamente."})
        
        flow_state = json.loads(flow_file.read_text())
        flow_data = flow_state["flow_data"]
        code_verifier = flow_state.get("code_verifier")
        
        # Criar flow com os dados salvos
        flow = Flow.from_client_config(
            flow_data,
            config.google.scopes,
            redirect_uri=f"http://localhost:{config.server.port}"
        )
        
        # Trocar código pelo token
        fetch_kwargs = {"code": code}
        if code_verifier:
            fetch_kwargs["code_verifier"] = code_verifier
        
        flow.fetch_token(**fetch_kwargs)
        creds = flow.credentials
        
        # Salvar token persistente
        with open(config.google.token_path, 'w') as token:
            token.write(creds.to_json())
            
        logger.info("Google OAuth autenticado com sucesso e token.json atualizado.")
        return {"status": "✅ Sucesso!", "message": "Gmail/Calendário autenticado com sucesso! O JARVIS já pode gerenciar seus serviços."}
        
    except Exception as e:
        logger.error(f"Erro no callback OAuth: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

# Endpoints FastAPI para comandos
@app.post("/api/email-command")
async def process_email_command(request: EmailRequest):
    """Processar comando de email via API"""
    try:
        result = await orchestrator.process(int(request.user_id), request.query)
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Erro no process_email_command: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/telegram-command")
async def process_telegram_command(request: TelegramCommand):
    """Processar comando via Telegram API"""
    try:
        result = await orchestrator.process(int(request.chat_id), request.text)
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Erro no process_telegram_command: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/status")
async def get_status():
    """Status do sistema"""
    from tools.gmail_tool import get_gmail_service
    gmail_ok = "authenticated" if get_gmail_service() else "not_authenticated"
    return {
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "google_api": gmail_ok,
            "groq_ia": "connected",
            "telegram_bot": "configured"
        }
    }

# Inicialização
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.server.host, port=config.server.port)