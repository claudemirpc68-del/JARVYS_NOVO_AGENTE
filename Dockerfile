FROM python:3.11-slim

# Evitar escrita de arquivos .pyc e habilitar saída de log imediata
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements.txt e instalar dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o restante da aplicação
COPY . .

# Dar permissão de execução ao script entrypoint
RUN chmod +x /app/entrypoint.sh

# Porta exposta para o FastAPI
EXPOSE 8000

# Executar o entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]
