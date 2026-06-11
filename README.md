# JARVIS 2.0 - Assistente de Email Inteligente

🤖 Uma implementação alternativa do JARVIS 2.0 sem n8n, construída com Python, FastAPI e Groq API.

## 🚀 Funcionalidades

- **Gestão de Emails**: Envio, resposta, busca e organização de emails
- **Interface Telegram**: Controle via chatbot do Telegram
- **IA com Groq**: Processamento inteligente de comandos naturais
- **Formatação Profissional**: Emails em HTML com assinatura padrão
- **Automação Inteligente**: Seleção automática de ações baseada em contexto

## 📁 Estrutura do Projeto

```
JARVIS_2.0/
├── jarvis_server.py      # Servidor FastAPI principal
├── telegram_bot.py      # Bot do Telegram
├── setup.py            # Script de configuração inicial
├── requirements.txt   # Dependências Python
├── .env.example       # Modelo de variáveis de ambiente
└── README.md          # Este arquivo
```

## 🔧 Configuração Inicial

### 1. Pré-requisitos
- Python 3.8+
- Conta Google (para Gmail API)
- Conta Groq (para API IA)
- Bot Telegram

### 2. Instalação das Dependências
```bash
pip install -r requirements.txt
```

### 3. Configuração das Credenciais

#### Google API
1. Acesse [Google Cloud Console](https://console.cloud.google.com/)
2. Crie um novo projeto
3. Ative as APIs: **Gmail API**, **Google Drive API** (opcional)
4. Crie credenciais OAuth 2.0:
   - Tipo: "Web application"
   - URIs de redirecionamento: `http://localhost:8000`
5. Baixe o arquivo `credentials.json`

#### Groq API
1. Acesse [Groq Console](https://console.groq.com/)
2. Crie sua conta e obtenha a API Key
3. Adicione ao arquivo `.env`

#### Telegram Bot
1. Crie um bot no [@BotFather](https://t.me/BotFather)
2. Copie o token
3. Adicione ao arquivo `.env`

### 4. Configuração do Ambiente
```bash
python setup.py
```

Este script irá:
- Copiar `credentials.json` para o diretório do projeto
- Criar arquivo `.env` a partir do exemplo
- Configurar variáveis de ambiente

### 5. Variáveis de Ambiente
Crie/edite o arquivo `.env`:

```env
# API Keys
GROQ_API_KEY=sua_chave_groq_aqui
TELEGRAM_TOKEN=seu_token_telegram_aqui

# Google API Credentials
GOOGLE_CREDENTIALS_PATH=credentials.json
GOOGLE_TOKEN_PATH=token.json

# User Configuration
USER_ID=seu_id_telegram_aqui

# Server Configuration
HOST=0.0.0.0
PORT=8000
```

## 🚀 Execução

### 1. Servidor Principal
```bash
python jarvis_server.py
```

Servidor estará disponível em: `http://localhost:8000`

#### Endpoints Disponíveis
- `POST /api/email-command` - Processar comandos de email
- `POST /api/telegram-command` - Processar comandos do Telegram
- `GET /api/status` - Status do sistema

### 2. Bot do Telegram
```bash
python telegram_bot.py
```

### 3. Acessar a API
- Swagger UI: `http://localhost:8000/docs`
- Alternativo: `http://localhost:8000/redoc`

## 💻 Comandos Disponíveis

### Comandos do Telegram
- `/start` - Mensagem de boas-vindas
- `/help` - Ajuda detalhada
- `/status` - Status do sistema

### Comandos de Email (em linguagem natural)
- **Enviar email**: "Envia um email para joao@exemplo.com assunto reunião corpo da mensagem"
- **Buscar emails**: "Busca emails do João" ou "Busca os últimos 5 emails"
- **Criar rascunho**: "Cria rascunho para maria@empresa.com assunto proposta corpo da mensagem"
- **Responder email**: "Responde ao último email sobre a proposta"
- **Marcar como não lido**: "Marca o último email como não lido"
- **Adicionar etiqueta**: "Adiciona etiqueta importante ao email do João"

## 🔄 Fluxo de Trabalho

1. **Receber Comando**: Via Telegram ou API
2. **Processar IA**: Groq interpreta a linguagem natural
3. **Selecionar Ação**: IA escolhe a ferramenta apropriada
4. **Executar**: Ação é realizada via Gmail API
5. **Resposta**: Resultado é enviado de volta ao usuário

## 🛠️ Desenvolvimento

### Adicionar Novas Ações
1. Adicionar método na classe `JarvisService`
2. Atualizar o prompt do sistema em `AService._get_system_prompt`
3. Adicionar endpoint correspondente se necessário

### Estrutura de Pastas (Sugestão)
```
JARVIS_2.0/
├── src/
│   ├── __init__.py
│   ├── core/
│   │   ├── jarvis_service.py
│   │   ├── ai_service.py
│   │   └── email_service.py
│   ├── api/
│   │   ├── routes.py
│   │   └── models.py
│   └── utils/
│       ├── config.py
│       └── helpers.py
├── tests/
├── config/
├── logs/
└── data/
```

## 🐛 Troubleshooting

### Erros Comuns

**1. Erro de autenticação Gmail**
```
google.auth.exceptions.RefreshError: invalid_grant
```
Solução: Excluir `token.json` e executar novamente para obter novo token OAuth.

**2. Erro de API Key Groq**
```
groq.core.RateLimitError: Rate limit exceeded
```
Solução: Verificar API Key e limites de uso da Groq.

**3. Bot não responde**
Solução: Verificar token Telegram e se o bot pode enviar mensagens.

### Logs
Os logs são gerados no console. Para salvar em arquivo:
```bash
python jarvis_server.py > jarvis.log 2>&1
```

## 📈 Melhorias Futuras

- [ ] Interface web para gerenciamento
- [ ] Suporte a outros provedores de email
- [ ] Integração com calendário
- [ ] Agendamento de emails
- [ ] Análise de sentimentos de emails
- [ ] Templates de emails
- [ ] Sistema de autenticação de usuários
- [ ] Logs detalhados e monitoramento

## 🔒 Segurança

- Nunca compartilhe suas credenciais
- Use HTTPS em produção
- Rotacione tokens regularmente
- Restrinja escopos das APIs do Google
- Valide inputs dos usuários

## 📞 Suporte

Para dúvidas ou sugestões:
- Crie uma issue no repositório
- Verifique os logs para erros
- Teste com credenciais dummy primeiro

---

💡 **Dica**: Comece testando com o servidor primeiro antes de iniciar o bot Telegram para garantir que tudo está funcionando corretamente.
