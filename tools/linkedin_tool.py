import os
import json
from pathlib import Path
from harness.logger import logger

# Caminho absoluto para salvar o histórico de tópicos do LinkedIn
HISTORY_FILE = Path(__file__).parent.parent / "logs" / "linkedin_topics.json"

VIRAL_POST_TEMPLATE = (
    "Você é um LinkedIn Post Expert, especialista em criar posts virais e engajantes para o LinkedIn nas áreas de TI, Logística e Inteligência Artificial (IA).\n"
    "Escreva um RASCUNHO de post curto e dinâmico sobre o tema: '{topic}'.\n\n"
    "Diretrizes da Skill:\n"
    "1. **Analisador de Contexto**: Identifique se o tema se refere a TI, Logística ou IA (ou uma combinação delas) e ajuste o tom para ser adequado: profissional, inspirador, técnico ou reflexivo.\n"
    "2. **Personalizador de Jornada**: Você deve OBRIGATORIAMENTE incluir a frase exata: \"Estou iniciando minha jornada no mundo da TI\" de forma fluida no texto, destacando evolução, aprendizado contínuo ou a conexão do tema com a tecnologia.\n"
    "3. **Gerador de Estrutura de Post**:\n"
    "   - **Abertura chamativa**: Comece com uma pergunta impactante, uma reflexão forte ou um dado interessante para capturar a atenção imediata.\n"
    "   - **Corpo**: Apresente uma breve explicação, uma experiência ou um insight relevante sobre a conexão do tema com a sua jornada.\n"
    "   - **Fechamento**: Termine com um convite/chamada aberta para interação (ex: \"O que você pensa sobre isso?\", \"Compartilhe sua experiência\").\n"
    "4. **Regra de Hashtags**: NÃO inclua nenhuma hashtag neste rascunho. As hashtags serão adicionadas automaticamente depois.\n"
    "5. **Tamanho e Estilo**: O texto do rascunho deve ser curto (entre 100 e 150 palavras), usar parágrafos curtos, espaçamento limpo e emojis com moderação.\n\n"
    "IMPORTANTE: Retorne APENAS o texto final do rascunho, sem observações do sistema, sem introduções adicionais e sem nenhuma hashtag."
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
