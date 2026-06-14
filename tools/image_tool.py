"""
JARVIS 2.0 — Skill de Geração de Imagens
Gera imagens a partir de prompts de texto usando o Space Hugging Face KingNish/Realtime-FLUX (Gradio Client).
"""

import asyncio
import logging
import os
import shutil
from pathlib import Path
from datetime import datetime
from gradio_client import Client

logger = logging.getLogger(__name__)

DEFAULT_WIDTH = 1024
DEFAULT_HEIGHT = 1024

def _run_gradio_predict(prompt: str, width: int, height: int) -> tuple:
    """Função síncrona executada em thread para evitar bloquear o loop de eventos."""
    logger.info("Conectando ao Space Gradio KingNish/Realtime-FLUX...")
    client = Client("KingNish/Realtime-FLUX")
    
    logger.info(f"Enviando predição para o Space: prompt='{prompt[:80]}...'")
    result_tuple = client.predict(
        prompt=prompt,
        seed=0,  # Semente padrão do endpoint /generate_image
        width=width,
        height=height,
        api_name="/generate_image"
    )
    return result_tuple

async def generate_image(
    prompt: str,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    chat_id: int = 0,
) -> tuple[str | None, str | None]:
    """
    Gera uma imagem a partir de um prompt de texto usando o Space KingNish/Realtime-FLUX.

    Args:
        prompt: Descrição da imagem a ser gerada (preferencialmente em inglês).
        width: Largura da imagem in pixels.
        height: Altura da imagem in pixels.
        chat_id: ID do chat para nomear o arquivo temporário.

    Returns:
        Tupla (caminho_do_arquivo, None) em sucesso ou (None, mensagem_de_erro) em falha.
    """
    if not prompt or not prompt.strip():
        return None, "Prompt de imagem vazio. Por favor, descreva a imagem que deseja gerar."

    # Preparar diretório temporário
    temp_dir = Path("temp_images")
    temp_dir.mkdir(exist_ok=True)

    timestamp = int(datetime.now().timestamp())
    output_path = temp_dir / f"img_{chat_id}_{timestamp}.webp"

    logger.info(f"Iniciando geração de imagem via Gradio: prompt='{prompt[:80]}...'")

    try:
        # Executa a chamada do Gradio em uma thread secundária
        result_tuple = await asyncio.to_thread(_run_gradio_predict, prompt.strip(), width, height)
        
        if not result_tuple or len(result_tuple) < 1:
            logger.error("Resposta vazia ou inválida do Gradio Client")
            return None, "A IA não retornou nenhum resultado. Tente novamente."
            
        temp_image_path = result_tuple[0]
        latency_str = result_tuple[2] if len(result_tuple) > 2 else "desconhecida"
        
        logger.info(f"Gradio respondeu com sucesso! Latência: {latency_str}")
        
        if temp_image_path and os.path.exists(temp_image_path):
            # Copiar a imagem para o nosso diretório temporário
            shutil.copy(temp_image_path, output_path)
            file_size_kb = os.path.getsize(output_path) / 1024
            logger.info(f"Imagem gerada e salva com sucesso: {output_path} ({file_size_kb:.1f} KB)")
            return str(output_path), None
        else:
            logger.error(f"Arquivo temporário gerado pelo Gradio não existe: {temp_image_path}")
            return None, "Erro ao recuperar o arquivo de imagem gerado pela IA."

    except Exception as e:
        logger.exception(f"Erro inesperado na geração de imagem com Gradio: {e}")
        return None, f"Erro ao gerar a imagem no servidor da IA: {str(e)}"
