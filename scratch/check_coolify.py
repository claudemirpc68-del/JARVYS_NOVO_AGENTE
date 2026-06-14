import os
import sys
import httpx
from pathlib import Path

# Adicionar raiz do projeto ao path
project_root = Path(r"c:\Users\FAMÍLIA\Desktop\NOVO_AGENTE")
env_path = project_root / ".env"

# Parser manual do .env
coolify_url = "http://72.61.130.70:8000"
coolify_token = ""

if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, val = line.split("=", 1)
            key = key.strip()
            val = val.strip()
            if key == "COOLIFY_URL":
                coolify_url = val
            elif key == "COOLIFY_TOKEN":
                coolify_token = val

async def main():
    app_uuid = "x48pzjbo1a4q0nlxr9v6e2ah"
    
    if not coolify_token:
        print("[ERRO] COOLIFY_TOKEN nao encontrado no .env local.")
        return
        
    headers = {
        "Authorization": f"Bearer {coolify_token}",
        "Accept": "application/json"
    }
    
    print(f"Conectando ao Coolify: {coolify_url}")
    print(f"Buscando status detalhado da aplicacao {app_uuid}...")
    
    async with httpx.AsyncClient() as client:
        # 1. Consultar status detalhado
        try:
            resp = await client.get(f"{coolify_url}/api/v1/applications/{app_uuid}", headers=headers, timeout=15.0)
            if resp.status_code == 200:
                app_info = resp.json()
                print("\n[INFO DETALHADA DO APP]")
                print(f" Nome: {app_info.get('name')}")
                print(f" Repository: {app_info.get('git_repository')} (branch: {app_info.get('git_branch')})")
                print(f" FQDN: {app_info.get('fqdn')}")
                print(f" Status: {app_info.get('status')}")
                print(f" Base Directory: {app_info.get('base_directory')}")
            else:
                print(f"Nao foi possivel obter detalhes: Status {resp.status_code} - {resp.text}")
        except Exception as e:
            print(f"Erro ao obter detalhes do app: {e}")

        # 2. Forcar redeploy
        print(f"\nDisparando o redeploy da aplicacao {app_uuid} no Coolify...")
        deploy_urls = [
            # Tentar o endpoint geral /deploy?uuid=... (comum no Coolify)
            f"{coolify_url}/api/v1/deploy?uuid={app_uuid}&force=true",
            # Rota alternativa
            f"{coolify_url}/api/v1/applications/{app_uuid}/deploy"
        ]
        
        success = False
        for url in deploy_urls:
            try:
                print(f"Tentando endpoint: {url}")
                if "applications" in url:
                    resp = await client.post(url, headers=headers, timeout=15.0)
                else:
                    resp = await client.get(url, headers=headers, timeout=15.0)
                
                if resp.status_code in [200, 201, 202]:
                    print(f"✅ SUCESSO: Deploy disparado! Resposta ({resp.status_code}): {resp.text}")
                    success = True
                    break
                else:
                    print(f"❌ Falha no endpoint: Status {resp.status_code} - {resp.text}")
            except Exception as e:
                print(f"Erro no endpoint: {e}")
                
        if not success:
            print("\n[ERRO] Nao foi possivel disparar o redeploy automaticamente. Verifique os logs ou o painel do Coolify.")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
