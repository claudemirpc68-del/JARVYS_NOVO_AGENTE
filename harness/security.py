import time
from harness.logger import logger

class JarvisSecurity:
    def __init__(self):
        # Controle de rate limit em memória: {chat_id: [timestamps_de_requisicoes]}
        self.rate_limits = {}
        # Limite: máximo de 10 chamadas a cada 60 segundos
        self.max_requests = 10
        self.time_window = 60

        # Termos abusivos ou de moderação (básico)
        self.banned_words = ["hackear", "crackear", "destruir sistema", "roubar dados"]

        # Ações consideradas críticas que exigem confirmação explícita
        self.critical_actions = ["calendar_delete", "contacts_delete"]

    def check_rate_limit(self, chat_id: int) -> tuple[bool, int]:
        """
        Verifica se o chat_id excedeu o limite de requisições.
        Retorna (autorizado, segundos_para_esperar).
        """
        current_time = time.time()
        if chat_id not in self.rate_limits:
            self.rate_limits[chat_id] = []

        # Limpar timestamps antigos fora da janela de tempo
        self.rate_limits[chat_id] = [t for t in self.rate_limits[chat_id] if current_time - t < self.time_window]

        if len(self.rate_limits[chat_id]) >= self.max_requests:
            oldest_request = self.rate_limits[chat_id][0]
            wait_time = int(self.time_window - (current_time - oldest_request))
            logger.warning(f"Rate limit atingido para o chat_id {chat_id}. Esperar {wait_time}s.")
            return False, max(1, wait_time)

        # Adicionar o timestamp atual
        self.rate_limits[chat_id].append(current_time)
        return True, 0

    def sanitize_input(self, text: str) -> str:
        """Sanitiza o texto de entrada do usuário para evitar injeções ou formatações nocivas"""
        if not text:
            return ""
        # Remove espaços extras e caracteres de controle
        cleaned = text.strip()
        # Impedir injeções de prompt comuns removendo comandos clássicos de jailbreak
        lower_cleaned = cleaned.lower()
        if "ignore as instruções anteriores" in lower_cleaned or "esqueça as regras acima" in lower_cleaned:
            logger.warning("Tentativa de injeção de prompt detectada e sanitizada.")
            cleaned = cleaned.replace("ignore as instruções anteriores", "").replace("esqueça as regras acima", "")
        return cleaned

    def moderate_content(self, text: str) -> bool:
        """
        Verifica se o texto contém termos inadequados ou perigosos.
        Retorna True se o conteúdo for seguro, False se for bloqueado.
        """
        if not text:
            return True
        lower_text = text.lower()
        for word in self.banned_words:
            if word in lower_text:
                logger.warning(f"Filtro de conteúdo ativado: termo proibido '{word}' encontrado.")
                return False
        return True

    def requires_confirmation(self, action_type: str) -> bool:
        """Retorna True se a ação for considerada crítica e exigir confirmação explícita"""
        return action_type in self.critical_actions

    def has_user_confirmed(self, last_messages: list) -> bool:
        """
        Analisa as últimas mensagens no histórico do chat para verificar se
        o usuário deu uma resposta afirmativa de confirmação.
        """
        if not last_messages:
            return False
            
        # 1. Encontrar a última mensagem do assistente no histórico
        last_assistant_msg = None
        for m in reversed(last_messages):
            if m["role"] == "assistant":
                last_assistant_msg = m["content"].lower()
                break
                
        # Se não há mensagem do assistente solicitando confirmação, não pode ser considerado confirmado
        if not last_assistant_msg or not any(word in last_assistant_msg for word in ["confirma", "deseja", "confirmar"]):
            logger.info("Tentativa de confirmação ignorada: o assistente não solicitou confirmação recentemente.")
            return False
            
        # Analisar as mensagens do usuário de trás para frente no histórico recente (últimas 3 mensagens)
        user_responses = [m["content"].lower().strip() for m in last_messages if m["role"] == "user"]
        if not user_responses:
            return False
            
        last_response = user_responses[-1]
        
        # Se o usuário explicitamente negar ou cancelar, não é confirmação
        negation_words = ["não", "nao", "cancelar", "cancela", "mudar", "alterar", "ajustar"]
        if any(word in last_response for word in negation_words):
            logger.info(f"Negação do usuário detectada: '{last_response}'")
            return False
            
        affirmative_words = ["sim", "confirmo", "pode enviar", "envie", "ok", "pode", "autorizo", "prosseguir", "deletar", "apagar"]
        
        # Verifica se alguma palavra afirmativa está contida na última resposta do usuário
        for word in affirmative_words:
            if word in last_response:
                logger.info(f"Confirmação do usuário detectada: '{last_response}' contendo '{word}'")
                return True
                
        return False
