#!/usr/bin/env python3
"""
Teste simplificado do JARVIS 2.0
Verifica se os arquivos básicos existem e as dependencias podem ser importadas
"""

import os
import sys
from pathlib import Path

def check_files():
    """Verificar arquivos necessarios"""
    required_files = [
        "jarvis_server.py",
        "telegram_bot.py",
        "config.py",
        "requirements.txt",
        "credentials.json",
        ".env"
    ]
    
    print("Verificando arquivos necessarios...")
    all_ok = True
    
    for file in required_files:
        if Path(file).exists():
            print(f"[OK] {file}")
        else:
            print(f"[ERRO] {file} - Arquivo nao encontrado")
            all_ok = False
    
    return all_ok

def check_imports():
    """Verificar importacoes basicas"""
    print("\nVerificando importacoes...")
    
    try:
        from config import config
        print("[OK] config.py")
        return True
    except ImportError as e:
        print(f"[ERRO] config.py - {e}")
        return False

def check_credentials():
    """Verificar credenciais"""
    print("\nVerificando credenciais...")
    
    try:
        from config import config
        
        # Verificar se temos as credenciais basicas
        if config.api.groq_api_key:
            print("[OK] Groq API Key")
        else:
            print("[ERRO] Groq API Key")
            return False
            
        if config.api.telegram_token:
            print("[OK] Telegram Token")
        else:
            print("[ERRO] Telegram Token")
            return False
            
        if config.google.credentials_path:
            print("[OK] Google Credentials Path")
        else:
            print("[ERRO] Google Credentials Path")
            return False
            
        if config.user["id"]:
            print("[OK] User ID")
        else:
            print("[ERRO] User ID")
            return False
            
        return True
        
    except Exception as e:
        print(f"[ERRO] Verificando credenciais - {e}")
        return False

def check_dependencies():
    """Verificar dependencias"""
    print("\nVerificando dependencias...")
    
    dependencies = {
        "fastapi": "fastapi",
        "uvicorn": "uvicorn",
        "httpx": "httpx",
        "google-auth-oauthlib": "google_auth_oauthlib.flow",
        "googleapiclient": "googleapiclient",
        "python-telegram-bot": "telegram"
    }
    
    all_ok = True
    for dep_name, module_name in dependencies.items():
        try:
            __import__(module_name)
            print(f"[OK] {dep_name}")
        except ImportError:
            print(f"[ERRO] {dep_name} - Nao instalado")
            all_ok = False
    
    return all_ok

def main():
    """Funcao principal"""
    print("Teste simplificado - JARVIS 2.0")
    print("=" * 30)
    
    # Testes
    files_ok = check_files()
    imports_ok = check_imports()
    creds_ok = check_credentials()
    deps_ok = check_dependencies()
    
    # Resultado final
    print("\n" + "=" * 30)
    print("Resultado dos testes:")
    
    tests = [
        ("Arquivos necessarios", files_ok),
        ("Importacoes", imports_ok),
        ("Credenciais", creds_ok),
        ("Dependencias", deps_ok)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, result in tests:
        status = "PASS" if result else "FAIL"
        print(f"{status}: {test_name}")
        if result:
            passed += 1
    
    print(f"\nTotal: {passed}/{total} testes passados")
    
    if passed == total:
        print("\nSUCESSO! O JARVIS 2.0 esta pronto para uso.")
        print("\nProximos passos:")
        print("1. Instale dependencias: pip install -r requirements.txt")
        print("2. Inicie servidor: python jarvis_server.py")
        print("3. Inicie bot: python telegram_bot.py")
        print("4. Acesse API: http://localhost:8000/docs")
    else:
        print("\nFALHA! Corrija os problemas antes de usar.")
        print("\nProblemas encontrados:")
        for test_name, result in tests:
            if not result:
                print(f"- {test_name}")

if __name__ == "__main__":
    main()