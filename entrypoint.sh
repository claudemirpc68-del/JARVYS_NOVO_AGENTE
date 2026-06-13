#!/bin/sh

# 1. Restaurar arquivos de credenciais do Google Cloud a partir das variáveis de ambiente (Base64 ou JSON direto)
if [ -n "$GOOGLE_CREDENTIALS_BASE64" ]; then
    echo "Restaurando credentials.json a partir de Base64..."
    python -c "import os, base64; open('/app/credentials.json', 'wb').write(base64.b64decode(os.environ['GOOGLE_CREDENTIALS_BASE64']))"
elif [ -n "$GOOGLE_CREDENTIALS_JSON" ]; then
    echo "Restaurando credentials.json direto..."
    echo "$GOOGLE_CREDENTIALS_JSON" > /app/credentials.json
else
    echo "AVISO: GOOGLE_CREDENTIALS_BASE64 ou GOOGLE_CREDENTIALS_JSON não configurado."
fi

if [ -n "$GOOGLE_TOKEN_BASE64" ]; then
    echo "Restaurando token.json a partir de Base64..."
    python -c "import os, base64; open('/app/token.json', 'wb').write(base64.b64decode(os.environ['GOOGLE_TOKEN_BASE64']))"
elif [ -n "$GOOGLE_TOKEN_JSON" ]; then
    echo "Restaurando token.json direto..."
    echo "$GOOGLE_TOKEN_JSON" > /app/token.json
else
    echo "AVISO: GOOGLE_TOKEN_BASE64 ou GOOGLE_TOKEN_JSON não configurado."
fi

# 2. Inicializar o servidor FastAPI em segundo plano
echo "Iniciando jarvis_server.py na porta 8000..."
python jarvis_server.py &
SERVER_PID=$!

# 3. Inicializar o bot do Telegram
echo "Iniciando jarvis_bot.py..."
python jarvis_bot.py &
BOT_PID=$!

# Função de limpeza ao receber sinal de encerramento
cleanup() {
    echo "Encerrando serviços..."
    kill $SERVER_PID
    kill $BOT_PID
    exit 0
}

trap cleanup INT TERM

# 4. Monitorar os processos. Se qualquer um deles cair, o container deve falhar.
while true; do
    if ! kill -0 $SERVER_PID 2>/dev/null; then
        echo "Erro: Servidor FastAPI parou inesperadamente."
        exit 1
    fi
    if ! kill -0 $BOT_PID 2>/dev/null; then
        echo "Erro: Bot do Telegram parou inesperadamente."
        exit 1
    fi
    sleep 5
done
