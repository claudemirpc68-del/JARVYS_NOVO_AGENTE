"""
JARVIS 2.0 - Bot do Telegram
Interage com o servidor via Telegram
"""

import os
import json
import logging
import httpx
import asyncio
from pathlib import Path
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Config logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load .env
def load_env():
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()

load_env()

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
SERVER_URL = "http://localhost:8000"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start"""
    await update.message.reply_text(
        "🤖 JARVIS 2.0 - Assistente de Email\n\n"
        "Envie qualquer mensagem para interagir!\n\n"
        "Comandos:\n"
        "/start - Iniciar\n"
        "/status - Status do sistema\n"
        "/email - Verificar emails\n"
        "/ajuda - Ajuda"
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /status"""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{SERVER_URL}/api/status")
            data = resp.json()
        
        text = (
            f"📊 Status do Sistema\n\n"
            f"Servidor: {data.get('status', 'desconhecido')}\n"
            f"Groq: {data.get('groq', 'desconhecido')}\n"
            f"Gmail: {data.get('gmail', 'desconhecido')}\n"
            f"Telegram: {data.get('telegram', 'desconhecido')}"
        )
        await update.message.reply_text(text)
    except Exception as e:
        await update.message.reply_text(f"❌ Erro ao verificar status: {e}")

async def email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /email - verificar emails"""
    try:
        query = " ".join(context.args) if context.args else "Quais são meus últimos emails?"
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{SERVER_URL}/api/chat",
                json={"query": query, "user_id": str(update.effective_chat.id)},
                timeout=30
            )
            data = resp.json()
        
        await update.message.reply_text(data.get("response", "Sem resposta"))
    except Exception as e:
        await update.message.reply_text(f"❌ Erro: {e}")

async def ajuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /ajuda"""
    await update.message.reply_text(
        "📚 Como usar o JARVIS 2.0\n\n"
        "Basta enviar uma mensagem descrevendo o que deseja fazer:\n\n"
        "📧 Emails:\n"
        "- 'Enviar email para fulano@exemplo.com'\n"
        "- 'Quais são meus últimos emails?'\n"
        "- 'Responder ao último email'\n"
        "- 'Criar rascunho para fulano'\n\n"
        "Comandos especiais:\n"
        "/start - Iniciar bot\n"
        "/status - Ver status\n"
        "/email - Ver emails\n"
        "/ajuda - Esta mensagem"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lida com mensagens do usuário"""
    try:
        text = update.message.text
        user_id = str(update.effective_chat.id)
        
        logger.info(f"Mensagem de {user_id}: {text}")
        
        # Enviar para o servidor
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{SERVER_URL}/api/chat",
                json={"query": text, "user_id": user_id},
                timeout=30
            )
            data = resp.json()
        
        response = data.get("response", "Desculpe, não consegui processar.")
        await update.message.reply_text(response)
        
    except httpx.ConnectError:
        await update.message.reply_text("❌ Servidor offline. Tente novamente.")
    except Exception as e:
        logger.error(f"Erro: {e}")
        await update.message.reply_text(f"❌ Erro ao processar: {e}")

def main():
    """Iniciar bot"""
    if not TELEGRAM_TOKEN:
        print("TELEGRAM_TOKEN nao configurado no .env")
        return
    
    print("Iniciando JARVIS 2.0 Bot...")
    
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Comandos
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("email", email))
    app.add_handler(CommandHandler("ajuda", ajuda))
    
    # Mensagens
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("Bot rodando! Envie mensagem no Telegram.")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()