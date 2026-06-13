import os
import json
from pathlib import Path
from harness.logger import logger

# Caminho absoluto para salvar o histórico de tópicos do LinkedIn
HISTORY_FILE = Path(__file__).parent.parent / "logs" / "linkedin_topics.json"

VIRAL_POST_TEMPLATE = (
    "Escreva um post curto e viral para o LinkedIn sobre o tema: '{topic}'.\n\n"
    "Diretrizes:\n"
    "1. Tamanho: Curto (entre 100 e 200 palavras).\n"
    "2. Tom: Altamente inspirador, enérgico e provocativo.\n"
    "3. Estrutura:\n"
    "   - Um título inicial chamativo e de forte impacto.\n"
    "   - Insight rápido sobre o tema com dados rápidos ou tendências.\n"
    "   - Termine com uma pergunta provocativa ou Chamada para Ação (CTA) instigando comentários.\n"
    "4. Estilo: Use formatações limpas e emojis com moderação para melhorar a escaneabilidade.\n\n"
    "IMPORTANTE: Retorne APENAS o texto final do post formatado, sem observações do sistema ou introduções."
)

TECHNICAL_ARTICLE_TEMPLATE = (
    "Escreva um artigo técnico e analítico para o LinkedIn sobre o tema: '{topic}'.\n\n"
    "Diretrizes:\n"
    "1. Tamanho: Médio/Longo (entre 500 e 1000 palavras).\n"
    "2. Tom: Profissional, analítico e técnico, adequado para a comunidade de TI.\n"
    "3. Estrutura:\n"
    "   - Título técnico direto.\n"
    "   - **Introdução**: Contextualização do problema.\n"
    "   - **Desenvolvimento**: Dividido em subtópicos organizados e aprofundados (use títulos em Markdown, listas e blocos de código se relevante).\n"
    "   - **Conclusão**: Considerações finais e uma breve referência ou conselho prático.\n"
    "4. Estilo: Clareza extrema e profundidade profissional.\n\n"
    "IMPORTANTE: Retorne APENAS o artigo formatado, sem introduções adicionais."
)

def load_history() -> list:
    """Lê o arquivo local logs/linkedin_topics.json contendo os temas já abordados"""
    if not HISTORY_FILE.exists():
        return []
    try:
        data = HISTORY_FILE.read_text(encoding="utf-8")
        return json.loads(data)
    except Exception as e:
        logger.error(f"Erro ao carregar histórico de tópicos do LinkedIn: {e}")
        return []

def save_topic(topic: str) -> None:
    """Adiciona o tema gerado ao arquivo de histórico para evitar repetições"""
    history = load_history()
    cleaned_topic = topic.strip().lower()
    if cleaned_topic not in history:
        history.append(cleaned_topic)
        try:
            HISTORY_FILE.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
            logger.info(f"Tópico do LinkedIn '{topic}' adicionado ao histórico em json.")
        except Exception as e:
            logger.error(f"Erro ao salvar tópico do LinkedIn no histórico: {e}")

def is_topic_duplicate(topic: str) -> tuple[bool, str | None]:
    """
    Verifica se o tema já foi abordado anteriormente.
    Retorna (is_duplicate, sugestao_de_alerta).
    """
    history = load_history()
    cleaned_topic = topic.strip().lower()
    
    # Verifica correspondência direta ou parcial básica
    for old_topic in history:
        if cleaned_topic in old_topic or old_topic in cleaned_topic:
            logger.warning(f"LinkedIn: Tópico duplicado detectado com '{old_topic}'!")
            alert = (
                f"Aviso: Você já gerou conteúdo sobre um tema semelhante recentemente ('{old_topic}'). "
                "Para o engajamento ideal no LinkedIn, recomendo tentar abordar por outro ângulo ou escolher outro tópico."
            )
            return True, alert
            
    return False, None

def validate_content(text: str, style: str) -> tuple[bool, int, int]:
    """
    Valida se o texto está dentro dos limites de caracteres do LinkedIn.
    Posts comuns têm limite estrito de 3.000 caracteres.
    Artigos de página inteira têm limite de 100.000 caracteres (portanto, livres para o nosso limite de 1000 palavras).
    Retorna (is_valid, tamanho_atual, limite_maximo).
    """
    char_count = len(text)
    
    if style == "post":
        limit = 3000
        is_valid = char_count <= limit
        logger.debug(f"Validação de post LinkedIn: {char_count}/{limit} caracteres. Válido: {is_valid}")
        return is_valid, char_count, limit
    else:
        limit = 100000
        is_valid = char_count <= limit
        logger.debug(f"Validação de artigo LinkedIn: {char_count}/{limit} caracteres. Válido: {is_valid}")
        return is_valid, char_count, limit
