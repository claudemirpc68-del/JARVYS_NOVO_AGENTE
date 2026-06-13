import os
import logging
from pathlib import Path

# Cria a pasta de logs na raiz do projeto se não existir
LOGS_DIR = Path(__file__).parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)

class SuccessFilter(logging.Filter):
    """Filtro para permitir apenas logs de nível INFO e DEBUG (sucesso/operação)"""
    def filter(self, record):
        return record.levelno <= logging.INFO

def setup_logger():
    # Criar logger root ou específico do Harness
    logger = logging.getLogger("jarvis")
    logger.setLevel(logging.DEBUG)
    
    # Evitar duplicação de handlers se já configurado
    if logger.handlers:
        return logger

    # Formatadores
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_formatter = logging.Formatter('%(asctime)s - [%(levelname)s] - %(message)s')

    # Handler do Console (mostra INFO e acima no terminal)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # Handler para logs de Sucesso / Operação (app.log)
    app_handler = logging.FileHandler(str(LOGS_DIR / "app.log"), encoding="utf-8")
    app_handler.setLevel(logging.DEBUG)
    app_handler.setFormatter(file_formatter)
    app_handler.addFilter(SuccessFilter())
    logger.addHandler(app_handler)

    # Handler para logs de Erro (error.log)
    error_handler = logging.FileHandler(str(LOGS_DIR / "error.log"), encoding="utf-8")
    error_handler.setLevel(logging.WARNING)
    error_handler.setFormatter(file_formatter)
    logger.addHandler(error_handler)

    return logger

# Instância global do logger para importação simples
logger = setup_logger()
