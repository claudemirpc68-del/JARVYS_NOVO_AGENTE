"""
JARVIS 2.0 - Bot Telegram Interface (Sincronizado)
Focado exclusivamente na comunicação com o usuário e interface do Telegram.
Toda a lógica de negócios, IA, ferramentas e memória é gerenciada pelo Harness.
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

# Configuração de logging básica para o bot
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Instanciar o orquestrador do Harness
orchestrator = JarvisOrchestrator()

# Handlers do Telegram
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 JARVIS 2.0 - Assistente de Email Inteligente\n\n"
        "Olá! Eu sou seu assistente pessoal. Comandos disponíveis:\n\n"
        "• Para enviar email: \"Envia um email para joao@exemplo.com sobre reunião\"\n"
        "• Para buscar emails: \"Busca emails do João\"\n"
        "• Para criar rascunho: \"Cria rascunho para maria@empresa.com\"\n"
        "• Para responder email: \"Responde ao último email\"\n\n"
        "Você também pode me enviar mensagens de voz para interagir!\n\n"
        "Comandos:\n"
        "/start - Iniciar\n"
        "/status - Status do sistema\n"
        "/auth - Autenticar Gmail/Calendário\n"
        "/email - Ver últimos e-mails\n"
        "/ajuda - Ajuda"
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from tools.gmail_tool import get_gmail_service
    gmail_ok = "Conectado" if get_gmail_service() else "Não autenticado"
    await update.message.reply_text(
        f"📊 Status do Sistema - JARVIS 2.0\n\n"
        f"Groq (IA): OK\n"
        f"Google API: {gmail_ok}\n"
        f"Telegram Bot: OK\n"
        f"Skill de Áudio: Ativa"
    )

async def auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = f"http://localhost:{config.server.port}/api/gmail/auth-url"
    await update.message.reply_text(f"Abra este link para autenticar seu Gmail e Calendário:\n\n{url}")

async def email_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from tools.gmail_tool import get_emails
    emails, err = get_emails(5)
    if err:
        await update.message.reply_text(err)
        return
    if not emails:
        await update.message.reply_text("Nenhum e-mail encontrado.")
        return
    text = "📧 Seus últimos e-mails:\n\n" + "\n---\n".join(emails)
    await update.message.reply_text(text[:4000])

async def ajuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📚 Como usar o JARVIS 2.0\n\n"
        "Basta enviar uma mensagem por texto ou comandos, ou uma nota de voz:\n\n"
        "Exemplos:\n"
        "- \"Enviar e-mail para fulano sobre o assunto x\"\n"
        "- \"Quais compromissos eu tenho hoje?\"\n"
        "- \"Pesquisar na internet sobre as últimas notícias de IA\"\n"
        "- \"Agende uma reunião com a diretoria amanhã às 15h\"\n\n"
        "Comandos:\n"
        "/status - Status da aplicação\n"
        "/auth - Reautenticar Google\n"
        "/email - Listar e-mails\n"
        "/ajuda - Esta mensagem de ajuda"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text
    logger.info(f"Telegram recebido de {chat_id}: {text}")
    
    # 1. Enviar feedback visual de progresso inicial
    status_msg = await update.message.reply_text("🤖 *JARVIS está processando...*", parse_mode="Markdown")
    
    # 2. Callback assíncrono para atualizar o status do progresso conforme a ação detectada pelo Harness
    async def on_action_start(action_type, action_data):
        try:
            if action_type == "web_search":
                query = action_data.get("query", "")
                await status_msg.edit_text(f"🔍 *Pesquisando na web por '{query}'...*", parse_mode="Markdown")
            elif action_type == "send":
                to = action_data.get("to", "")
                await status_msg.edit_text(f"📧 *Enviando e-mail para {to}...*", parse_mode="Markdown")
            elif action_type == "list":
                await status_msg.edit_text("📧 *Buscando seus últimos e-mails...*", parse_mode="Markdown")
            elif action_type == "contacts":
                query = action_data.get("query", "")
                await status_msg.edit_text(f"👤 *Buscando contato '{query}'...*", parse_mode="Markdown")
            elif action_type == "calendar_create":
                title = action_data.get("title", "")
                await status_msg.edit_text(f"📅 *Agendando compromisso '{title}'...*", parse_mode="Markdown")
            elif action_type == "calendar_list":
                await status_msg.edit_text("📅 *Buscando compromissos...*", parse_mode="Markdown")
            elif action_type == "linkedin_post":
                topic = action_data.get("topic", "")
                await status_msg.edit_text(f"✍️ *Gerando post para o LinkedIn sobre '{topic}'...*", parse_mode="Markdown")
            elif action_type == "linkedin_article":
                topic = action_data.get("topic", "")
                await status_msg.edit_text(f"✍️ *Redigindo artigo para o LinkedIn sobre '{topic}'...*", parse_mode="Markdown")
            elif action_type == "weather":
                location = action_data.get("location", "")
                await status_msg.edit_text(f"🌤️ *Buscando a previsão do tempo para '{location}'...*", parse_mode="Markdown")
        except Exception as e:
            logger.warning(f"Erro ao editar mensagem de status do Telegram: {e}")

    # 3. Processar mensagem na camada de orquestração do Harness
    result = await orchestrator.process(chat_id, text, on_action_start=on_action_start)
    response_text = result.get("response", "Desculpe, não consegui processar a resposta.")
    
    # 4. Deletar a mensagem temporária de progresso
    try:
        await status_msg.delete()
    except Exception as e:
        logger.warning(f"Erro ao deletar mensagem de status do Telegram: {e}")
        
    # 5. Enviar a resposta final para o usuário
    try:
        await update.message.reply_text(response_text, parse_mode="Markdown")
    except Exception as e:
        logger.warning(f"Erro de parser Markdown no Telegram. Enviando texto puro. Detalhe: {e}")
        await update.message.reply_text(response_text)
        
    # 6. Atualizar a memória do chat com a resposta final do JARVIS
    orchestrator.update_memory(chat_id, "assistant", response_text)

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    
    # 1. Enviar feedback visual de progresso inicial
    status_msg = await update.message.reply_text("🤖 *Recebendo áudio...*", parse_mode="Markdown")
    
    try:
        # 2. Identificar se é nota de voz nativa ou arquivo de áudio
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
        
        # Baixar o arquivo de áudio
        new_file = await context.bot.get_file(file_id)
        await new_file.download_to_drive(str(ogg_path))
        
        await status_msg.edit_text("🤖 *Transcrevendo áudio...*", parse_mode="Markdown")
        
        # 3. Transcrever usando Groq Whisper
        groq_key = config.api.groq_api_key or os.environ.get("GROQ_API_KEY", "")
        transcribed_text = await audio.transcribe_audio(str(ogg_path), groq_key)
        
        if not transcribed_text:
            await status_msg.edit_text("⚠️ Não consegui transcrever ou entender o áudio. Por favor, tente enviar novamente.")
            if ogg_path.exists():
                ogg_path.unlink()
            return
            
        await status_msg.edit_text(
            f"📝 *Transcrição:* \"{transcribed_text}\"\n\n"
            f"🤖 *Processando resposta...*",
            parse_mode="Markdown"
        )
        
        # 4. Callback assíncrono para atualizar o status do progresso conforme a ação detectada pelo Harness
        async def on_action_start(action_type, action_data):
            try:
                if action_type == "web_search":
                    query = action_data.get("query", "")
                    await status_msg.edit_text(f"📝 *Transcrição:* \"{transcribed_text}\"\n\n🔍 *Pesquisando na web por '{query}'...*", parse_mode="Markdown")
                elif action_type == "send":
                    to = action_data.get("to", "")
                    await status_msg.edit_text(f"📝 *Transcrição:* \"{transcribed_text}\"\n\n📧 *Enviando e-mail para {to}...*", parse_mode="Markdown")
                elif action_type == "list":
                    await status_msg.edit_text(f"📝 *Transcrição:* \"{transcribed_text}\"\n\n📧 *Buscando seus últimos e-mails...*", parse_mode="Markdown")
                elif action_type == "contacts":
                    query = action_data.get("query", "")
                    await status_msg.edit_text(f"📝 *Transcrição:* \"{transcribed_text}\"\n\n👤 *Buscando contato '{query}'...*", parse_mode="Markdown")
                elif action_type == "calendar_create":
                    title = action_data.get("title", "")
                    await status_msg.edit_text(f"📝 *Transcrição:* \"{transcribed_text}\"\n\n📅 *Agendando compromisso '{title}'...*", parse_mode="Markdown")
                elif action_type == "calendar_list":
                    await status_msg.edit_text(f"📝 *Transcrição:* \"{transcribed_text}\"\n\n📅 *Buscando compromissos...*", parse_mode="Markdown")
                elif action_type == "linkedin_post":
                    topic = action_data.get("topic", "")
                    await status_msg.edit_text(f"📝 *Transcrição:* \"{transcribed_text}\"\n\n✍️ *Gerando post para o LinkedIn sobre '{topic}'...*", parse_mode="Markdown")
                elif action_type == "linkedin_article":
                    topic = action_data.get("topic", "")
                    await status_msg.edit_text(f"📝 *Transcrição:* \"{transcribed_text}\"\n\n✍️ *Redigindo artigo para o LinkedIn sobre '{topic}'...*", parse_mode="Markdown")
                elif action_type == "weather":
                    location = action_data.get("location", "")
                    await status_msg.edit_text(f"📝 *Transcrição:* \"{transcribed_text}\"\n\n🌤️ *Buscando a previsão do tempo para '{location}'...*", parse_mode="Markdown")
            except Exception as err:
                logger.warning(f"Erro ao editar status da voz: {err}")

        # 5. Processar mensagem na camada de orquestração do Harness
        result = await orchestrator.process(chat_id, transcribed_text, on_action_start=on_action_start)
        response_text = result.get("response", "Desculpe, não consegui processar a resposta.")
        
        await status_msg.edit_text(
            f"📝 *Transcrição:* \"{transcribed_text}\"\n\n"
            f"🤖 *Gerando áudio de resposta...*",
            parse_mode="Markdown"
        )
        
        # 6. Gerar áudio a partir da resposta usando Edge TTS
        mp3_path = temp_dir / f"reply_{chat_id}_{timestamp}.mp3"
        clean_text = response_text.replace("*", "").replace("_", "").replace("`", "").replace("#", "")
        
        await audio.text_to_speech(clean_text, str(mp3_path))
        
        # 7. Remover mensagem de progresso temporária
        try:
            await status_msg.delete()
        except Exception as err:
            logger.warning(f"Erro ao deletar mensagem de status do Telegram: {err}")
            
        # 8. Enviar resposta em nota de voz com a transcrição do texto no caption
        try:
            with open(mp3_path, "rb") as voice_file:
                await update.message.reply_voice(
                    voice=voice_file,
                    caption=f"📝 *Resposta do JARVIS:*\n\n{response_text}"[:1024],
                    parse_mode="Markdown"
                )
        except Exception as e:
            logger.warning(f"Erro de parser Markdown ao enviar nota de voz. Tentando texto puro. Detalhe: {e}")
            with open(mp3_path, "rb") as voice_file:
                await update.message.reply_voice(
                    voice=voice_file,
                    caption=f"📝 Resposta do JARVIS:\n\n{response_text}"[:1024],
                    parse_mode=None
                )
            
        # Se o texto for maior que o limite de legenda, enviar em mensagem de texto
        if len(response_text) > 950:
            await update.message.reply_text(response_text, parse_mode="Markdown")
            
        # 9. Atualizar memória
        orchestrator.update_memory(chat_id, "assistant", response_text)
        
        # 10. Limpar arquivos temporários do disco
        if ogg_path.exists():
            ogg_path.unlink()
        if mp3_path.exists():
            mp3_path.unlink()
            
    except Exception as e:
        logger.error(f"Erro no processamento de mensagem de voz: {e}")
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
        
    print("JARVIS 2.0 Telegram Bot iniciando...")
    
    app = Application.builder().token(telegram_token).build()
    
    # Comandos
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("auth", auth))
    app.add_handler(CommandHandler("email", email_cmd))
    app.add_handler(CommandHandler("ajuda", ajuda))
    
    # Mensagens de texto, notas de voz e arquivos de áudio
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice))
    
    print("Bot do Telegram rodando e pronto para receber mensagens, notas de voz e arquivos de áudio!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()