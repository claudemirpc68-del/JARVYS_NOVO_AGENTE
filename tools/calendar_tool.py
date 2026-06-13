from datetime import datetime
from googleapiclient.discovery import build
from harness.logger import logger
from tools.gmail_tool import get_creds
from tools.contacts_tool import resolve_email_address

def get_calendar_service():
    creds = get_creds()
    if not creds:
        return None
    try:
        service = build('calendar', 'v3', credentials=creds)
        return service
    except Exception as e:
        logger.error(f"Erro ao inicializar o serviço Google Calendar: {e}")
        return None

def create_event(title: str, start_iso: str, end_iso: str, description: str = "", attendees: list[str] = None) -> tuple[dict | None, str | None]:
    """
    Cria um compromisso no Google Calendar primário do usuário.
    Retorna (evento_criado, error_message).
    """
    service = get_calendar_service()
    if not service:
        return None, "Google Calendar não autenticado."

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

        # Resolver emails dos convidados (caso tenham sido passados nomes)
        if attendees:
            resolved_attendees = []
            for att in attendees:
                resolved_email, _, _ = resolve_email_address(att)
                if resolved_email:
                    resolved_attendees.append({'email': resolved_email})
                else:
                    # Fallback caso não ache ou já seja um email direto
                    resolved_attendees.append({'email': att})
            event['attendees'] = resolved_attendees

        logger.info(f"Criando evento '{title}' no Google Calendar ({start_iso} a {end_iso})...")
        created_event = service.events().insert(
            calendarId='primary', 
            body=event, 
            sendUpdates='all'
        ).execute()
        
        logger.info(f"Evento criado com sucesso. Link: {created_event.get('htmlLink')}")
        return created_event, None
    except Exception as e:
        logger.error(f"Erro ao criar evento via Google Calendar API: {e}")
        return None, str(e)

def list_events(start_iso: str = None, end_iso: str = None, max_results: int = 10) -> tuple[list[dict] | None, str | None]:
    """
    Lista compromissos agendados no calendário do usuário.
    Retorna (lista_de_eventos, error_message).
    """
    service = get_calendar_service()
    if not service:
        return None, "Google Calendar não autenticado."

    try:
        if not start_iso:
            start_iso = datetime.now().isoformat() + 'Z'
            
        logger.info(f"Buscando eventos no calendário de {start_iso} até {end_iso}...")
        events_result = service.events().list(
            calendarId='primary',
            timeMin=start_iso,
            timeMax=end_iso if end_iso else None,
            maxResults=max_results,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        logger.info(f"Busca finalizada. {len(events)} eventos encontrados.")
        return events, None
    except Exception as e:
        logger.error(f"Erro ao listar eventos via Google Calendar API: {e}")
        return None, str(e)
