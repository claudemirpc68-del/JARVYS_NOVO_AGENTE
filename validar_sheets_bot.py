import os
import sys
import io

# Forçar codificação UTF-8 na saída
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Adicionar a pasta do projeto ao path de busca do Python para permitir importar as tools
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools.customer_sheets_tool import get_sheets_summary, search_customer_by_name, add_customer_record

def rodar_validacao():
    print("==================================================")
    print("🧪 INICIANDO VALIDAÇÃO DE CONEXÃO E SKILL DO SHEETS")
    print("==================================================")
    
    # 1. Testar conexão e resumo estatístico
    print("\n1. Testando leitura e resumo estatístico da planilha...")
    resumo, err = get_sheets_summary()
    if err:
        print(f"❌ ERRO na leitura: {err}")
        return
    print("✅ Sucesso na leitura!")
    print("--------------------------------------------------")
    print(resumo)
    print("--------------------------------------------------")
    
    # 2. Testar busca de clientes
    print("\n2. Testando busca de clientes na planilha por 'Juana'...")
    busca, err = search_customer_by_name("Juana")
    if err:
        print(f"❌ ERRO na busca: {err}")
        return
    print("✅ Sucesso na busca!")
    print("--------------------------------------------------")
    print(busca)
    print("--------------------------------------------------")
    
    # 3. Testar inserção e higienização
    print("\n3. Testando cadastro e higienização de novo cliente...")
    # Teste de inversão de nome com vírgula e inicial com ponto, gênero masculino e data em formato alternativo
    nome_teste = "silva, carlos b."
    genero_teste = "masculino"
    nascimento_teste = "15-08-1995"
    
    print(f"Enviando dados brutos: '{nome_teste}', '{genero_teste}', '{nascimento_teste}'...")
    res_cadastro, err = add_customer_record(nome_teste, genero_teste, nascimento_teste)
    if err:
        print(f"❌ ERRO no cadastro: {err}")
        return
    print("✅ Sucesso no cadastro e higienização!")
    print("--------------------------------------------------")
    print(res_cadastro)
    print("==================================================")
    print("🎉 TODOS OS TESTES DA SKILL DO SHEETS PASSARAM!")
    print("==================================================")

if __name__ == "__main__":
    rodar_validacao()
