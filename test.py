#!/usr/bin/env python3
"""
Script de teste do JARVIS 2.0
Verifica se todos os componentes estão funcionando corretamente
"""

import os
import sys
import json
import asyncio
from pathlib import Path
from config import config

def test_imports():
    """Testar importações básicas"""
    try:
        from jarvis_server import jarvis_service
        print("✅ Importações básicas OK")
        return True
    except ImportError as e:
        print(f"❌ Erro de importação: {e}")
        return False

async def test_groq_api():
    """Testar conexão com Groq API"""
    try:
        import httpx
        
        async with httpx.AsyncClient(
            base_url="https://api.groq.com/openai/v1",
            headers={"Authorization": f"Bearer {config.api.groq_api_key}"}
        ) as client:
            response = await client.get("/models")
            if response.status_code == 200:
                print("✅ Groq API OK")
                return True
            else:
                print(f"❌ Groq API erro: {response.status_code}")
                return False
    except Exception as e:
        print(f"❌ Erro Groq API: {e}")
        return False

async def test_telegram_api():
    """Testar conexão com Telegram API"""
    try:
        import telegram
        from telegram import Bot
        
        bot = Bot(token=config.api.telegram_token)
        info = await bot.get_me()
        print(f"✅ Telegram OK - Bot: {info.username}")
        return True
    except Exception as e:
        print(f"❌ Erro Telegram API: {e}")
        return False

async def test_gmail_api():
    """Testar conexão com Gmail API"""
    try:
        from jarvis_server import EmailService
        
        email_service = EmailService()
        if email_service.gmail_service:
            print("✅ Gmail API OK")
            return True
        else:
            print("❌ Gmail API falhou")
            return False
    except Exception as e:
        print(f"❌ Erro Gmail API: {e}")
        return False

async def test_contacts_api():
    """Testar conexão com People API (Google Contatos)"""
    try:
        from jarvis_server import EmailService, ContactsService
        
        email_service = EmailService()
        contacts_service = ContactsService(email_service)
        if contacts_service.people_service:
            print("✅ Google Contacts API OK")
            return True
        else:
            print("❌ Google Contacts API falhou (serviço não inicializado)")
            return False
    except Exception as e:
        print(f"❌ Erro Google Contacts API: {e}")
        return False

async def test_ai_service():
    """Testar serviço de IA"""
    try:
        from jarvis_server import AIService
        
        ai_service = AIService()
        result = await ai_service.process_command("test")
        
        if result and "action" in result:
            print("✅ Serviço de IA OK")
            return True
        else:
            print("❌ Serviço de IA falhou")
            return False
    except Exception as e:
        print(f"❌ Erro serviço de IA: {e}")
        return False

async def test_email_command():
    """Testar comando de email"""
    try:
        from jarvis_server import JarvisService
        
        jarvis = JarvisService()
        result = await jarvis.execute_command("test", "123")
        
        if result and "response" in result:
            print("✅ Comando de email OK")
            return True
        else:
            print("❌ Comando de email falhou")
            return False
    except Exception as e:
        print(f"❌ Erro comando de email: {e}")
        return False

async def run_tests():
    """Executar todos os testes"""
    print("🧪 Testes do JARVIS 2.0")
    print("=" * 25)
    
    tests = [
        ("Importações", test_imports),
        ("Groq API", test_groq_api),
        ("Telegram API", test_telegram_api),
        ("Gmail API", test_gmail_api),
        ("Google Contacts API", test_contacts_api),
        ("Serviço de IA", test_ai_service),
        ("Comando de Email", test_email_command),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        if asyncio.iscoroutinefunction(test_func):
            results[test_name] = await test_func()
        else:
            results[test_name] = test_func()
        
        # Pausa entre testes
        await asyncio.sleep(1)
    
    # Resumo
    print("\n📊 Resumo dos Testes")
    print("=" * 20)
    
    passed = 0
    total = len(tests)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\nResultado: {passed}/{total} testes passados")
    
    if passed == total:
        print("🎉 Todos os testes passaram! O JARVIS 2.0 está pronto para uso.")
        return True
    else:
        print("⚠️  Alguns testes falharam. Verifique a configuração.")
        return False

def main():
    """Função principal"""
    # Verificar se estamos no diretório correto
    if not os.path.exists("jarvis_server.py"):
        print("❌ Execute este script no diretório do JARVIS 2.0")
        return
    
    # Verificar arquivo .env
    if not os.path.exists(".env"):
        print("⚠️  Arquivo .env não encontrado. Execute setup.py primeiro.")
        return
    
    # Executar testes
    try:
        import asyncio
        result = asyncio.run(run_tests())
        
        if result:
            print("\n🚀 Próximos passos:")
            print("1. Execute: python start.py")
            print("2. Acesse: http://localhost:8000/docs")
            print("3. Teste o bot do Telegram")
        else:
            print("\n🔧 Corrija os problemas antes de usar o sistema.")
            
    except KeyboardInterrupt:
        print("\n🛑 Testes interrompidos")
    except Exception as e:
        print(f"❌ Erro durante testes: {e}")

if __name__ == "__main__":
    main()