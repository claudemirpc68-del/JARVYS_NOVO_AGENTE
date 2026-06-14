import os
import shutil
from gradio_client import Client

def main():
    print("Conectando ao Space FLUX.1-schnell...")
    try:
        client = Client("KingNish/Realtime-FLUX")
        print("Fazendo requisição de geração de imagem...")
        
        prompt = "a majestic futuristic robot standing in a cyberpunk city street, glowing lights, highly detailed, 8k resolution"
        
        result_tuple = client.predict(
            prompt=prompt,
            seed=0,
            width=1024,
            height=1024,
            api_name="/generate_image"
        )
        
        # O resultado é uma tupla (result_dict, seed)
        print(f"Tupla de retorno: {result_tuple}")
        
        result_image_path = result_tuple[0]
        seed_used = result_tuple[1]
        latency_str = result_tuple[2]
        
        print(f"Seed utilizada: {seed_used}")
        print(f"Latência reportada: {latency_str}")
        print(f"Caminho temporário: {result_image_path}")
        
        if result_image_path and os.path.exists(result_image_path):
            output_dest = "scratch/test_flux_result.webp"
            shutil.copy(result_image_path, output_dest)
            print(f"\n[SUCESSO] Imagem gerada e copiada para {output_dest}")
            print(f"Tamanho do arquivo: {os.path.getsize(output_dest) / 1024:.1f} KB")
        else:
            print(f"\n[ERRO] O caminho temporário da imagem não existe ou é inválido: {result_image_path}")
            
    except Exception as e:
        import traceback
        print("\n[ERRO] Ocorreu uma excecao detalhada abaixo:")
        traceback.print_exc()

if __name__ == "__main__":
    main()
