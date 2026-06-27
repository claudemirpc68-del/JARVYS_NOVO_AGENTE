# JARVIS 2.0 - Gerenciador de Planilha de Clientes (IA & Telegram)

🤖 Uma implementação inteligente do **JARVIS 2.0** integrada ao Telegram, construída com Python e conectada diretamente à API do Google Sheets para o gerenciamento de registros de clientes da planilha `"Cadastro Clientes Tratado"`.

O bot utiliza inteligência artificial multimodelo com suporte prioritário ao **Google Gemini 2.5 Flash** (e fallbacks para **Groq Llama 3** e **OpenRouter**), garantindo estabilidade, suporte a grandes contextos e respostas em tempo recorde.

---

## 🚀 Funcionalidades Principais

* **📊 Resumo Estatístico em Tempo Real:** Gera métricas demográficas instantâneas da base de clientes (total de clientes, contagem de gêneros M/F, idade média do público e distribuição por faixas etárias).
* **🔍 Busca Inteligente:** Localiza registros na tabela a partir de buscas parciais de nomes ou sobrenomes de clientes.
* **➕ Cadastro e Higienização Automática de Dados:** Cadastra novos clientes aplicando regras de padronização corporativa:
  - Inversão automática de nomes desordenados (ex: `"silva, carlos b."` ➔ `"Carlos B. Silva"`).
  - Padronização rigorosa do gênero (`M` ou `F`).
  - Formatação e validação de datas de nascimento no formato `DD/MM/AAAA`.
  - Cálculo preciso de idade com base no dia e mês corrente.
  - Classificação matemática da Faixa Etária (`Menor de Idade`, `Jovem Adulto`, `Adulto`, `Idoso`).
* **🗣️ Interação por Voz:** Suporta o recebimento e envio de notas de voz nativas no Telegram (usa Groq Whisper para transcrição e Edge TTS para falar de volta com você).

---

## 📁 Estrutura do Projeto

```text
JARVIS_2.0/
├── harness/
│   ├── orchestrator.py        # Orquestrador ReAct e classificação de intenções da IA
│   ├── memory.py              # Gerenciador de histórico e contexto persistente
│   └── security.py            # Sanitização e validação de segurança de entrada
├── tools/
│   ├── customer_sheets_tool.py# Lógica e integração com o Google Sheets API (gspread)
│   └── audio_tool.py          # Transcrição (Whisper) e síntese de voz (TTS)
├── llm_persona/
│   └── system_prompt.md       # Persona e regras JSON do agente focado em planilhas
├── telegram_bot.py            # Interface principal do bot do Telegram
├── validar_sheets_bot.py      # Script autônomo de testes de integração e conexão
├── inserir_ficticios.py       # Script de automação para inserção rápida de 10 clientes em lote
├── credentials.json           # Chave de acesso da conta de serviço Google (Ignorada no Git)
├── .env                       # Configuração de tokens e variáveis (Ignorada no Git)
└── requirements.txt           # Dependências Python do projeto
```

---

## 🔧 Configuração e Instalação

### 1. Pré-requisitos
* Python 3.10 ou superior.
* Conta no Telegram (Token obtido via [@BotFather](https://t.me/BotFather)).
* Google Cloud Console (Arquivo `credentials.json` habilitado para Google Sheets API e compartilhado como editor na sua planilha online).
* API Key do Google AI Studio (Gemini) ou Groq.

### 2. Configurando o Ambiente
Navegue até a pasta do projeto e instale as dependências:
```bash
# Ativar o ambiente virtual (.venv)
.venv\Scripts\activate

# Instalar as bibliotecas necessárias
pip install -r requirements.txt
```

### 3. Variáveis de Ambiente (`.env`)
Garanta que as seguintes variáveis estejam configuradas no seu arquivo `.env`:
```env
TELEGRAM_TOKEN=seu_token_telegram_aqui
GEMINI_API_KEY=sua_chave_gemini_aqui
GROQ_API_KEY=sua_chave_groq_aqui
```

---

## 🚀 Como Executar

### 1. Executando o Bot do Telegram
Para iniciar o bot e deixá-lo escutando comandos (texto e voz) no Telegram:
```bash
.venv\Scripts\python telegram_bot.py
```

### 2. Validar Conexão Local e Operações
Para rodar os testes de diagnóstico isolados de leitura, busca e gravação no Sheets:
```bash
.venv\Scripts\python validar_sheets_bot.py
```

### 3. Inserir Clientes Fictícios de Demonstração
Para rodar a automação em lote que insere 10 novos clientes fictícios higienizados na nuvem de uma única vez:
```bash
.venv\Scripts\python inserir_ficticios.py
```

---

## 💬 Exemplos de Uso no Telegram

* **Pedir estatísticas:** *"JARVIS, me dê um resumo estatístico da planilha."*
* **Pesquisar alguém:** *"Busque por 'Juana' na tabela."*
* **Cadastrar cliente:** *"Adicionar cliente Carlos Santos, masculino, nascido em 10/12/1985."*
