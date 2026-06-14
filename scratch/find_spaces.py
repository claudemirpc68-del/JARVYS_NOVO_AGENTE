from huggingface_hub import HfApi

def main():
    api = HfApi()
    print("Buscando Spaces populares de geracao de imagem...")
    
    # Buscar spaces com termo 'flux' ou 'schnell' ou 'sdxl'
    spaces = api.list_spaces(
        filter="stable-diffusion",
        sort="likes",
        limit=20
    )
    
    print("\nSpaces de Geração de Imagem Populares:")
    for space in spaces:
        stage = "UNKNOWN"
        if getattr(space, 'runtime', None) is not None:
            stage = getattr(space.runtime, 'stage', 'UNKNOWN')
        print(f"ID: {space.id} | Likes: {space.likes} | Status: {stage}")
        
    print("\nBuscando especificamente por 'flux'...")
    flux_spaces = api.list_spaces(
        search="flux",
        sort="likes",
        limit=20
    )
    
    print("\nSpaces contendo 'flux':")
    for space in flux_spaces:
        stage = "UNKNOWN"
        if getattr(space, 'runtime', None) is not None:
            stage = getattr(space.runtime, 'stage', 'UNKNOWN')
        print(f"ID: {space.id} | Likes: {space.likes} | Status: {stage}")

if __name__ == "__main__":
    main()
