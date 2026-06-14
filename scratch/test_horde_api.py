import asyncio
import httpx
import json

async def test_horde():
    # URL da API
    base_url = "https://aihorde.net/api"
    
    # Headers recomendados pela AI Horde
    headers = {
        "apikey": "0000000000",
        "Client-Agent": "jarvis:2.0:telegrambot"
    }
    
    # Payload para gerar uma imagem
    payload = {
        "prompt": "a cute orange cat wearing a space suit, cartoon style, highly detailed",
        "params": {
            "n": 1,
            "width": 512,
            "height": 512,
            "steps": 20
        }
    }
    
    print("Enviando requisição para AI Horde...")
    async with httpx.AsyncClient() as client:
        try:
            # 1. Enviar requisição
            response = await client.post(
                f"{base_url}/v2/generate/async",
                headers=headers,
                json=payload,
                timeout=30
            )
            print(f"Status do POST: {response.status_code}")
            
            if response.status_code != 202:
                print("Erro ao iniciar geração:")
                print(response.text)
                return
                
            data = response.json()
            job_id = data.get("id")
            print(f"Job ID criado: {job_id}")
            
            if not job_id:
                print("Nenhum Job ID retornado.")
                return
                
            # 2. Polling de status
            for attempt in range(30): # Até 60 segundos
                await asyncio.sleep(2)
                
                status_response = await client.get(
                    f"{base_url}/v2/generate/status/{job_id}",
                    headers=headers,
                    timeout=30
                )
                
                if status_response.status_code != 200:
                    print(f"Erro ao verificar status (tentativa {attempt}): {status_response.status_code}")
                    continue
                    
                status_data = status_response.json()
                finished = status_data.get("finished", 0)
                done = status_data.get("done", False)
                faulted = status_data.get("faulted", False)
                wait_time = status_data.get("wait_time", 0)
                queue_pos = status_data.get("queue_position", 0)
                
                print(f"Tentativa {attempt}: finished={finished}, done={done}, faulted={faulted}, wait_time={wait_time}s, queue={queue_pos}")
                
                if faulted:
                    print("Geração falhou no AI Horde.")
                    break
                    
                if finished > 0 or done:
                    print("Geração concluída!")
                    print(json.dumps(status_data, indent=2))
                    
                    generations = status_data.get("generations", [])
                    if generations:
                        img_url = generations[0].get("img")
                        print(f"URL da Imagem: {img_url}")
                        
                        # Tentar baixar a imagem
                        img_response = await client.get(img_url, timeout=30)
                        if img_response.status_code == 200:
                            with open("test_horde_img.webp", "wb") as f:
                                f.write(img_response.content)
                            print("Imagem baixada e salva com sucesso em 'test_horde_img.webp'!")
                        else:
                            print(f"Erro ao baixar imagem: {img_response.status_code}")
                    break
            else:
                print("Timeout aguardando a geração da imagem.")
                
        except Exception as e:
            print(f"Erro durante o teste: {e}")

if __name__ == "__main__":
    asyncio.run(test_horde())
