from gradio_client import Client

def main():
    print("Conectando ao Space sdxl-turbo...")
    try:
        client = Client("stabilityai/sdxl-turbo")
        print("\nConexao estabelecida com sucesso!")
        print("\nExibindo informacoes da API:")
        client.view_api()
    except Exception as e:
        print(f"Erro ao conectar ou ler API: {e}")

if __name__ == "__main__":
    main()
