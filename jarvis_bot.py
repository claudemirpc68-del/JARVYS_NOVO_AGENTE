"""
JARVIS 2.0 - Bot Telegram Interface
Focado exclusivamente na comunicação com o usuário e interface do Telegram.
Toda a lógica de negócios, IA, ferramentas e memória foi movida para o Harness.
"""

import os
import logging
from pathlib import Path
from datetime import datetime

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from harness.orchestrator import JarvisOrchestrator
from config import config

# Configuração de logging básica para o bot
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Instanciar o orquestrador do Harness
orchestrator = JarvisOrchestrator()

# Handlers do Telegram
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "JARVIS 2.0 - Assistente Pessoal Inteligente\n\n"
        "Envie qualquer mensagem para interagir!\n\n"
        "Comandos:\n"
        "/start - Iniciar\n"
        "/status - Status\n"
        "/auth - Autenticar Gmail/Calendário\n"
        "/email - Ver últimos e-mails\n"
        "/ajuda - Ajuda"
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from tools.gmail_tool import get_gmail_service
    gmail_ok = "Conectado" if get_gmail_service() else "Não autenticado"
    await update.message.reply_text(
        f"Status do Sistema\n\n"
        f"Groq (IA): OK\n"
        f"Google API: {gmail_ok}\n"
        f"Telegram Bot: OK"
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
    text = "Seus últimos e-mails:\n\n" + "\n---\n".join(emails)
    await update.message.reply_text(text[:4000])

async def ajuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Como usar o JARVIS 2.0\n\n"
        "Basta enviar uma mensagem por texto ou comandos:\n\n"
        "Exemplos:\n"
        "- Enviar e-mail para fulano sobre o assunto x\n"
        "- Quais compromissos eu tenho hoje?\n"
        "- Pesquisar na internet sobre as últimas notícias de IA\n"
        "- Agendar reunião com Joelma amanhã às 14h\n\n"
        "Comandos:\n"
        "/status - Status da aplicação\n"
        "/auth - Reautenticar Google"
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
                await status_msg.edit_text(f"👤 *Buscando contato '{query}' nos seus contatos...*", parse_mode="Markdown")
            elif action_type == "calendar_create":
                title = action_data.get("title", "")
                await status_msg.edit_text(f"📅 *Agendando compromisso '{title}' no seu calendário...*", parse_mode="Markdown")
            elif action_type == "calendar_list":
                await status_msg.edit_text("📅 *Buscando seus compromissos...*", parse_mode="Markdown")
            elif action_type == "linkedin_post":
                topic = action_data.get("topic", "")
                await status_msg.edit_text(f"✍️ *Gerando post viral para o LinkedIn sobre '{topic}'...*", parse_mode="Markdown")
            elif action_type == "linkedin_article":
                topic = action_data.get("topic", "")
                await status_msg.edit_text(f"✍️ *Redigindo artigo técnico para o LinkedIn sobre '{topic}'...*", parse_mode="Markdown")
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
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("auth", auth))
    app.add_handler(CommandHandler("email", email_cmd))
    app.add_handler(CommandHandler("ajuda", ajuda))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("Bot do Telegram rodando e pronto para receber mensagens!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()