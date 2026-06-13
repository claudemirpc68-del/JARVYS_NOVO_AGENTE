import base64
from pathlib import Path
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from harness.logger import logger
from config import config

# Usar escopos do config ou os escopos fornecidos pela autenticação
SCOPES = config.google.scopes

def get_creds():
    token_path = Path(config.google.token_path)
    if not token_path.exists():
        logger.warning(f"Token do Google não encontrado em: {token_path}")
        return None
    try:
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
        if creds.expired and creds.refresh_token:
            logger.info("Token do Google expirado. Tentando atualizar...")
            creds.refresh(Request())
            token_path.write_text(creds.to_json())
            logger.info("Token do Google atualizado com sucesso.")
        return creds
    except Exception as e:
        logger.error(f"Erro ao carregar credenciais do Google: {e}")
        return None

def get_gmail_service():
    creds = get_creds()
    if not creds:
        return None
    try:
        service = build('gmail', 'v1', credentials=creds)
        return service
    except Exception as e:
        logger.error(f"Erro ao inicializar o serviço do Gmail: {e}")
        return None

def send_email(to: str, subject: str, body: str) -> tuple[str | None, str | None]:
    """
    Envia um e-mail em HTML usando a API do Gmail.
    Retorna (message_id, error_message).
    """
    service = get_gmail_service()
    if not service:
        return None, "Gmail não autenticado. Favor autenticar."

    try:
        # Nota: A assinatura é adicionada programaticamente no bot
        msg = f"From: me\nTo: {to}\nSubject: {subject}\nContent-Type: text/html; charset=UTF-8\n\n{body}"
        raw = base64.urlsafe_b64encode(msg.encode()).decode()
        
        logger.info(f"Enviando e-mail para '{to}' com assunto '{subject}'")
        result = service.users().messages().send(userId="me", body={"raw": raw}).execute()
        
        message_id = result.get('id')
        logger.info(f"E-mail enviado com sucesso. ID da mensagem: {message_id}")
        return message_id, None
    except Exception as e:
        logger.error(f"Erro ao enviar e-mail via Gmail API: {e}")
        return None, str(e)

def get_emails(limit: int = 5) -> tuple[list[str] | None, str | None]:
    """
    Busca os últimos e-mails da caixa de entrada do usuário.
    Retorna (lista_de_emails_formatados, error_message).
    """
    service = get_gmail_service()
    if not service:
        return None, "Gmail não autenticado. Favor autenticar."

    try:
        logger.info(f"Buscando os últimos {limit} e-mails do Gmail...")
        results = service.users().messages().list(userId="me", maxResults=limit).execute()
        messages = results.get('messages', [])
        
        if not messages:
            logger.info("Nenhum e-mail encontrado na caixa de entrada.")
            return [], None

        emails = []
        for m in messages:
            msg = service.users().messages().get(
                userId="me", 
                id=m['id'], 
                format='metadata', 
                metadataHeaders=['From', 'Subject', 'Date']
            ).execute()
            
            headers = {h['name']: h['value'] for h in msg['payload']['headers']}
            emails.append(
                f"De: {headers.get('From', '?')}\n"
                f"Assunto: {headers.get('Subject', '?')}\n"
                f"Data: {headers.get('Date', '?')}"
            )
            
        logger.info(f"Busca concluída. {len(emails)} e-mails carregados.")
        return emails, None
    except Exception as e:
        logger.error(f"Erro ao listar e-mails via Gmail API: {e}")
        return None, str(e)
