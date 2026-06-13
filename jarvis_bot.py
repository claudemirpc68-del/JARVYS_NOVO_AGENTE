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
    'https://www.googleapis.com/auth/contacts.readonly',
    'https://www.googleapis.com/auth/calendar'
]

gmail_service = None
people_service = None
calendar_service = None

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

def get_calendar():
    global calendar_service
    if calendar_service:
        return calendar_service
    creds = get_creds()
    if not creds:
        return None
    try:
        calendar_service = build('calendar', 'v3', credentials=creds)
        return calendar_service
    except Exception as e:
        logger.error(f"Erro ao inicializar Calendar: {e}")
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

def get_all_contacts():
    svc = get_people()
    if not svc:
        return []
    try:
        results = svc.people().connections().list(
            resourceName='people/me',
            pageSize=250,
            personFields='names,emailAddresses'
        ).execute()
        connections = results.get('connections', [])
        contacts = []
        for person in connections:
            names = person.get('names', [])
            emails = person.get('emailAddresses', [])
            name = names[0].get('displayName', 'Sem Nome') if names else 'Sem Nome'
            email = emails[0].get('value', '') if emails else ''
            if email:
                contacts.append(f"{name} ({email})")
        return contacts
    except Exception as e:
        logger.error(f"Erro ao listar todos os contatos: {e}")
        return []

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
        
    # Adicionar assinatura programática
    signature = os.environ.get("SIGNATURE", "Claudemir Pedroso Cubas")
    signature = signature.replace('"', '').replace("'", "").strip()
    body_with_sig = f"{body}<br><br>---<br><i>{signature}</i>"
        
    msg = f"From: me\nTo: {resolved_to}\nSubject: {subject}\nContent-Type: text/html; charset=UTF-8\n\n{body_with_sig}"
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

def create_event(title, start_iso, end_iso, description="", attendees=None):
    svc = get_calendar()
    if not svc:
        return None, "Google Calendar nao autenticado. Envie /auth para autenticar."
    try:
        event = {
            'summary': title,
            'description': description,
            'start': {
                'dateTime': start_iso,
                'timeZone': 'America/Sao_Paulo',
            },
            'end': {
                'dateTime': end_iso,
                'timeZone': 'America/Sao_Paulo',
            }
        }
        if attendees:
            resolved_attendees = []
            for att in attendees:
                resolved_email, _, _ = resolve_email_address(att)
                if resolved_email:
                    resolved_attendees.append({'email': resolved_email})
                else:
                    resolved_attendees.append({'email': att})
            event['attendees'] = resolved_attendees
            
        created_event = svc.events().insert(calendarId='primary', body=event, sendUpdates='all').execute()
        return created_event, None
    except Exception as e:
        return None, str(e)

def list_events(start_iso=None, end_iso=None, max_results=10):
    svc = get_calendar()
    if not svc:
        return None, "Google Calendar nao autenticado. Envie /auth para autenticar."
    try:
        if not start_iso:
            start_iso = datetime.now().isoformat() + 'Z'
        events_result = svc.events().list(
            calendarId='primary',
            timeMin=start_iso,
            timeMax=end_iso if end_iso else None,
            maxResults=max_results,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        return events_result.get('items', []), None
    except Exception as e:
        return None, str(e)

async def search_web_tavily(query):
    tavily_key = os.environ.get("TAVILY_API_KEY", "")
    if not tavily_key:
        logger.warning("TAVILY_API_KEY nao configurada no .env.")
        return "Erro: TAVILY_API_KEY nao configurada no .env."
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": tavily_key,
                    "query": query,
                    "search_depth": "basic",
                    "max_results": 3
                },
                timeout=15
            )
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])
                if not results:
                    return "Nenhum resultado relevante encontrado na pesquisa web."
                lines = []
                for idx, r in enumerate(results, 1):
                    lines.append(f"{idx}. **{r.get('title')}**\nLink: {r.get('url')}\nConteudo: {r.get('content')}")
                return "\n\n".join(lines)
            else:
                return f"Erro na API do Tavily: Status {resp.status_code}"
    except Exception as e:
        logger.error(f"Erro ao buscar no Tavily: {e}")
        return f"Erro na pesquisa web: {e}"

# Memória de conversação por chat_id
chat_memories = {}

def get_chat_history(chat_id):
    if chat_id not in chat_memories:
        chat_memories[chat_id] = []
    return chat_memories[chat_id]

def add_to_history(chat_id, role, content):
    history = get_chat_history(chat_id)
    history.append({"role": role, "content": content})
    # Manter as últimas 15 mensagens para não estourar o contexto
    if len(history) > 15:
        history.pop(0)

# IA
async def groq_chat(chat_id: int, query: str, save_to_history: bool = True) -> dict:
    # Buscar os contatos para injetar no Prompt do sistema
    contacts_list = get_all_contacts()
    contacts_str = "\n".join(contacts_list) if contacts_list else "Nenhum contato encontrado ou Google Contacts nao autenticado."

    # Dia da semana para ajudar na conversão de datas relativas (ex: amanhã, segunda-feira)
    weekdays = ["segunda-feira", "terca-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sabado", "domingo"]
    today_weekday = weekdays[datetime.now().weekday()]

    prompt = f"""Voce e o JARVIS 2.0, assistente pessoal de Claudemir Pedroso Cubas (email padrao: claudemirpc68@gmail.com). Responda SEMPRE em JSON.

SUA LISTA DE CONTATOS ATUAL (Use para associar nomes a e-mails diretamente):
{contacts_str}

REGRAS DO GOOGLE CALENDAR (CALENDÁRIO):
1. Para criar eventos: Você precisa do título, data/hora de início e fim no formato ISO 8601 (ex: "2026-06-12T15:00:00-03:00"). O fuso horário padrão é America/Sao_Paulo (UTC-3).
2. Se o usuário disser datas relativas (ex: "amanhã", "próxima segunda"), calcule com base na Data Atual abaixo. Lembre que hoje é {today_weekday}.
3. Se o usuário quiser convidar alguém (ex: "marcar reunião com Joelma"), busque o e-mail correspondente na SUA LISTA DE CONTATOS ATUAL e coloque a lista de e-mails em "attendees".
4. Se faltar a duração do compromisso, use 1 hora como padrão.
5. Se quer ver a agenda, filtre pelo período adequado (início e fim em formato ISO 8601).

AÇÕES DE CALENDÁRIO:
- Criar evento:
{{"action":"calendar_create","title":"Reuniao","start":"2026-06-13T15:00:00-03:00","end":"2026-06-13T16:00:00-03:00","description":"detalhes","attendees":["email1@teste.com"],"response":"Criando o evento na sua agenda..."}}
- Listar agenda:
{{"action":"calendar_list","start":"2026-06-13T00:00:00-03:00","end":"2026-06-13T23:59:59-03:00","response":"Buscando seus compromissos..."}}

REGRAS CRÍTICAS PARA ENVIO DE E-MAIL:
1. Se o usuario pedir para enviar um e-mail para um NOME (ex: "Joao", "Maria", "esposa") in vez de um endereço de e-mail completo (com "@"), você deve verificar se ele existe na SUA LISTA DE CONTATOS ATUAL acima. Se existir, use o e-mail correspondente. Caso contrário, ou em caso de ambiguidade, retorne a ação "contacts" primeiro para pesquisar o e-mail correspondente no Google Contatos.
2. Apenas retorne a ação "send" se você tiver um endereço de e-mail válido (contendo "@") no campo "to" E o usuário tiver fornecido a aprovação ou confirmação explícita de envio (ex: "pode enviar", "envie", "sim", "confirmo").
3. Se você precisar criar ou sugerir a mensagem do e-mail (conforme regra 4), use a ação "chat" ou "ask" para apresentar a mensagem sugerida ao usuário e solicitar a sua aprovação explícita de envio. NUNCA envie (ação "send") de imediato sem que o usuário aprove o texto que você escreveu.
4. Se o usuário fornecer o assunto/contexto do e-mail mas não detalhar o texto exato do corpo, você deve REDIGIR de forma autônoma um corpo de mensagem completo, profissional, amigável e contextualmente adequado. Nunca deixe a mensagem/corpo de e-mail em branco ou vazio.

AÇÕES DE E-MAIL:
- Enviar e-mail:
{{"action":"send","to":"email_com_arroba","subject":"assunto","body":"corpo","response":"Enviando..."}}
- Pedir dados faltantes:
{{"action":"ask","response":"Olá, Claudemir! Para enviar, preciso de:\\n- Assunto\\n- Mensagem"}}
- Ver e-mails:
{{"action":"list","limit":5,"response":"Buscando seus emails, Claudemir..."}}

REGRAS DE PESQUISA WEB (INTERNET):
1. Use a ação "web_search" se o usuário perguntar sobre fatos recentes, notícias do dia, previsão do tempo atualizada, resultados de jogos ou qualquer informação em tempo real que você não tenha em seu conhecimento prévio.
2. Formule uma query de pesquisa clara e objetiva para o campo "query".

OUTRAS AÇÕES:
- Pesquisa na Web:
{{"action":"web_search","query":"termo de busca","response":"Pesquisando na web por termo de busca..."}}
- Buscar contatos:
{{"action":"contacts","query":"nome_do_contato","response":"Buscando o e-mail de nome_do_contato nos seus contatos..."}}
- Autenticar:
{{"action":"auth","response":"Acesse para autenticar seu Gmail e Calendario: {get_auth_url()}"}}
- Chat Geral:
{{"action":"chat","response":"sua resposta para Claudemir"}}

Data/Hora Atual: {datetime.now().strftime('%d/%m/%Y %H:%M')} (Fuso: America/Sao_Paulo)"""

    # Adicionar mensagem do usuário ao histórico apenas se solicitado
    if save_to_history:
        add_to_history(chat_id, "user", query)
        messages = [{"role": "system", "content": prompt}] + get_chat_history(chat_id)
    else:
        # Se save_to_history for False, incluímos a query temporariamente apenas no payload enviado à API, sem poluir a memória persistente do chat
        messages = [{"role": "system", "content": prompt}] + get_chat_history(chat_id) + [{"role": "user", "content": query}]

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json={"model": "llama-3.3-70b-versatile", "messages": messages, "temperature": 0.7},
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
    return "http://localhost:8000/api/gmail/auth-url"

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
    chat_id = update.effective_chat.id
    text = update.message.text
    logger.info(f"Msg from {chat_id}: {text}")
    
    result = await groq_chat(chat_id, text)
    logger.info(f"Groq Chat result: {result}")
    action = result.get("action", "chat")
    
    response_text = ""
    if action == "send":
        to = result.get("to", "")
        subject = result.get("subject", "")
        body = result.get("body", "")
        msg_id, err = send_email(to, subject, body)
        if err:
            response_text = err
        else:
            response_text = f"Email enviado para {to}! ID: {msg_id}"
        await update.message.reply_text(response_text)
    elif action == "list":
        emails, err = get_emails(result.get("limit", 5))
        if err:
            response_text = err
        elif not emails:
            response_text = "Nenhum email encontrado."
        else:
            response_text = "Seus emails:\n\n" + "\n---\n".join(emails)[:4000]
        await update.message.reply_text(response_text)
    elif action == "contacts":
        search_query = result.get("query", "")
        contacts, err = search_contacts(search_query)
        if err:
            response_text = f"Erro ao buscar contatos: {err}"
        elif not contacts:
            response_text = f"Nenhum contato encontrado para '{search_query}'."
        else:
            options = [f"• **{c['name']}**: {c['email']}" for c in contacts]
            response_text = f"Olá, Claudemir! Encontrei os seguintes contatos para '{search_query}':\n\n" + "\n".join(options)
        await update.message.reply_text(response_text)
    elif action == "calendar_create":
        title = result.get("title", "")
        start = result.get("start", "")
        end = result.get("end", "")
        description = result.get("description", "")
        attendees = result.get("attendees", [])
        
        event, err = create_event(title, start, end, description, attendees)
        if err:
            response_text = f"Erro ao criar evento: {err}"
        else:
            response_text = f"✅ Evento '{event.get('summary')}' criado com sucesso!\nLink do Google Calendar: {event.get('htmlLink')}"
        await update.message.reply_text(response_text)
    elif action == "calendar_list":
        start = result.get("start", "")
        end = result.get("end", "")
        events, err = list_events(start, end)
        if err:
            response_text = f"Erro ao buscar eventos: {err}"
        elif not events:
            response_text = "Nenhum evento encontrado na agenda para o período solicitado."
        else:
            lines = []
            for ev in events:
                start_time = ev.get('start', {}).get('dateTime') or ev.get('start', {}).get('date')
                try:
                    dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    dt_str = dt.strftime('%d/%m às %H:%M')
                except:
                    dt_str = start_time
                lines.append(f"• **{ev.get('summary')}** — {dt_str}")
            response_text = "📅 Seus compromissos encontrados:\n\n" + "\n".join(lines)
        await update.message.reply_text(response_text)
    elif action == "web_search":
        search_query = result.get("query", "")
        status_msg = await update.message.reply_text(f"🔍 Pesquisando na web por '{search_query}'...")
        
        search_results = await search_web_tavily(search_query)
        
        temp_context = f"[SISTEMA: Resultados da pesquisa para '{search_query}']\n\n{search_results}"
        add_to_history(chat_id, "system", temp_context)
        
        final_result = await groq_chat(chat_id, f"Responda a pergunta original ('{text}') usando as informações acima.", save_to_history=False)
        logger.info(f"Web Search final result: {final_result}")
        
        history = get_chat_history(chat_id)
        if history and history[-1]["role"] == "system":
            history.pop()
            
        response_text = final_result.get("response", "Desculpe, nao consegui formular a resposta.")
        logger.info(f"Sending web_search final response: {response_text[:300]}")
        try:
            await status_msg.delete()
        except Exception as e:
            logger.warning(f"Erro ao deletar msg de status: {e}")
            
        try:
            await update.message.reply_text(response_text, parse_mode="Markdown")
        except Exception as e:
            logger.warning(f"Erro ao enviar resposta com Markdown: {e}. Enviando texto puro.")
            await update.message.reply_text(response_text)
    elif action == "auth":
        response_text = result.get("response", "")
        await update.message.reply_text(response_text)
    else:
        response_text = result.get("response", result.get("response", "Desculpe, nao entendi."))
        await update.message.reply_text(response_text)
        
    # Salvar a resposta no histórico da conversação
    add_to_history(chat_id, "assistant", response_text)

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