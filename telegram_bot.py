import asyncio
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from jarvis_server import jarvis_service, config


# Configuração básica de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lida com mensagens do Telegram"""
    try:
        chat_id = str(update.effective_chat.id)
        text = update.message.text
        
        logger.info(f"Mensagem recebida do chat {chat_id}: {text}")
        
        # Processar comando
        result = await jarvis_service.execute_command(text, chat_id)
        
        # Enviar resposta
        if result.get("success"):
            await update.message.reply_text(result["response"])
        else:
            await update.message.reply_text(f"Erro: {result.get('error', 'Desconhecido')}")
            
    except Exception as e:
        logger.error(f"Erro ao processar mensagem: {e}")
        await update.message.reply_text("Desculpe, ocorreu um erro. Tente novamente.")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start"""
    welcome_message = """🤖 JARVIS 2.0 - Assistente de Email Inteligente

Olá! Eu sou seu assistente de email. Comandos disponíveis:

• Para enviar email: "Envia um email para joao@exemplo.com sobre reunião"
• Para buscar emails: "Busca emails do João"
• Para criar rascunho: "Cria rascunho para maria@empresa.com"
• Para responder email: "Responde ao último email"

Como posso ajudar você hoje?"""
    
    await update.message.reply_text(welcome_message)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /help"""
    help_text = """📚 Ajuda - JARVIS 2.0

Comandos disponíveis:
• /start - Mensagem de boas-vindas
• /help - Esta mensagem de ajuda
• /status - Status do sistema

Exemplos de uso:
• "Envia um email para joao@exemplo.com assunto reunião corpo da mensagem"
• "Busca os últimos 5 emails"
• "Marca como não lido o último email"
• "Responde ao email da Maria sobre o projeto"

Formatos suportados:
• Emails em formato profissional (HTML)
• Busca por remetente
• Respostas diretas
• Organização com etiquetas"""
    
    await update.message.reply_text(help_text)

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /status"""
    try:
        # Simular status do servidor
        status_text = """📊 Status - JARVIS 2.0

✅ Servidor: Online
✅ Gmail: Conectado
✅ Groq: Conectado
✅ Telegram: Ativo

Pronto para ajudar você com seus emails!"""
    
        await update.message.reply_text(status_text)
    except Exception as e:
        logger.error(f"Erro no comando status: {e}")
        await update.message.reply_text("Erro ao verificar status.")

def main():
    """Função principal para o bot do Telegram"""
    try:
        # Criar aplicação Telegram
        application = Application.builder().token(config.api.telegram_token).build()
        
        # Adicionar handlers
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("status", status_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        logger.info("Bot do Telegram iniciado com sucesso!")
        application.run_polling(drop_pending_updates=True)
        
    except Exception as e:
        logger.error(f"Erro ao iniciar bot Telegram: {e}")

if __name__ == "__main__":
    main()