"""
JARVIS 2.0 - Bot Telegram Interface (Planilhas de Clientes)
Focado no controle e gerenciamento da tabela de clientes no Google Sheets.
"""

import os
import logging
from pathlib import Path
from datetime import datetime

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from harness.orchestrator import JarvisOrchestrator
from config import config
import tools.audio_tool as audio

# Configuração de logging básica
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Instanciar o orquestrador
orchestrator = JarvisOrchestrator()

# Handlers do Telegram
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 JARVIS 2.0 - Gerenciador de Planilha de Clientes\n\n"
        "Olá! Eu sou seu assistente pessoal focado em gerenciar e consultar os dados dos seus clientes na planilha \"Cadastro Clientes Tratado\".\n\n"
        "Exemplos de Comandos disponíveis:\n"
        "• Para ver estatísticas: \"Me dá um resumo da planilha\"\n"
        "• Para buscar um cliente: \"Busca por Darcio\"\n"
        "• Para cadastrar novo cliente: \"Adicionar o cliente Matheus M, masculino, nascido em 22/10/1997\"\n\n"
        "Você também pode me enviar mensagens de voz para interagir!\n\n"
        "Comandos:\n"
        "/start - Iniciar\n"
        "/status - Status da planilha e do sistema\n"
        "/ajuda - Ajuda detalhada"
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from tools.customer_sheets_tool import get_sheet
    sheet_ok = "Conectado" if get_sheet() is not None else "Erro de Conexão"
    await update.message.reply_text(
        f"📊 Status do Sistema - JARVIS 2.0\n\n"
        f"Groq/OpenRouter (IA): OK\n"
        f"Google Sheets API: {sheet_ok}\n"
        f"Telegram Bot: OK\n"
        f"Skill de Áudio: Ativa"
    )

async def ajuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📚 Guia de Uso - JARVIS 2.0 (Planilha de Clientes)\n\n"
        "Envie uma mensagem por texto ou nota de voz pedindo uma ação na planilha.\n\n"
        "Exemplos práticos:\n"
        "- \"Me dê o resumo estatístico da tabela de clientes\"\n"
        "- \"Quantos idosos temos na planilha?\"\n"
        "- \"Ache o cliente Juana\"\n"
        "- \"Adicione Carlos Santos, gênero M, nascido em 10/12/1985\"\n\n"
        "Comandos do Chat:\n"
        "/status - Verificar conexão com Google Sheets\n"
        "/ajuda - Esta mensagem de ajuda"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text
    logger.info(f"Telegram recebido de {chat_id}: {text}")
    
    # 1. Enviar feedback visual de progresso inicial
    status_msg = await update.message.reply_text("🤖 *JARVIS está processando...*", parse_mode="Markdown")
    
    # 2. Callback para atualizar o progresso
    async def on_action_start(action_type, action_data):
        try:
            if action_type == "sheets_resumo":
                await status_msg.edit_text("📊 *Processando resumo e estatísticas dos clientes...*", parse_mode="Markdown")
            elif action_type == "sheets_buscar":
                query = action_data.get("query", "")
                await status_msg.edit_text(f"🔍 *Buscando correspondências para '{query}' na planilha...*", parse_mode="Markdown")
            elif action_type == "sheets_adicionar":
                name = action_data.get("name", "")
                await status_msg.edit_text(f"➕ *Cadastrando e higienizando cliente '{name}' no Google Sheets...*", parse_mode="Markdown")
        except Exception as e:
            logger.warning(f"Erro ao editar status no Telegram: {e}")

    # 3. Processar na camada de orquestração do Harness
    result = await orchestrator.process(chat_id, text, on_action_start=on_action_start)
    response_text = result.get("response", "Desculpe, não consegui processar a resposta.")
    
    # 4. Deletar mensagem temporária
    try:
        await status_msg.delete()
    except Exception as e:
        logger.warning(f"Erro ao deletar status: {e}")
        
    # 5. Responder para o usuário
    try:
        await update.message.reply_text(response_text, parse_mode="Markdown")
    except Exception as e:
        logger.warning(f"Erro de Markdown. Enviando como texto puro. Detalhe: {e}")
        await update.message.reply_text(response_text)
        
    # 6. Atualizar memória do chat
    orchestrator.update_memory(chat_id, "assistant", response_text)

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    
    status_msg = await update.message.reply_text("🤖 *Recebendo áudio...*", parse_mode="Markdown")
    
    try:
        # Identificar tipo de áudio
        if update.message.voice:
            audio_obj = update.message.voice
            file_ext = "ogg"
        elif update.message.audio:
            audio_obj = update.message.audio
            file_ext = "mp3"
            if audio_obj.mime_type:
                if "ogg" in audio_obj.mime_type or "opus" in audio_obj.mime_type:
                    file_ext = "ogg"
                elif "wav" in audio_obj.mime_type:
                    file_ext = "wav"
                elif "m4a" in audio_obj.mime_type:
                    file_ext = "m4a"
        else:
            await status_msg.edit_text("⚠️ Tipo de arquivo de áudio não suportado.")
            return

        file_id = audio_obj.file_id
        
        temp_dir = Path("temp_audio")
        temp_dir.mkdir(exist_ok=True)
        
        timestamp = int(datetime.now().timestamp())
        ogg_path = temp_dir / f"voice_{chat_id}_{timestamp}.{file_ext}"
        
        # Baixar o áudio
        new_file = await context.bot.get_file(file_id)
        await new_file.download_to_drive(str(ogg_path))
        
        await status_msg.edit_text("🤖 *Transcrevendo áudio...*", parse_mode="Markdown")
        
        # Transcrever
        groq_key = config.api.groq_api_key or os.environ.get("GROQ_API_KEY", "")
        transcribed_text = await audio.transcribe_audio(str(ogg_path), groq_key)
        
        if not transcribed_text:
            await status_msg.edit_text("⚠️ Não consegui entender o áudio. Tente enviar novamente.")
            if ogg_path.exists():
                ogg_path.unlink()
            return
            
        await status_msg.edit_text(
            f"📝 *Transcrição:* \"{transcribed_text}\"\n\n"
            f"🤖 *Processando resposta...*",
            parse_mode="Markdown"
        )
        
        # Callback de ação
        async def on_action_start(action_type, action_data):
            try:
                if action_type == "sheets_resumo":
                    await status_msg.edit_text(f"📝 *Transcrição:* \"{transcribed_text}\"\n\n📊 *Processando resumo e estatísticas...*", parse_mode="Markdown")
                elif action_type == "sheets_buscar":
                    query = action_data.get("query", "")
                    await status_msg.edit_text(f"📝 *Transcrição:* \"{transcribed_text}\"\n\n🔍 *Buscando '{query}' na planilha...*", parse_mode="Markdown")
                elif action_type == "sheets_adicionar":
                    name = action_data.get("name", "")
                    await status_msg.edit_text(f"📝 *Transcrição:* \"{transcribed_text}\"\n\n➕ *Cadastrando e higienizando cliente '{name}'...*", parse_mode="Markdown")
            except Exception as err:
                logger.warning(f"Erro ao editar status da voz: {err}")

        # Processar
        result = await orchestrator.process(chat_id, transcribed_text, on_action_start=on_action_start)
        response_text = result.get("response", "Desculpe, não consegui processar a resposta.")
        
        await status_msg.edit_text(
            f"📝 *Transcrição:* \"{transcribed_text}\"\n\n"
            f"🤖 *Gerando áudio de resposta...*",
            parse_mode="Markdown"
        )
        
        # Gerar áudio
        mp3_path = temp_dir / f"reply_{chat_id}_{timestamp}.mp3"
        clean_text = response_text.replace("*", "").replace("_", "").replace("`", "").replace("#", "")
        
        await audio.text_to_speech(clean_text, str(mp3_path))
        
        # Remover status temporário
        try:
            await status_msg.delete()
        except Exception:
            pass
            
        # Responder em áudio e texto
        try:
            with open(mp3_path, "rb") as voice_file:
                await update.message.reply_voice(
                    voice=voice_file,
                    caption=f"📝 *Resposta do JARVIS:*\n\n{response_text}"[:1024],
                    parse_mode="Markdown"
                )
        except Exception as e:
            logger.warning(f"Erro de parser Markdown no envio da nota de voz. Detalhe: {e}")
            with open(mp3_path, "rb") as voice_file:
                await update.message.reply_voice(
                    voice=voice_file,
                    caption=f"📝 Resposta do JARVIS:\n\n{response_text}"[:1024],
                    parse_mode=None
                )
            
        if len(response_text) > 950:
            await update.message.reply_text(response_text, parse_mode="Markdown")
            
        # Atualizar memória e limpar arquivos temporários
        orchestrator.update_memory(chat_id, "assistant", response_text)
        if ogg_path.exists():
            ogg_path.unlink()
        if mp3_path.exists():
            mp3_path.unlink()
            
    except Exception as e:
        logger.error(f"Erro no processamento de voz: {e}")
        try:
            await status_msg.edit_text("❌ Ocorreu um erro ao processar sua nota de voz. Por favor, tente novamente.")
        except Exception:
            await update.message.reply_text("❌ Ocorreu um erro ao processar sua nota de voz. Por favor, tente novamente.")

def main():
    telegram_token = config.api.telegram_token or os.environ.get("TELEGRAM_TOKEN", "")
    groq_key = config.api.groq_api_key or os.environ.get("GROQ_API_KEY", "")
    
    if not telegram_token:
        print("Erro: TELEGRAM_TOKEN não configurado.")
        return
    if not groq_key:
        print("Erro: GROQ_API_KEY não configurado.")
        return
        
    print("JARVIS 2.0 Telegram Bot iniciando (Módulo Planilha)...")
    
    app = Application.builder().token(telegram_token).build()
    
    # Comandos registrados
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("ajuda", ajuda))
    
    # Mensagens de texto e de voz
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice))
    
    print("Bot do Telegram rodando e pronto para gerenciar sua tabela de clientes!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()