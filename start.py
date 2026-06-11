#!/usr/bin/env python3
"""
Script de inicialização do JARVIS 2.0
Inicia tanto o servidor principal quanto o bot do Telegram
"""

import os
import sys
import subprocess
import threading
import time
from pathlib import Path

def check_requirements():
    """Verificar dependências"""
    try:
        import fastapi
        import uvicorn
        import httpx
        import google_auth_oauthlib
        import googleapiclient
        import telegram
        print("✅ Todas as dependências estão instaladas")
        return True
    except ImportError as e:
        print(f"❌ Dependência faltando: {e}")
        print("Instale com: pip install -r requirements.txt")
        return False

def start_server():
    """Iniciar servidor FastAPI"""
    print("🚀 Iniciando servidor JARVIS 2.0...")
    try:
        subprocess.run([sys.executable, "jarvis_server.py"])
    except KeyboardInterrupt:
        print("\n🛑 Servidor desligado")

def start_telegram():
    """Iniciar bot do Telegram"""
    print("📱 Iniciando bot do Telegram...")
    try:
        subprocess.run([sys.executable, "telegram_bot.py"])
    except KeyboardInterrupt:
        print("\n🛑 Bot desligado")

def main():
    """Função principal"""
    print("🤖 JARVIS 2.0 - Inicialização")
    print("=" * 30)
    
    # Verificar se estamos no diretório correto
    if not os.path.exists("jarvis_server.py") or not os.path.exists("telegram_bot.py"):
        print("❌ Execute este script no diretório do JARVIS 2.0")
        return
    
    # Verificar dependências
    if not check_requirements():
        return
    
    # Verificar arquivo .env
    if not os.path.exists(".env"):
        print("⚠️  Arquivo .env não encontrado. Criando a partir do exemplo...")
        if os.path.exists(".env.example"):
            import shutil
            shutil.copy2(".env.example", ".env")
            print("✅ Arquivo .env criado")
        else:
            print("❌ Arquivo .env.example não encontrado")
            return
    
    # Perguntar qual iniciar
    print("\nO que você deseja iniciar?")
    print("1. Servidor principal (API)")
    print("2. Bot do Telegram")
    print("3. Ambos (em background)")
    
    choice = input("Escolha (1-3): ").strip()
    
    if choice == "1":
        start_server()
    elif choice == "2":
        start_telegram()
    elif choice == "3":
        print("🚀 Iniciando ambos em background...")
        
        # Iniciar servidor em thread
        server_thread = threading.Thread(target=start_server, daemon=True)
        server_thread.start()
        
        # Dar tempo para servidor iniciar
        time.sleep(3)
        
        # Iniciar bot
        start_telegram()
    else:
        print("❌ Opção inválida")

if __name__ == "__main__":
    main()