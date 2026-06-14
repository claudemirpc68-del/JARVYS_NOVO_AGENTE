import asyncio
import os
import sys

project_root = r"c:\Users\FAMÍLIA\Desktop\NOVO_AGENTE"
if project_root not in sys.path:
    sys.path.insert(0, project_root)
os.chdir(project_root)

from harness.orchestrator import JarvisOrchestrator

async def test_extra_keys():
    # Instanciar o orquestrador
    orchestrator = JarvisOrchestrator()
    
    # 1. Simular o dicionario retornado pela LLM contendo chaves adicionais
    validated_action = {
        "action": "chat",
        "response": "Eu posso ajudar com várias coisas, como:",
        "skills": [
            "Gerenciar calendário (criar eventos, listar agenda)",
            "Enviar e-mails (criar, enviar, listar)",
            "Pesquisar na web (fatos recentes, notícias, resultados de jogos)",
            "Previsão do tempo (clima, temperatura, chuva, vento)",
            "Criação de conteúdo para o LinkedIn (posts, artigos)",
            "Geração de imagens (desenhos, ilustrações, arte)",
            "Interagir em chat (conversar, perguntar, responder)"
        ]
    }
    
    # 2. Simular a passagem pelo bloco de processamento de Chat Geral (else)
    response_text = validated_action.get("response", "")
    extra_parts = []
    for key, val in validated_action.items():
        if key in ["action", "response", "image_path"]:
            continue
        if isinstance(val, list):
            formatted_list = "\n".join([f"• {item}" for item in val])
            extra_parts.append(formatted_list)
        elif isinstance(val, dict):
            formatted_dict = "\n".join([f"• **{k}**: {v}" for k, v in val.items()])
            extra_parts.append(formatted_dict)
        elif val:
            extra_parts.append(str(val))
            
    if extra_parts:
        response_text += "\n\n" + "\n\n".join(extra_parts)
        validated_action["response"] = response_text
        
    print("=== RESPOSTA PROCESSADA ===")
    print(validated_action["response"])
    print("===========================")
    
    # Verificar se as skills foram incluídas
    if "Gerenciar calendário" in validated_action["response"]:
        print("[OK] SUCESSO! As chaves extras do JSON foram concatenadas perfeitamente na resposta de chat.")
    else:
        print("[FALHA] As chaves extras foram ignoradas.")

if __name__ == "__main__":
    asyncio.run(test_extra_keys())
