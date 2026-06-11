"""
JARVIS 2.0 - Bot Telegram Autônomo
Não precisa de servidor local. Tudo em um só arquivo.
"""

import os
import json
import logging
import httpx
from pathlib import Path
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Config
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_env():
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()

load_env()

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

# Gmail
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
import base64

GOOGLE_CREDS = Path(__file__).parent / "credentials.json"
GOOGLE_TOKEN = Path(__file__).parent / "token.json"
SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/gmail.compose',
    'https://www.googleapis.com/auth/contacts.readonly'
]

gmail_service = None
people_service = None

def get_creds():
    if not GOOGLE_TOKEN.exists():
        return None
    try:
        creds = Credentials.from_authorized_user_file(str(GOOGLE_TOKEN), SCOPES)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            GOOGLE_TOKEN.write_text(creds.to_json())
        return creds
    except:
        return None

def get_gmail():
    global gmail_service
    if gmail_service:
        return gmail_service
    creds = get_creds()
    if not creds:
        return None
    try:
        gmail_service = build('gmail', 'v1', credentials=creds)
        return gmail_service
    except:
        return None

def get_people():
    global people_service
    if people_service:
        return people_service
    creds = get_creds()
    if not creds:
        return None
    try:
        people_service = build('people', 'v1', credentials=creds)
        return people_service
    except:
        return None

def search_contacts(query):
    svc = get_people()
    if not svc:
        return [], "Google Contacts nao autenticado."
    try:
        results = svc.people().searchContacts(query=query, readMask="names,emailAddresses").execute()
        contacts = []
        for result in results.get('results', []):
            person = result.get('person', {})
            names = person.get('names', [])
            emails = person.get('emailAddresses', [])
            name = names[0].get('displayName', 'Sem Nome') if names else 'Sem Nome'
            email = emails[0].get('value', '') if emails else ''
            if email:
                contacts.append({"name": name, "email": email})
        return contacts, None
    except Exception as e:
        return [], str(e)

def resolve_email_address(email_or_name):
    email_or_name = email_or_name.strip()
    if "@" in email_or_name:
        return email_or_name, None, None
    contacts, err = search_contacts(email_or_name)
    if err:
        return None, None, f"Erro ao buscar contatos: {err}"
    if not contacts:
        return None, None, f"Nao encontrei nenhum contato com o nome '{email_or_name}' no seu Google Contatos."
    if len(contacts) == 1:
        return contacts[0]["email"], contacts[0]["name"], None
    
    options = [f"- {c['name']} ({c['email']})" for c in contacts]
    return None, None, f"Encontrei mais de um contato para '{email_or_name}':\n\n" + "\n".join(options) + "\n\nPor favor especifique o email ou nome completo."

def send_email(to, subject, body):
    svc = get_gmail()
    if not svc:
        return None, "Gmail nao autenticado. Envie /auth para autenticar."
    
    resolved_to, name, err = resolve_email_address(to)
    if err:
        return None, err
        
    msg = f"From: me\nTo: {resolved_to}\nSubject: {subject}\nContent-Type: text/html; charset=UTF-8\n\n{body}"
    raw = base64.urlsafe_b64encode(msg.encode()).decode()
    result = svc.users().messages().send(userId="me", body={"raw": raw}).execute()
    return result['id'], None

def get_emails(limit=5):
    svc = get_gmail()
    if not svc:
        return None, "Gmail nao autenticado. Envie /auth para autenticar."
    results = svc.users().messages().list(userId="me", maxResults=limit).execute()
    msgs = results.get('messages', [])
    emails = []
    for m in msgs:
        msg = svc.users().messages().get(userId="me", id=m['id'], format='metadata', metadataHeaders=['From','Subject','Date']).execute()
        headers = {h['name']: h['value'] for h in msg['payload']['headers']}
        emails.append(f"De: {headers.get('From','?')}\nAssunto: {headers.get('Subject','?')}\nData: {headers.get('Date','?')}")
    return emails, None

# IA
async def groq_chat(query: str) -> dict:
    prompt = f"""Voce e o JARVIS 2.0, assistente de email via Telegram de Claudemir Pedroso Cubas (email padrao: claudemirpc68@gmail.com). Responda SEMPRE em JSON.

Se quer ENVIAR email mas faltam dados:
{{"action":"ask","response":"Olá, Claudemir! Para enviar, preciso de:\\n- Email do destinatario\\n- Assunto\\n- Mensagem\\n\\nExemplo: enviar para fulano@x.com assunto Reuniao oi tudo bem"}}

Se tem TODOS os dados para enviar:
{{"action":"send","to":"email","subject":"assunto","body":"corpo","response":"Enviando..."}}

Se quer VER emails:
{{"action":"list","limit":5,"response":"Buscando seus emails, Claudemir..."}}

Se quer BUSCAR ou saber o email de alguém na agenda do Google Contatos:
{{"action":"contacts","query":"nome_do_contato","response":"Buscando contato..."}}

Se quer AUTENTICAR Gmail:
{{"action":"auth","response":"Acesse para autenticar seu Gmail: {get_auth_url()}"}}

Se e pergunta/saudacao geral (ou perguntas sobre seu nome/email):
{{"action":"chat","response":"sua resposta para Claudemir"}}

Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}"""

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json={"model": "llama-3.3-70b-versatile", "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": query}
            ], "temperature": 0.7},
            timeout=30
        )
        if resp.status_code == 200:
            content = resp.json()["choices"][0]["message"]["content"]
            try:
                if "```" in content:
                    import re
                    m = re.search(r'```(?:json)?\s*(.*?)\s*```', content, re.DOTALL)
                    if m: content = m.group(1)
                return json.loads(content)
            except:
                return {"action": "chat", "response": content}
        return {"action": "chat", "response": "Erro ao processar."}

def get_auth_url():
    if not GOOGLE_CREDS.exists():
        return "Credenciais Google nao encontradas"
    flow = Flow.from_client_secrets_file(str(GOOGLE_CREDS), SCOPES, redirect_uri="http://localhost:8000/api/gmail/callback")
    auth_url, _ = flow.authorization_url(access_type='offline', prompt='consent')
    return auth_url

# Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "JARVIS 2.0 - Assistente de Email\n\n"
        "Envie qualquer mensagem para interagir!\n\n"
        "Comandos:\n"
        "/start - Iniciar\n"
        "/status - Status\n"
        "/auth - Autenticar Gmail\n"
        "/email - Ver emails\n"
        "/ajuda - Ajuda"
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    gmail_ok = "Conectado" if get_gmail() else "Nao autenticado"
    await update.message.reply_text(
        f"Status do Sistema\n\n"
        f"Groq: OK\n"
        f"Gmail: {gmail_ok}\n"
        f"Telegram: OK"
    )

async def auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = get_auth_url()
    await update.message.reply_text(f"Abra este link para autenticar Gmail:\n\n{url}")

async def email_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    emails, err = get_emails(5)
    if err:
        await update.message.reply_text(err)
        return
    if not emails:
        await update.message.reply_text("Nenhum email encontrado.")
        return
    text = "Seus ultimos emails:\n\n" + "\n---\n".join(emails)
    await update.message.reply_text(text[:4000])

async def ajuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Como usar o JARVIS 2.0\n\n"
        "Basta enviar uma mensagem:\n\n"
        "Exemplos:\n"
        "- enviar email para fulano@x.com assunto oi corpo tudo bem\n"
        "- quais sao meus emails\n"
        "- criar rascunho para fulano\n"
        "- responder ao ultimo email\n\n"
        "Comandos:\n"
        "/start - Iniciar\n"
        "/status - Status\n"
        "/auth - Autenticar Gmail\n"
        "/email - Ver emails"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    logger.info(f"Msg: {text}")
    
    result = await groq_chat(text)
    action = result.get("action", "chat")
    
    if action == "send":
        to = result.get("to", "")
        subject = result.get("subject", "")
        body = result.get("body", "")
        msg_id, err = send_email(to, subject, body)
        if err:
            await update.message.reply_text(err)
        else:
            await update.message.reply_text(f"Email enviado para {to}! ID: {msg_id}")
    elif action == "list":
        emails, err = get_emails(result.get("limit", 5))
        if err:
            await update.message.reply_text(err)
        elif not emails:
            await update.message.reply_text("Nenhum email encontrado.")
        else:
            await update.message.reply_text("Seus emails:\n\n" + "\n---\n".join(emails)[:4000])
    elif action == "contacts":
        search_query = result.get("query", "")
        contacts, err = search_contacts(search_query)
        if err:
            await update.message.reply_text(f"Erro ao buscar contatos: {err}")
        elif not contacts:
            await update.message.reply_text(f"Nenhum contato encontrado para '{search_query}'.")
        else:
            options = [f"• **{c['name']}**: {c['email']}" for c in contacts]
            await update.message.reply_text(f"Olá, Claudemir! Encontrei os seguintes contatos para '{search_query}':\n\n" + "\n".join(options))
    elif action == "auth":
        await update.message.reply_text(result.get("response", ""))
    else:
        await update.message.reply_text(result.get("response", "Desculpe, nao entendi."))

def main():
    if not TELEGRAM_TOKEN:
        print("TELEGRAM_TOKEN nao configurado")
        return
    if not GROQ_API_KEY:
        print("GROQ_API_KEY nao configurado")
        return
    
    print("JARVIS 2.0 Bot iniciando...")
    
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("auth", auth))
    app.add_handler(CommandHandler("email", email_cmd))
    app.add_handler(CommandHandler("ajuda", ajuda))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("Bot rodando! Envie mensagem no Telegram.")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()