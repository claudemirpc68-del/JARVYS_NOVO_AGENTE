import os
import pandas as pd
import gspread
from datetime import datetime
from harness.logger import logger

# Caminho para o credentials.json na raiz do projeto (um nível acima da pasta tools/)
CREDENCIAIS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "credentials.json")
PLANILHA_NOME = "Cadastro Clientes Tratado"

def get_sheets_client():
    if not os.path.exists(CREDENCIAIS_PATH):
        logger.error(f"Arquivo de credenciais não encontrado em: {CREDENCIAIS_PATH}")
        return None
    try:
        return gspread.service_account(filename=CREDENCIAIS_PATH)
    except Exception as e:
        logger.error(f"Erro ao autenticar com o Google Sheets API: {e}")
        return None

def get_sheet():
    client = get_sheets_client()
    if not client:
        return None
    try:
        planilha = client.open(PLANILHA_NOME)
        return planilha.sheet1
    except Exception as e:
        logger.error(f"Erro ao abrir a planilha '{PLANILHA_NOME}': {e}")
        return None

# Funções de higienização e regras de negócio
def inverter_e_limpar_nome(nome):
    if not nome:
        return ""
    nome_str = str(nome).strip()
    if ',' in nome_str:
        partes = nome_str.split(',', 1)
        sobrenome = partes[0].strip().replace('.', '')
        nome_proprio = partes[1].strip()
        nome_completo = f"{nome_proprio} {sobrenome}"
        return " ".join([p.capitalize() for p in nome_completo.split()])
    return " ".join([p.capitalize() for p in nome_str.split()])

def limpar_genero(genero):
    if not genero:
        return ""
    g = str(genero).strip().upper()
    if g in ['M', 'F']:
        return g
    if 'MAS' in g or 'HOM' in g:
        return 'M'
    if 'FEM' in g or 'MUL' in g:
        return 'F'
    return ""

def calcular_idade(data_nascimento_dt):
    hoje = datetime.now()
    idade = hoje.year - data_nascimento_dt.year - ((hoje.month, hoje.day) < (data_nascimento_dt.month, data_nascimento_dt.day))
    return int(idade)

def definir_faixa_etaria(idade):
    if idade < 18:
        return "Menor de Idade"
    elif idade < 30:
        return "Jovem Adulto"
    elif idade < 60:
        return "Adulto"
    else:
        return "Idoso"

def get_sheets_summary() -> tuple[str | None, str | None]:
    aba = get_sheet()
    if not aba:
        return None, "Não foi possível conectar ao Google Sheets."
    try:
        # Ler todos os registros
        valores = aba.get_all_records()
        if not valores:
            return "📊 A planilha está vazia.", None
        
        df = pd.DataFrame(valores)
        total_clientes = len(df)
        
        # Estatísticas de Gênero
        gen_counts = df['Genero'].value_counts()
        masc = gen_counts.get('M', 0)
        fem = gen_counts.get('F', 0)
        
        # Estatísticas de Idade
        df['Idade'] = pd.to_numeric(df['Idade'], errors='coerce')
        idade_media = df['Idade'].mean()
        
        # Estatísticas de Faixa Etária
        faixas = df['Faixa Etaria'].value_counts()
        menor = faixas.get('Menor de Idade', 0)
        jovem = faixas.get('Jovem Adulto', 0)
        adulto = faixas.get('Adulto', 0)
        idoso = faixas.get('Idoso', 0)
        
        resumo = (
            f"📊 **Resumo Estatístico da Planilha de Clientes**\n\n"
            f"👥 **Total de Clientes:** {total_clientes}\n\n"
            f"👫 **Distribuição por Gênero:**\n"
            f"• Masculino (M): {masc} ({masc/total_clientes*100:.1f}%)\n"
            f"• Feminino (F): {fem} ({fem/total_clientes*100:.1f}%)\n\n"
            f"🎂 **Idade Média:** {idade_media:.1f} anos\n\n"
            f"👵 **Distribuição por Faixa Etária:**\n"
            f"• Menores de Idade (<18): {menor}\n"
            f"• Jovens Adultos (18-29): {jovem}\n"
            f"• Adultos (30-59): {adulto}\n"
            f"• Idosos (60+): {idoso}"
        )
        return resumo, None
    except Exception as e:
        logger.error(f"Erro ao obter resumo da planilha: {e}")
        return None, str(e)

def search_customer_by_name(query: str) -> tuple[str | None, str | None]:
    aba = get_sheet()
    if not aba:
        return None, "Não foi possível conectar ao Google Sheets."
    try:
        valores = aba.get_all_records()
        if not valores:
            return "🔍 A planilha está vazia.", None
        
        df = pd.DataFrame(valores)
        
        # Busca sem diferenciar maiúsculas/minúsculas
        query_clean = query.strip().lower()
        df_filtered = df[df['Nome Completo'].astype(str).str.lower().str.contains(query_clean)]
        
        total_encontrados = len(df_filtered)
        if total_encontrados == 0:
            return f"🔍 Nenhum cliente encontrado correspondente a **'{query}'**.", None
        
        linhas = []
        # Mostrar no máximo 10 correspondências para não estourar limite do Telegram
        for _, row in df_filtered.head(10).iterrows():
            linhas.append(
                f"• **ID {row['Id Cliente']}** — {row['Nome Completo']} ({row['Genero']}) | "
                f"Nasc: {row['Data de Nascimento']} | Idade: {row['Idade']} ({row['Faixa Etaria']})"
            )
            
        resposta = f"🔍 **Resultados para '{query}'** ({total_encontrados} encontrados):\n\n" + "\n".join(linhas)
        if total_encontrados > 10:
            resposta += f"\n\n_(Exibindo as primeiras 10 correspondências)_"
            
        return resposta, None
    except Exception as e:
        logger.error(f"Erro ao buscar cliente: {e}")
        return None, str(e)

def add_customer_record(name: str, gender: str, birth_date_str: str) -> tuple[str | None, str | None]:
    aba = get_sheet()
    if not aba:
        return None, "Não foi possível conectar ao Google Sheets."
    try:
        # 1. Higienizar e Validar Nome
        nome_limpo = inverter_e_limpar_nome(name)
        if not nome_limpo:
            return None, "Nome inválido ou vazio."
            
        # 2. Higienizar e Validar Gênero
        gen_limpo = limpar_genero(gender)
        if not gen_limpo:
            return None, "Gênero inválido. Use 'M' ou 'F'."
            
        # 3. Validar e Formatar Data de Nascimento
        dt = None
        for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y'):
            try:
                dt = datetime.strptime(birth_date_str.strip(), fmt)
                break
            except ValueError:
                continue
                
        if not dt:
            return None, "Formato de data inválido. Use DD/MM/AAAA."
            
        data_nascimento = dt.strftime('%d/%m/%Y')
        
        # 4. Calcular Idade e Faixa Etária
        idade = calcular_idade(dt)
        faixa = definir_faixa_etaria(idade)
        
        # 5. Obter próximo ID
        valores = aba.get_all_values()
        if len(valores) <= 1:
            proximo_id = 1
        else:
            try:
                # O ID é a primeira coluna do último elemento
                proximo_id = int(valores[-1][0]) + 1
            except ValueError:
                proximo_id = len(valores)
                
        nova_linha = [proximo_id, nome_limpo, gen_limpo, data_nascimento, idade, faixa]
        
        logger.info(f"Adicionando cliente ao Sheets: {nova_linha}")
        aba.append_row(nova_linha)
        
        resposta = (
            f"✅ **Cliente registrado com sucesso no Google Sheets!**\n\n"
            f"🆔 **ID do Cliente:** {proximo_id}\n"
            f"👤 **Nome Completo:** {nome_limpo}\n"
            f"👫 **Gênero:** {gen_limpo}\n"
            f"📅 **Data de Nascimento:** {data_nascimento}\n"
            f"🎂 **Idade:** {idade} anos\n"
            f"👵 **Faixa Etária:** {faixa}"
        )
        return resposta, None
        
    except Exception as e:
        logger.error(f"Erro ao adicionar cliente ao Sheets: {e}")
        return None, str(e)
