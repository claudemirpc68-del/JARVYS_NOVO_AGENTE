import asyncio
import os
import sys

project_root = r"c:\Users\FAMÍLIA\Desktop\NOVO_AGENTE"
if project_root not in sys.path:
    sys.path.insert(0, project_root)
os.chdir(project_root)

from harness.orchestrator import JarvisOrchestrator

async def test_consecutive():
    orchestrator = JarvisOrchestrator()
    chat_id = 88888
    
    # 1. Limpar memoria anterior para o chat de teste
    orchestrator.memory.clear_history(chat_id)
    
    # 2. Simular Turno 1: Pedido de imagem
    print("--- Simulando Turno 1: Usuário pede imagem ---")
    user_msg1 = "Gera uma imagem de um gato de cartola"
    orchestrator.update_memory(chat_id, "user", user_msg1)
    
    # Classificar Turno 1
    result1 = await orchestrator.classify_intent(chat_id, user_msg1, save_to_history=False)
    print(f"Resultado Classificacao Turno 1: {result1}")
    
    # Adicionar resposta simulada do assistente (imagem gerada)
    assistant_msg1 = "🎨 Aqui está a imagem gerada para: a cute cat wearing a top hat, digital art, vibrant colors, studio lighting"
    orchestrator.update_memory(chat_id, "assistant", assistant_msg1)
    
    # 3. Simular Turno 2: Agradecimento do usuário ("perfeito")
    print("\n--- Aguardando 20 segundos para evitar Rate Limit (TPM) ---")
    await asyncio.sleep(20)
    print("--- Simulando Turno 2: Usuário agradece dizendo 'perfeito' ---")
    user_msg2 = "perfeito"
    
    # Classificar Turno 2 (vai ler o historico que criamos na memoria)
    result2 = await orchestrator.classify_intent(chat_id, user_msg2, save_to_history=True)
    print(f"Resultado Classificacao Turno 2: {result2}")
    
    # Verificar se a acao classificada foi chat
    action = result2.get("action")
    if action == "chat":
        print("\n[OK] SUCESSO! A acao foi classificada corretamente como 'chat'.")
    else:
        print(f"\n[FALHA] A acao foi classificada incorretamente como '{action}'. Deveria ser 'chat'.")

if __name__ == "__main__":
    asyncio.run(test_consecutive())
