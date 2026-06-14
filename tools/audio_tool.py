import os
import logging
import httpx
import edge_tts

logger = logging.getLogger(__name__)

async def transcribe_audio(file_path: str, api_key: str) -> str:
    """
    Envia um arquivo de áudio local para a API do Groq Whisper e retorna o texto transcrito.
    Suporta formatos comuns como .ogg, .mp3, .wav, etc.
    """
    if not api_key:
        raise ValueError("Chave de API do Groq (GROQ_API_KEY) não fornecida.")

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Arquivo de áudio não encontrado: {file_path}")

    filename = os.path.basename(file_path)
    # Definir content-type apropriado para .ogg ou fallback
    content_type = "audio/ogg" if filename.endswith(".ogg") else "audio/mpeg"

    logger.info(f"Iniciando transcrição de {filename} via Groq Whisper...")

    url = "https://api.groq.com/openai/v1/audio/transcriptions"
    headers = {
        "Authorization": f"Bearer {api_key}"
    }

    try:
        async with httpx.AsyncClient() as client:
            with open(file_path, "rb") as f:
                files = {
                    "file": (filename, f, content_type)
                }
                data = {
                    "model": "whisper-large-v3",
                    "response_format": "json"
                }

                # O tempo limite para upload de áudio e transcrição deve ser generoso
                response = await client.post(
                    url,
                    headers=headers,
                    files=files,
                    data=data,
                    timeout=60.0
                )

            if response.status_code != 200:
                logger.error(f"Erro na API Groq Whisper ({response.status_code}): {response.text}")
                raise Exception(f"Erro do Groq Whisper (Status {response.status_code}): {response.text}")

            result_json = response.json()
            transcription = result_json.get("text", "").strip()
            logger.info(f"Transcrição concluída com sucesso para {filename}.")
            return transcription

    except Exception as e:
        logger.error(f"Falha na transcrição do áudio {filename}: {e}")
        raise e

async def text_to_speech(text: str, output_path: str, voice: str = "pt-BR-AntonioNeural") -> str:
    """
    Converte texto em fala usando a biblioteca edge-tts e salva o arquivo de saída.
    A voz padrão é pt-BR-AntonioNeural.
    """
    if not text:
        raise ValueError("Texto vazio fornecido para conversão de fala.")

    logger.info(f"Iniciando conversão de texto para fala (voz: {voice})...")
    try:
        # Garantir que a pasta destino existe
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_path)
        logger.info(f"Áudio gerado e salvo em: {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"Erro na geração de áudio com edge-tts: {e}")
        raise e
