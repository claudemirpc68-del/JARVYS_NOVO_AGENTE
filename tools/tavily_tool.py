import os
import requests
from harness.logger import logger
from config import config

def search_web_tavily(query: str) -> str:
    """
    Realiza uma pesquisa web usando a API do Tavily e a biblioteca requests.
    Retorna uma string formatada com os 3 principais resultados.
    """
    # Carregar do config centralizado
    tavily_key = config.api.tavily_api_key or os.environ.get("TAVILY_API_KEY", "")
    
    if not tavily_key:
        logger.warning("TAVILY_API_KEY não configurada nas variáveis de ambiente ou config.")
        return "Erro: Chave de API do Tavily (TAVILY_API_KEY) não configurada."

    try:
        logger.info(f"Iniciando pesquisa web no Tavily para a query: '{query}'")
        resp = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": tavily_key,
                "query": query,
                "search_depth": "basic",
                "max_results": 3
            },
            headers={"Content-Type": "application/json"},
            timeout=15
        )
        
        if resp.status_code == 200:
            data = resp.json()
            results = data.get("results", [])
            
            if not results:
                logger.info("Tavily Search: Nenhum resultado relevante encontrado.")
                return "Nenhum resultado relevante encontrado na pesquisa web."
                
            lines = []
            for idx, r in enumerate(results, 1):
                lines.append(f"{idx}. **{r.get('title')}**\nLink: {r.get('url')}\nConteúdo: {r.get('content')}")
            
            logger.info(f"Pesquisa no Tavily concluída. {len(results)} resultados retornados.")
            return "\n\n".join(lines)
        else:
            logger.error(f"Erro na chamada da API do Tavily: Status {resp.status_code} - {resp.text}")
            return f"Erro na API do Tavily: Status {resp.status_code}"
            
    except Exception as e:
        logger.error(f"Exceção durante a pesquisa no Tavily: {e}")
        return f"Erro na pesquisa web: {e}"
