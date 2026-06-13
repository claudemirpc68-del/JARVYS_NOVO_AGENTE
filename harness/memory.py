from harness.logger import logger

class JarvisMemory:
    def __init__(self):
        # Memória conversacional em memória: {chat_id: [{"role": role, "content": content}]}
        self.chat_memories = {}
        # Limite padrão de mensagens mantidas para histórico de contexto
        self.default_limit = 15

        # Espaço reservado para cliente de banco vetorial (opcional futuro)
        # self.vector_db_client = None

    def get_history(self, chat_id: int) -> list:
        """Obtém o histórico de mensagens completo para um chat específico"""
        if chat_id not in self.chat_memories:
            self.chat_memories[chat_id] = []
        return self.chat_memories[chat_id]

    def add_message(self, chat_id: int, role: str, content: str) -> None:
        """Adiciona uma nova mensagem (user, assistant ou system) ao histórico e poda se necessário"""
        if chat_id not in self.chat_memories:
            self.chat_memories[chat_id] = []
        
        self.chat_memories[chat_id].append({"role": role, "content": content})
        self.prune_history(chat_id)
        
        # Opcional futuro: Gravar interação no banco vetorial para busca de longo prazo
        # self._store_in_vector_db(chat_id, role, content)

    def prune_history(self, chat_id: int, limit: int = None) -> None:
        """Mantém apenas as últimas X mensagens no histórico do chat para evitar estouro de contexto"""
        limit = limit or self.default_limit
        history = self.get_history(chat_id)
        if len(history) > limit:
            # Remove as mensagens mais antigas até atingir o limite
            removed_count = len(history) - limit
            self.chat_memories[chat_id] = history[removed_count:]
            logger.debug(f"Poda de histórico ativada para chat {chat_id}. {removed_count} mensagens antigas removidas.")

    def clear_history(self, chat_id: int) -> None:
        """Limpa todo o histórico de conversação do chat"""
        self.chat_memories[chat_id] = []
        logger.info(f"Histórico de conversação do chat {chat_id} limpo.")

    def _store_in_vector_db(self, chat_id: int, role: str, content: str):
        """
        Placeholder para armazenar embeddings das conversas em um banco vetorial
        como ChromaDB ou FAISS para busca semântica de longo prazo.
        """
        pass

    def search_semantic_memory(self, chat_id: int, query: str, top_k: int = 3) -> list:
        """
        Placeholder para buscar mensagens antigas contextualmente relevantes no banco vetorial.
        Pode ser implementado no futuro integrando com ChromaDB ou FAISS.
        """
        logger.debug(f"Pesquisa semântica simulada em memória para: '{query}'")
        return []
