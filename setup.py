"""
Script de configuração inicial para o JARVIS 2.0
Este script ajudará você a configurar as credenciais do Google API
"""

import os
import json
from pathlib import Path

def setup_google_credentials():
    """Configura credenciais do Google API"""
    
    print("🔧 Configuração Inicial - JARVIS 2.0")
    print("=" * 40)
    
    # Verificar se já existe arquivo de credenciais
    if os.path.exists("credentials.json"):
        print("✅ Arquivo credentials.json já existe")
        return True
    
    print("📝 Você precisa criar um projeto no Google Cloud Console:")
    print("1. Acesse: https://console.cloud.google.com/")
    print("2. Crie um novo projeto ou selecione existente")
    print("3. Ative as APIs: Gmail API, Google Drive API (opcional)")
    print("4. Crie credenciais do tipo 'OAuth 2.0 Client IDs'")
    print("5. Selecione 'Web application'")
    print("6. Adicione URIs de redirecionamento: http://localhost:8000")
    print("7. Baixe o arquivo credentials.json")
    print()
    
    # Perguntar se o usuário tem o arquivo
    have_credentials = input("Você já tem o arquivo credentials.json? (s/n): ").lower()
    
    if have_credentials == 's':
        # Copiar arquivo
        source = input("Digite o caminho completo do arquivo credentials.json: ")
        if os.path.exists(source):
            import shutil
            shutil.copy2(source, "credentials.json")
            print("✅ Arquivo copiado com sucesso!")
            return True
        else:
            print("❌ Arquivo não encontrado!")
            return False
    else:
        print("\n⚠️  Por favor, siga as instruções acima e execute este script novamente.")
        return False

def setup_environment():
    """Configura arquivo .env"""
    
    print("\n📋 Configurando arquivo .env...")
    
    # Criar .env a partir do exemplo
    if os.path.exists(".env.example"):
        shutil.copy2(".env.example", ".env")
        print("✅ Arquivo .env criado a partir do exemplo")
        
        # Editar .env se necessário
        edit_env = input("Deseja editar o arquivo . agora? (s/n): ").lower()
        if edit_env == 's':
            print("\n📝 Edite o arquivo .env com suas credenciais:")
            print("- GROQ_API_KEY: Sua chave da API Groq")
            print("- TELEGRAM_TOKEN: Seu token do bot Telegram")
            print("- GOOGLE_CREDENTIALS_PATH: caminho para credentials.json")
            print("- GOOGLE_TOKEN_PATH: caminho para token.json")
            print("- USER_ID: seu ID do Telegram")
    
    return True

def main():
    """Função principal"""
    
    # Criar diretório se não existir
    os.makedirs("config", exist_ok=True)
    
    print("🚀 Configurando JARVIS 2.0...")
    
    # Configurar Google credentials
    google_ok = setup_google_credentials()
    
    # Configurar ambiente
    if google_ok:
        env_ok = setup_environment()
        
        if env_ok:
            print("\n✅ Configuração concluída!")
            print("\n📦 Próximos passos:")
            print("1. Instale as dependências: pip install -r requirements.txt")
            print("2. Teste o servidor: python jarvis_server.py")
            print("3. Inicie o bot Telegram: python telegram_bot.py")
            print("4. Acesse a API: http://localhost:8000/docs")
        else:
            print("\n❌ Falha na configuração do ambiente")
    else:
        print("\n❌ Falha na configuração das credenciais")

if __name__ == "__main__":
    import shutil
    main()