"""
Script para gerar o arquivo credentials.json para o JARVIS 2.0
Usa as credenciais fornecidas pelo usuário
"""

import json
import os
from pathlib import Path

def generate_credentials():
    """Gera arquivo credentials.json com as credenciais fornecidas"""
    
    # Credenciais fornecidas
    credentials_data = {
        "installed": {
            "client_id": "seu-client-id.apps.googleusercontent.com",
            "project_id": "seu-projeto-id",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": "seu-client-secret",
            "redirect_uris": ["http://localhost:8000"],
            "client_email": "seu-email@project-id.iam.gserviceaccount.com",
            "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/seu-email%40project-id.iam.gserviceaccount.com"
        }
    }
    
    # Salvar arquivo
    with open("credentials.json", "w") as f:
        json.dump(credentials_data, f, indent=2)
    
    print("✅ Arquivo credentials.json gerado com sucesso!")
    print("📍 Local: credentials.json")
    
    # Verificar se foi criado
    if Path("credentials.json").exists():
        print("✅ Arquivo criado com sucesso!")
        
        # Mostrar conteúdo básico (sem segredos)
        print("\n📋 Conteúdo do arquivo:")
        with open("credentials.json", "r") as f:
            data = json.load(f)
            client_id = data["installed"]["client_id"]
            client_secret = data["installed"]["client_secret"]
            print(f"Client ID: {client_id}")
            print(f"Client Secret: {client_secret[:10]}... (truncado)")
    else:
        print("❌ Falha ao criar arquivo")

def update_env_file():
    """Atualiza arquivo .env com as credenciais"""
    
    # Criar .env se não existir
    if not os.path.exists(".env"):
        print("📋 Criando arquivo .env...")
        env_content = """# Configuração do JARVIS 2.0
# Copie este arquivo para .env e preencha com suas credenciais

# API Keys
GROQ_API_KEY=sua_chave_groq_aqui
TELEGRAM_TOKEN=seu_token_telegram_aqui

# Google API Credentials
GOOGLE_CREDENTIALS_PATH=credentials.json
GOOGLE_TOKEN_PATH=token.json

# User Configuration
USER_ID=seu_id_telegram_aqui

# Server Configuration
HOST=0.0.0.0
PORT=8000
"""
        
        with open(".env", "w") as f:
            f.write(env_content)
        
        print("✅ Arquivo .env criado com sucesso!")
    else:
        print("✅ Arquivo .env já existe")

def main():
    """Função principal"""
    print("🔧 Gerando configuração do JARVIS 2.0...")
    print("=" * 40)
    
    # Gerar credentials.json
    generate_credentials()
    
    # Atualizar .env
    update_env_file()
    
    print("\n🎉 Configuração concluída!")
    print("\n📦 Próximos passos:")
    print("1. Instale as dependências: pip install -r requirements.txt")
    print("2. Teste a instalação: python test.py")
    print("3. Inicie o sistema: python start.py")
    print("4. Acesse a API: http://localhost:8000/docs")

if __name__ == "__main__":
    main()