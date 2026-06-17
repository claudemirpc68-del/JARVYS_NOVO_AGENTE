import json
import os
from pathlib import Path
from harness.logger import logger

class JarvisMemory:
    def __init__(self):
        # Memória conversacional em memória: {chat_id: [{role, content}]}
        self.chat_memories = {}
        # Resumo acumulado do contexto anterior por chat_id
        self.context_summaries = {}
        # Limite padrão de mensagens mantidas para histórico de contexto
        self.default_limit = 30
        # Caminho para persistência em disco na raiz do projeto
        self.file_path = Path(__file__).parent.parent / "chat_memories.json"
        
        # Carregar memórias persistidas
        self.load_from_disk()

    def load_from_disk(self) -> None:
        """
        Carrega o histórico de mensagens do disco se o arquivo JSON existir.
        Suporta tanto o formato antigo (lista direta) quanto o novo formato (dict com messages + context_summary).
        """
        try:
            if self.file_path.exists():
                data = json.loads(self.file_path.read_text(encoding="utf-8"))
                self.chat_memories = {}
                self.context_summaries = {}
                
                for k, v in data.items():
                    chat_id = int(k)
                    
                    if isinstance(v, list):
                        # Formato antigo: lista direta de mensagens — migra automaticamente
                        self.chat_memories[chat_id] = v
                        self.context_summaries[chat_id] = ""
                        logger.info(f"Chat {chat_id}: migrado do formato antigo para o novo.")
                    elif isinstance(v, dict):
                        # Formato novo: dict com messages + context_summary
                        self.chat_memories[chat_id] = v.get("messages", [])
                        self.context_summaries[chat_id] = v.get("context_summary", "")
                    else:
                        logger.warning(f"Chat {chat_id}: formato desconhecido ignorado.")
                        
                logger.info(f"Histórico de conversação carregado com sucesso do disco ({len(self.chat_memories)} chats).")
            else:
                self.chat_memories = {}
                self.context_summaries = {}
        except Exception as e:
            logger.error(f"Erro ao carregar histórico de conversação do disco: {e}")
            self.chat_memories = {}
            self.context_summaries = {}

    def save_to_disk(self) -> None:
        """Salva o histórico de mensagens e resumos de contexto no disco"""
        try:
            data = {}
            all_chat_ids = set(list(self.chat_memories.keys()) + list(self.context_summaries.keys()))
            
            for chat_id in all_chat_ids:
                data[str(chat_id)] = {
                    "messages": self.chat_memories.get(chat_id, []),
                    "context_summary": self.context_summaries.get(chat_id, "")
                }
                
            self.file_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            logger.debug("Histórico de conversação salvo com sucesso no disco.")
        except Exception as e:
            logger.error(f"Erro ao salvar histórico de conversação no disco: {e}")

    def get_history(self, chat_id: int) -> list:
        """Obtém o histórico de mensagens completo para um chat específico"""
        if chat_id not in self.chat_memories:
            self.chat_memories[chat_id] = []
        return self.chat_memories[chat_id]

    def add_message(self, chat_id: int, role: str, content: str) -> None:
        """Adiciona uma nova mensagem (user, assistant ou system) ao histórico"""
        if chat_id not in self.chat_memories:
            self.chat_memories[chat_id] = []
        
        self.chat_memories[chat_id].append({"role": role, "content": content})
        self.save_to_disk()

    def get_overflow_messages(self, chat_id: int) -> list:
        """
        Retorna as mensagens que excederam o limite e precisam ser resumidas.
        NÃO remove as mensagens ainda — isso é feito pelo prune_history.
        """
        history = self.get_history(chat_id)
        if len(history) <= self.default_limit:
            return []
        overflow_count = len(history) - self.default_limit
        return history[:overflow_count]

    def prune_history(self, chat_id: int, limit: int = None) -> int:
        """
        Mantém apenas as últimas X mensagens no histórico do chat.
        Retorna o número de mensagens removidas.
        """
        limit = limit or self.default_limit
        history = self.get_history(chat_id)
        if len(history) > limit:
            removed_count = len(history) - limit
            self.chat_memories[chat_id] = history[removed_count:]
            self.save_to_disk()
            logger.debug(f"Poda de histórico ativada para chat {chat_id}. {removed_count} mensagens antigas removidas.")
            return removed_count
        return 0

    def get_context_summary(self, chat_id: int) -> str:
        """Retorna o resumo acumulado do contexto anterior para um chat"""
        return self.context_summaries.get(chat_id, "")

    def set_context_summary(self, chat_id: int, summary: str) -> None:
        """Define/atualiza o resumo acumulado do contexto anterior para um chat"""
        self.context_summaries[chat_id] = summary
        self.save_to_disk()
        logger.info(f"Resumo de contexto atualizado para chat {chat_id} ({len(summary)} chars).")

    def clear_history(self, chat_id: int) -> None:
        """Limpa todo o histórico de conversação e o resumo de contexto do chat"""
        self.chat_memories[chat_id] = []
        self.context_summaries[chat_id] = ""
        self.save_to_disk()
        logger.info(f"Histórico de conversação e resumo do chat {chat_id} limpos.")

    def search_semantic_memory(self, chat_id: int, query: str, top_k: int = 3) -> list:
        """
        Placeholder para buscar mensagens antigas contextualmente relevantes no banco vetorial.
        Pode ser implementado no futuro integrando com ChromaDB ou FAISS.
        """
        logger.debug(f"Pesquisa semântica simulada em memória para: '{query}'")
        return []
