import os
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel
import httpx
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import asyncio
import aiofiles
from config import config

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

# Inicialização FastAPI
app = FastAPI(title="JARVIS 2.0 - Email Automation")

# Serviços
class EmailService:
    def __init__(self):
        self.gmail_service = None
        self.creds = None
        self.try_load_token()
    
    def try_load_token(self):
        """Tentar carregar token existente"""
        try:
            token_path = Path(config.google.token_path)
            if not token_path.exists():
                logger.info("Gmail: token não encontrado. Use /api/gmail/auth para autenticar.")
                return
            
            from google.oauth2.credentials import Credentials
            creds = Credentials.from_authorized_user_file(str(token_path), config.google.scopes)
            
            if creds.expired and creds.refresh_token:
                from google.auth.transport.requests import Request
                creds.refresh(Request())
                with open(config.google.token_path, 'w') as token:
                    token.write(creds.to_json())
            
            self.creds = creds
            self.gmail_service = build('gmail', 'v1', credentials=creds)
            logger.info("Gmail autenticado com token existente")
            
        except Exception as e:
            logger.warning(f"Gmail token inválido: {e}")
    
    def authenticate_with_code(self, code: str):
        """Autenticar com código OAuth"""
        try:
            from google_auth_oauthlib.flow import InstalledAppFlow
            flow = InstalledAppFlow.from_client_secrets_file(
                config.google.credentials_path, 
                config.google.scopes
            )
            
            flow.fetch_token(code=code)
            creds = flow.credentials
            
            with open(config.google.token_path, 'w') as token:
                token.write(creds.to_json())
            
            self.creds = creds
            self.gmail_service = build('gmail', 'v1', credentials=creds)
            logger.info("Gmail autenticado com sucesso")
            return True
            
        except Exception as e:
            logger.error(f"Erro na autenticação Gmail: {e}")
            return False

class ContactsService:
    def __init__(self, email_service: EmailService):
        self.email_service = email_service
        self._people_service = None

    @property
    def people_service(self):
        if self._people_service:
            return self._people_service
        if self.email_service.creds:
            try:
                self._people_service = build('people', 'v1', credentials=self.email_service.creds)
                logger.info("Serviço Google People (Contatos) inicializado")
            except Exception as e:
                logger.error(f"Erro ao inicializar People API: {e}")
        return self._people_service

    def search_contacts(self, query: str) -> list:
        """Busca contatos por nome na agenda"""
        if not self.people_service:
            logger.warning("Serviço Google Contacts não disponível")
            return []
        try:
            results = self.people_service.people().searchContacts(
                query=query,
                readMask="names,emailAddresses"
            ).execute()
            
            contacts = []
            for result in results.get('results', []):
                person = result.get('person', {})
                names = person.get('names', [])
                emails = person.get('emailAddresses', [])
                
                name = names[0].get('displayName', 'Sem Nome') if names else 'Sem Nome'
                email = emails[0].get('value', '') if emails else ''
                
                if email:
                    contacts.append({"name": name, "email": email})
            return contacts
        except Exception as e:
            logger.error(f"Erro ao buscar contatos para '{query}': {e}")
            return []

class AIService:
    def __init__(self):
        self.client = httpx.AsyncClient(
            base_url="https://api.groq.com/openai/v1",
            headers={
                "Authorization": f"Bearer {config.api.groq_api_key}",
                "Content-Type": "application/json"
            },
            timeout=30.0
        )
    
    async def process_command(self, query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Processa comando usando Groq API"""
        try:
            system_prompt = self._get_system_prompt()
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ]
            
            if context:
                messages.insert(1, {"role": "system", "content": f"Contexto: {json.dumps(context, indent=2)}"})
            
            response = await self.client.post(
                "/chat/completions",
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": messages,
                    "temperature": 0.7,
                    "response_format": {"type": "json_object"}
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                logger.info(f"Resposta bruta da IA: {content}")
                # Remover possíveis formatações markdown (```json ... ```)
                content = content.replace("```json", "").replace("```", "").strip()
                return json.loads(content)
            else:
                logger.error(f"Erro Groq: {response.status_code} - {response.text}")
                return {"error": "Erro ao processar comando com Groq", "action": "error"}
            
        except Exception as e:
            import traceback
            logger.error(f"Erro no processamento IA: {e}\n{traceback.format_exc()}")
            return {"error": "Erro ao processar comando", "action": "error"}

    def _get_system_prompt(self) -> str:
        """Define o prompt do sistema para email management"""
        return f"""# Visão Geral
Você é o JARVIS 2.0, o assistente pessoal de gerenciamento de e-mails e contatos do usuário.
O nome do usuário é Claudemir Pedroso Cubas, e o e-mail padrão dele é claudemirpc68@gmail.com.
Todos os e-mails devem ser formatados profissionalmente em HTML. IMPORTANTE: Não adicione NENHUMA assinatura ao final do e-mail (como "Atenciosamente..."), pois o sistema já anexa a assinatura oficial de Claudemir Pedroso Cubas automaticamente.

**Ferramentas e Parâmetros Exigidos**  
- **"sendEmail"**: Envia um e-mail. Exige: `emailAddress` (destinatário, que pode ser um e-mail ou apenas o nome do contato se estiver cadastrado na agenda), `subject` (assunto), `emailBody` (corpo).
- **"createDraft"**: Cria um rascunho. Exige: `emailAddress`, `subject`, `emailBody`.
- **"getEmails"**: Busca e-mails. Parâmetros opcionais: `sender` (remetente), `limit` (limite numérico).
- **"replyEmail"**: Responde um e-mail. Exige: `messageId`, `emailBody`. Opcional: `subject`.
- **"searchContact"**: Busca um contato na agenda do Google Contatos. Exige: `contactName` (nome ou termo de busca do contato).
- **"chat"**: Usa essa ação apenas para responder saudações (ex: "oi", "olá"), responder a dúvidas gerais do usuário sobre o sistema, suas credenciais (como seu e-mail ou nome) ou bate-papo geral, sem enviar e-mail nem buscar contatos.

## Regras de Resposta
- SEMPRE responda única e exclusivamente em formato JSON válido. Não adicione texto fora do JSON.
- Sempre inicie a sua mensagem no campo `"response"` com uma saudação amigável personalizada para o Claudemir (ex: "Olá, Claudemir!", "Oi, Claudemir, tudo bem?").
- Se o usuário pedir para buscar um contato, saber o e-mail de alguém ou listar contatos, use a ação "searchContact".

Responda em JSON EXATAMENTE com esta estrutura, respeitando os nomes em inglês das chaves de parâmetros (deixe os parâmetros vazios se a ação for 'chat'):
{{
    "action": "chat",
    "parameters": {{}},
    "response": "Olá, Claudemir! Mensagem de resposta humanizada e amigável para o usuário no Telegram."
}}"""

class JarvisService:
    def __init__(self):
        self.email_service = EmailService()
        self.contacts_service = ContactsService(self.email_service)
        self.ai_service = AIService()
    
    async def execute_command(self, query: str, user_id: str) -> Dict[str, Any]:
        """Executa comando completo do JARVIS"""
        try:
            # Processar com IA
            ai_response = await self.ai_service.process_command(query)
            
            if ai_response.get("error"):
                return ai_response
            
            # Executar ação
            action = ai_response.get("action")
            response = ai_response.get("response", "")
            
            if action == "sendEmail":
                result = self._send_email(ai_response.get("parameters", {}))
                if isinstance(result, dict):
                    if result.get("success"):
                        response = result["message"]
                    else:
                        response = result.get("message", f"Falha ao enviar email. Erro: {result.get('error')}")
                else:
                    response = f"Email enviado com sucesso! {result}" if result else "Falha ao enviar email."
            
            elif action == "createDraft":
                result = self._create_draft(ai_response.get("parameters", {}))
                if isinstance(result, dict):
                    if result.get("success"):
                        response = result["message"]
                    else:
                        response = result.get("message", f"Falha ao criar rascunho. Erro: {result.get('error')}")
                else:
                    response = f"Rascunho criado com sucesso! {result}" if result else "Falha ao criar rascunho."
            
            elif action == "getEmails":
                emails = self._get_emails(ai_response.get("parameters", {}))
                if emails:
                    lista_emails = "\n\n".join(emails)
                    response += f"\n\n📋 **Aqui estão os e-mails encontrados:**\n\n{lista_emails}"
                else:
                    response += "\n\nNenhum e-mail encontrado com esses critérios."
            
            elif action == "replyEmail":
                result = self._reply_email(ai_response.get("parameters", {}))
                # Mantém a resposta amigável gerada pela IA, apenas acrescentando status de falha se houver
                if not result:
                    response += "\n\n❌ Ops, houve uma falha ao tentar enviar/responder o e-mail."
            
            elif action == "searchContact":
                contact_name = ai_response.get("parameters", {}).get("contactName", "")
                contacts = self.contacts_service.search_contacts(contact_name)
                if contacts:
                    options = []
                    for c in contacts:
                        options.append(f"• **{c['name']}**: {c['email']}")
                    response = f"Olá, Claudemir! Encontrei os seguintes contatos para '{contact_name}':\n\n" + "\n".join(options)
                else:
                    response = f"Olá, Claudemir! Não encontrei nenhum contato com o nome '{contact_name}' no seu Google Contatos."
            
            elif action == "chat":
                # O campo response já terá a saudação amigável
                pass
                
            else:
                response = "Ação não reconhecida. Por favor, tente novamente."
            
            return {"success": True, "response": response}
            
        except Exception as e:
            logger.error(f"Erro ao executar comando: {e}")
            return {"success": False, "error": str(e)}
    
    def _resolve_email_address(self, email_or_name: str) -> Dict[str, Any]:
        """
        Verifica se o destinatário é um e-mail. Se não for, busca no Google Contatos.
        """
        email_or_name = email_or_name.strip()
        if "@" in email_or_name:
            return {"email": email_or_name, "status": "direct"}
        
        logger.info(f"Resolvendo nome '{email_or_name}' via Google Contatos...")
        contacts = self.contacts_service.search_contacts(email_or_name)
        
        if not contacts:
            return {
                "email": None,
                "status": "not_found",
                "message": f"Não encontrei nenhum contato com o nome '{email_or_name}' na sua agenda do Google Contatos."
            }
        
        if len(contacts) == 1:
            resolved_email = contacts[0]["email"]
            resolved_name = contacts[0]["name"]
            logger.info(f"Contato resolvido: {resolved_name} <{resolved_email}>")
            return {
                "email": resolved_email,
                "status": "resolved",
                "name": resolved_name
            }
        
        # Múltiplos contatos encontrados
        options = []
        for c in contacts:
            options.append(f"• **{c['name']}** ({c['email']})")
        options_text = "\n".join(options)
        
        return {
            "email": None,
            "status": "ambiguous",
            "message": f"Olá, Claudemir! Encontrei mais de um contato para '{email_or_name}':\n\n{options_text}\n\nPor favor, repita o comando especificando o e-mail ou o nome completo."
        }

    def _send_email(self, params: Dict) -> Dict[str, Any]:
        """Enviar email via Gmail"""
        if not self.email_service.gmail_service:
            return {"success": False, "error": "Gmail não configurado. Configure credentials.json para usar email."}
        try:
            dest = params.get("emailAddress", "")
            resolution = self._resolve_email_address(dest)
            
            if resolution["status"] in ["not_found", "ambiguous"]:
                return {"success": False, "message": resolution["message"]}
            
            to_email = resolution["email"]
            
            message = self._create_message(
                to=to_email,
                subject=params.get("subject", ""),
                body=params.get("emailBody", "")
            )
            
            send_message = (self.email_service.gmail_service.users().messages()
                          .send(userId="me", body=message)
                          .execute())
            
            msg_id = send_message['id']
            confirm_msg = f"Email enviado com sucesso para **{to_email}**!"
            if resolution["status"] == "resolved":
                confirm_msg = f"Email enviado com sucesso para **{resolution['name']}** ({to_email})!"
                
            return {"success": True, "message": confirm_msg, "id": msg_id}
            
        except Exception as e:
            logger.error(f"Erro ao enviar email: {e}")
            return {"success": False, "error": str(e)}
    
    def _create_draft(self, params: Dict) -> Dict[str, Any]:
        """Criar rascunho de email"""
        if not self.email_service.gmail_service:
            return {"success": False, "error": "Gmail não configurado. Configure credentials.json para usar email."}
        try:
            dest = params.get("emailAddress", "")
            resolution = self._resolve_email_address(dest)
            
            if resolution["status"] in ["not_found", "ambiguous"]:
                return {"success": False, "message": resolution["message"]}
            
            to_email = resolution["email"]
            
            message = self._create_message(
                to=to_email,
                subject=params.get("subject", ""),
                body=params.get("emailBody", ""),
                draft=True
            )
            
            draft = (self.email_service.gmail_service.users().drafts()
                    .create(userId="me", body=message)
                    .execute())
            
            draft_id = draft['id']
            confirm_msg = f"Rascunho criado com sucesso para **{to_email}**!"
            if resolution["status"] == "resolved":
                confirm_msg = f"Rascunho criado com sucesso para **{resolution['name']}** ({to_email})!"
                
            return {"success": True, "message": confirm_msg, "id": draft_id}
            
        except Exception as e:
            logger.error(f"Erro ao criar rascunho: {e}")
            return {"success": False, "error": str(e)}
    
    def _get_emails(self, params: Dict) -> list:
        """Buscar emails"""
        if not self.email_service.gmail_service:
            return ["Gmail não configurado"]
        try:
            query = f"from:{params.get('sender', '')}" if params.get('sender') else ""
            try:
                limit = int(params.get('limit', 5))
            except (ValueError, TypeError):
                limit = 5
            
            results = (self.email_service.gmail_service.users().messages()
                      .list(userId="me", q=query, maxResults=limit)
                      .execute())
            
            emails = results.get('messages', [])
            if not emails:
                return []
                
            email_details = []
            for email in emails[:limit]:
                msg = self.email_service.gmail_service.users().messages().get(
                    userId="me", id=email['id'], format='metadata', 
                    metadataHeaders=['Subject', 'From']
                ).execute()
                
                headers = msg.get('payload', {}).get('headers', [])
                subject = "Sem Assunto"
                sender = "Desconhecido"
                
                for header in headers:
                    if header['name'].lower() == 'subject':
                        subject = header['value']
                    elif header['name'].lower() == 'from':
                        sender = header['value']
                
                snippet = msg.get('snippet', '')
                email_details.append(f"📧 **De:** {sender}\n📌 **Assunto:** {subject}\n📝 **Resumo:** {snippet}...")
                
            return email_details
            
        except Exception as e:
            logger.error(f"Erro ao buscar emails: {e}")
            return []
    
    def _reply_email(self, params: Dict) -> Optional[str]:
        """Responder email"""
        if not self.email_service.gmail_service:
            return "Gmail não configurado. Configure credentials.json para usar email."
        try:
            message_id = params.get("messageId", "")
            body = params.get("emailBody", "")
            
            message = self._create_message(
                to="",  # Gmail preenche automaticamente
                subject=f"Re: {params.get('subject', '')}",
                body=body,
                thread_id=message_id
            )
            
            send_message = (self.email_service.gmail_service.users().messages()
                          .send(userId="me", body=message)
                          .execute())
            
            return f"ID: {send_message['id']}"
            
        except Exception as e:
            logger.error(f"Erro ao responder email: {e}")
            return None
    
    def _create_message(self, to: str, subject: str, body: str, draft: bool = False, thread_id: str = None) -> Dict:
        """Criar mensagem formatada em HTML"""
        message = {
            'raw': self._build_mime_message(to, subject, body)
        }
        
        if thread_id:
            message['threadId'] = thread_id
        
        if draft:
            return {'message': message}
        
        return message
    
    def _build_mime_message(self, to: str, subject: str, body: str) -> str:
        """Construir mensagem MIME"""
        import base64
        from email.message import EmailMessage
        
        full_body = f"{body}<br><br><p><em>Atenciosamente,<br>Claudemir Pedroso Cubas</em></p>"
        
        msg = EmailMessage()
        msg.set_content(full_body, subtype='html')
        msg['To'] = to
        msg['From'] = 'me'
        msg['Subject'] = subject
        
        return base64.urlsafe_b64encode(msg.as_bytes()).decode('utf-8')

# Inicializar serviços
jarvis_service = JarvisService()

# Endpoints Gmail Auth
@app.get("/api/gmail/auth-url")
async def get_gmail_auth_url():
    """Obter URL de autenticação do Gmail"""
    try:
        import tempfile
        from google_auth_oauthlib.flow import Flow
        
        flow = Flow.from_client_secrets_file(
            config.google.credentials_path,
            config.google.scopes,
            redirect_uri="http://localhost:8000"
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
            "code_verifier": flow.code_verifier  # None se PKCE não estiver ativo
        }
        flow_file.write_text(json.dumps(flow_state))
        
        return RedirectResponse(url=auth_url)
        
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})



@app.get("/api/gmail/callback")
async def gmail_callback(code: str = None, state: str = None):
    return await _handle_gmail_oauth(code)

@app.get("/")
async def root_callback(code: str = None, state: str = None):
    """Callback raiz OAuth do Gmail (redirect_uri cadastrado no Google Cloud)"""
    if code:
        return await _handle_gmail_oauth(code)
    return {"message": "JARVIS 2.0 - API de Email Inteligente. Use /docs para ver os endpoints."}

async def _handle_gmail_oauth(code: str):
    """Lógica de troca do código OAuth pelo token"""
    if not code:
        return JSONResponse(status_code=400, content={"error": "Código não fornecido"})
    
    try:
        import tempfile
        from google_auth_oauthlib.flow import Flow
        
        # Recuperar dados do flow (agora inclui code_verifier)
        flow_file = Path(tempfile.gettempdir()) / "gmail_flow.json"
        if not flow_file.exists():
            return JSONResponse(status_code=500, content={"error": "Flow não encontrado. Gere a URL de auth novamente."})
        
        flow_state = json.loads(flow_file.read_text())
        
        # Suporte ao novo formato (com code_verifier) e formato antigo
        if "flow_data" in flow_state:
            flow_data = flow_state["flow_data"]
            code_verifier = flow_state.get("code_verifier")
        else:
            flow_data = flow_state
            code_verifier = None
        
        # Criar flow com os dados salvos
        flow = Flow.from_client_config(
            flow_data,
            config.google.scopes,
            redirect_uri="http://localhost:8000"
        )
        
        # Trocar código pelo token, passando o code_verifier se existir (PKCE)
        fetch_kwargs = {"code": code}
        if code_verifier:
            fetch_kwargs["code_verifier"] = code_verifier
        
        flow.fetch_token(**fetch_kwargs)
        creds = flow.credentials
        
        # Salvar token
        with open(config.google.token_path, 'w') as token:
            token.write(creds.to_json())
        
        # Ativar serviço
        jarvis_service.email_service.creds = creds
        jarvis_service.email_service.gmail_service = build('gmail', 'v1', credentials=creds)
        
        return {"status": "✅ Sucesso!", "message": "Gmail autenticado com sucesso! O JARVIS já pode gerenciar seus emails."}
        
    except Exception as e:
        logger.error(f"Erro no callback OAuth: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})





# Endpoints FastAPI
@app.post("/api/email-command")
async def process_email_command(request: EmailRequest):
    """Processar comando de email"""
    result = await jarvis_service.execute_command(request.query, request.user_id)
    return JSONResponse(content=result)

@app.post("/api/telegram-command")
async def process_telegram_command(request: TelegramCommand):
    """Processar comando via Telegram"""
    result = await jarvis_service.execute_command(request.text, request.chat_id)
    return JSONResponse(content=result)

@app.get("/api/status")
async def get_status():
    """Status do sistema"""
    return {
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "gmail": "authenticated" if jarvis_service.email_service.gmail_service else "error",
            "openai": "connected",
            "telegram": "configured"
        }
    }

# Inicialização
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)