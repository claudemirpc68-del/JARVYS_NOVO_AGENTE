from googleapiclient.discovery import build
from harness.logger import logger
from tools.gmail_tool import get_creds

def get_people_service():
    creds = get_creds()
    if not creds:
        return None
    try:
        service = build('people', 'v1', credentials=creds)
        return service
    except Exception as e:
        logger.error(f"Erro ao inicializar o serviço Google People (Contatos): {e}")
        return None

def search_contacts(query: str) -> tuple[list[dict], str | None]:
    """
    Busca contatos por correspondência de nome no Google Contacts.
    Retorna (lista_de_contatos, error_message).
    """
    service = get_people_service()
    if not service:
        return [], "Google Contacts não autenticado."

    try:
        logger.info(f"Buscando contato correspondente a '{query}' no Google Contacts...")
        results = service.people().searchContacts(
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
                
        logger.info(f"Busca de contato concluída. {len(contacts)} resultados encontrados.")
        return contacts, None
    except Exception as e:
        logger.error(f"Erro ao buscar contatos: {e}")
        return [], str(e)

def get_all_contacts() -> list[str]:
    """
    Retorna a lista completa de conexões do usuário para injeção de contexto no Prompt.
    """
    service = get_people_service()
    if not service:
        logger.warning("Google Contacts não autenticado. Impossível listar contatos para o prompt.")
        return []

    try:
        logger.info("Carregando lista de todos os contatos para o prompt...")
        results = service.people().connections().list(
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
                
        logger.info(f"Carregamento de contatos finalizado. {len(contacts)} contatos carregados.")
        return contacts
    except Exception as e:
        logger.error(f"Erro ao carregar todos os contatos: {e}")
        return []

def resolve_email_address(email_or_name: str) -> tuple[str | None, str | None, str | None]:
    """
    Tenta resolver um e-mail ou nome para um endereço de e-mail válido no Google Contatos.
    Retorna (email_resolvido, nome_do_contato, error_message).
    """
    email_or_name = email_or_name.strip()
    if "@" in email_or_name:
        return email_or_name, None, None

    contacts, err = search_contacts(email_or_name)
    if err:
        return None, None, f"Erro ao buscar contatos: {err}"
        
    if not contacts:
        return None, None, f"Não encontrei nenhum contato com o nome '{email_or_name}' no seu Google Contatos."
        
    if len(contacts) == 1:
        return contacts[0]["email"], contacts[0]["name"], None

    # Múltiplos contatos encontrados (ambiguidade)
    options = [f"- {c['name']} ({c['email']})" for c in contacts]
    error_msg = (
        f"Encontrei mais de um contato para '{email_or_name}':\n\n"
        + "\n".join(options)
        + "\n\nPor favor, especifique o e-mail correspondente ou o nome completo do contato."
    )
    return None, None, error_msg
