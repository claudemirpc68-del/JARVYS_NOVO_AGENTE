import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime

# Configurar stdout e stderr para usar UTF-8 no Windows
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        import codecs
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
        sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())

# Garantir que a raiz do projeto esteja no path
project_root = str(Path(__file__).parent.resolve())
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Mudar o diretório de trabalho para a raiz do projeto
os.chdir(project_root)

from harness.orchestrator import JarvisOrchestrator
from harness.logger import logger

async def run_test_case(orchestrator, chat_id, title, user_input, validation_fn):
    print(f"\n[TESTANDO] {title}")
    print(f"  Entrada: '{user_input}'")
    try:
        result = await orchestrator.process(chat_id, user_input)
        response_text = result.get("response", "")
        
        # Se for uma ação que não retornou chat geral direto
        if not response_text:
            response_text = str(result)
            
        print(f"  Saída: {response_text[:120]}...")
        
        # Atualizar a memória do chat com a resposta final do assistente (JARVIS), simulando o bot real
        orchestrator.update_memory(chat_id, "assistant", response_text)
        
        # Delay de 5.5 segundos para respeitar a taxa de requisições de tokens do Groq
        await asyncio.sleep(5.5)
        
        is_pass, reason = validation_fn(response_text, result)
        if is_pass:
            print(f"  Status: ✅ PASS")
            return True, response_text
        else:
            print(f"  Status: ❌ FAIL (Motivo: {reason})")
            return False, response_text
    except Exception as e:
        print(f"  Status: ❌ FAIL (Exceção: {e})")
        await asyncio.sleep(5.5)
        return False, str(e)

async def main():
    print("==================================================")
    print("  INICIANDO CHECKLIST DE VALIDAÇÃO AUTOMATIZADO   ")
    print("==================================================")
    
    orchestrator = JarvisOrchestrator()
    
    # Usando IDs de chat diferentes por seção para evitar rate limiting local
    chat_persona = 888888001
    chat_geral = 888888002
    chat_gmail = 888888004
    chat_calendar = 888888005
    chat_contacts = 888888006
    chat_web = 888888007
    chat_linkedin = 888888008
    
    results = {}
    
    # ----------------------------------------------------
    # SEÇÃO 1: Persona e Contexto Temporal
    # ----------------------------------------------------
    
    # Teste 1.1: Oi -> Deve saudar com "Claudemir"
    results["1.1"] = await run_test_case(
        orchestrator, chat_persona,
        "1.1 Saudação e nome do usuário",
        "Oi",
        lambda text, res: ("Claudemir" in text, "Não mencionou 'Claudemir' na resposta")
    )
    
    # Teste 1.2: Quem é você -> Se apresentar como JARVIS
    results["1.2"] = await run_test_case(
        orchestrator, chat_persona,
        "1.2 Identificação de Persona",
        "Quem é você?",
        lambda text, res: ("jarvis" in text.lower() or "assistente" in text.lower(), "Não se identificou como JARVIS ou assistente")
    )
    
    # Teste 1.3: Que dia é hoje -> Trazer a data/dia da semana
    today_weekday = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"][datetime.now().weekday()]
    results["1.3"] = await run_test_case(
        orchestrator, chat_persona,
        "1.3 Contexto temporal (dia atual)",
        "Que dia é hoje?",
        lambda text, res: (today_weekday in text.lower(), f"Não citou o dia da semana atual ('{today_weekday}')")
    )
    
    # ----------------------------------------------------
    # SEÇÃO 2: Conversa Geral e Memória
    # ----------------------------------------------------
    
    # Teste 2.1: Curiosidade
    results["2.1"] = await run_test_case(
        orchestrator, chat_geral,
        "2.1 Curiosidade de tecnologia",
        "Me conte uma curiosidade sobre tecnologia",
        lambda text, res: (len(text) > 20, "Resposta curta demais ou vazia")
    )
    
    # Teste 2.2: Explicação Power BI
    results["2.2"] = await run_test_case(
        orchestrator, chat_geral,
        "2.2 Explicação conceitual",
        "O que é Power BI?",
        lambda text, res: ("dados" in text.lower() or "microsoft" in text.lower() or "análise" in text.lower() or "bi" in text.lower(), "Não explicou conceitos chaves do Power BI")
    )
    
    # Teste 2.3: Memória e Contexto de Conversa
    # Passo A: Injetar dado de preferência
    await orchestrator.process(chat_geral, "Meu prato favorito é lasanha de presunto e queijo")
    await asyncio.sleep(5.5)
    
    # Passo B: Perguntar de volta
    results["2.3"] = await run_test_case(
        orchestrator, chat_geral,
        "2.3 Retenção de contexto na memória",
        "Qual é o meu prato favorito?",
        lambda text, res: ("lasanha" in text.lower(), "Não lembrou do prato favorito (lasanha)")
    )
    
    # ----------------------------------------------------
    # SEÇÃO 4: Gmail
    # ----------------------------------------------------
    
    # Teste 4.1: Listagem de e-mails
    results["4.1"] = await run_test_case(
        orchestrator, chat_gmail,
        "4.1 Listagem de e-mails (Gmail)",
        "Mostre meus últimos 5 e-mails",
        lambda text, res: ("últimos e-mails" in text.lower() or "caixa de entrada" in text.lower() or "remetente" in text.lower() or "@" in text, "Não retornou a lista de e-mails do Gmail")
    )
    
    # Teste 4.3: Envio de e-mail com aprovação (Segurança)
    results["4.3"] = await run_test_case(
        orchestrator, chat_gmail,
        "4.3 Validação de segurança no envio de e-mail",
        "Envie um e-mail para Joelma com assunto 'Teste JARVIS' dizendo 'Olá'",
        lambda text, res: ("confirma" in text.lower() or "preparei o e-mail" in text.lower() or "assunto" in text.lower(), "Não barrou solicitando aprovação/confirmação explícita")
    )
    
    # ----------------------------------------------------
    # SEÇÃO 5: Calendário
    # ----------------------------------------------------
    
    # Teste 5.1: Agenda do dia
    results["5.1"] = await run_test_case(
        orchestrator, chat_calendar,
        "5.1 Consulta de agenda de compromissos",
        "O que tenho na minha agenda hoje?",
        lambda text, res: ("compromissos" in text.lower() or "agenda" in text.lower() or "nenhum compromisso" in text.lower(), "Falha ao ler agenda de compromissos")
    )
    
    # Teste 5.3: Criar compromisso
    results["5.3"] = await run_test_case(
        orchestrator, chat_calendar,
        "5.3 Criação de compromisso no calendário",
        "Agende uma reunião chamada 'Teste JARVIS Automático' amanhã às 10h",
        lambda text, res: ("evento criado" in text.lower() or "sucesso" in text.lower() or "htmllink" in text.lower() or "http" in text.lower(), "Não confirmou a criação do compromisso")
    )
    
    # ----------------------------------------------------
    # SEÇÃO 6: Contatos
    # ----------------------------------------------------
    
    # Teste 6.1: Buscar contato real/existente (Joelma)
    results["6.1"] = await run_test_case(
        orchestrator, chat_contacts,
        "6.1 Busca de contato existente",
        "Buscar contato Joelma",
        lambda text, res: ("joelma" in text.lower() or "contato" in text.lower(), "Não retornou informações sobre o contato Joelma")
    )
    
    # Teste 6.2: Buscar contato inexistente
    results["6.2"] = await run_test_case(
        orchestrator, chat_contacts,
        "6.2 Busca de contato inexistente",
        "Buscar contato XYZ123Inexistente",
        lambda text, res: ("não encontrado" in text.lower() or "não encontrei" in text.lower() or "nenhum contato" in text.lower(), "Não informou que o contato não foi encontrado")
    )
    
    # ----------------------------------------------------
    # SEÇÃO 7: Pesquisa Web
    # ----------------------------------------------------
    
    # Teste 7.1: Pesquisa no Tavily
    results["7.1"] = await run_test_case(
        orchestrator, chat_web,
        "7.1 Pesquisa web em tempo real (Tavily)",
        "Qual a previsão do tempo em Curitiba hoje?",
        lambda text, res: ("curitiba" in text.lower() or "tempo" in text.lower() or "graus" in text.lower() or "previsão" in text.lower() or "clima" in text.lower(), "Não retornou informações sobre o tempo em Curitiba")
    )
    
    # ----------------------------------------------------
    # SEÇÃO 8: LinkedIn Content Creator
    # ----------------------------------------------------
    
    # Teste 8.1: Post LinkedIn
    results["8.1"] = await run_test_case(
        orchestrator, chat_linkedin,
        "8.1 Geração de Post LinkedIn (Power BI)",
        "Crie um post para LinkedIn sobre os benefícios do Power BI para pequenas empresas",
        lambda text, res: (len(text) > 50 and ("power bi" in text.lower() or "dados" in text.lower() or "aviso" in text.lower()), "Não gerou o post viral ou não mencionou o tema")
    )
    
    # Teste 8.2: Artigo LinkedIn
    results["8.2"] = await run_test_case(
        orchestrator, chat_linkedin,
        "8.2 Geração de Artigo Técnico LinkedIn",
        "Escreva um artigo técnico sobre a importância de clean code em Python",
        lambda text, res: (("clean code" in text.lower() or "código limpo" in text.lower() or "aviso" in text.lower()) and ("python" in text.lower() or "código" in text.lower()), "Não gerou o artigo técnico de forma adequada")
    )

    # ----------------------------------------------------
    # RELATÓRIO CONSOLIDADO E ATUALIZAÇÃO DO CHECKLIST
    # ----------------------------------------------------
    
    print("\n==================================================")
    print("               RESUMO DA VALIDAÇÃO                ")
    print("==================================================")
    
    passed_count = 0
    failed_count = 0
    
    for k, v in results.items():
        is_pass, _ = v
        status_icon = "✅ PASS" if is_pass else "❌ FAIL"
        print(f"Teste {k}: {status_icon}")
        if is_pass:
            passed_count += 1
        else:
            failed_count += 1
            
    print(f"\nTotal Passados: {passed_count}/{len(results)}")
    print(f"Total Falhados: {failed_count}/{len(results)}")
    print("==================================================")

    # Caminho absoluto correto para o artefato da conversa
    checklist_path = Path(r"C:\Users\FAMÍLIA\.gemini\antigravity\brain\06b1c27c-81b6-4bf0-98c4-15bac522d58c\checklist_validacao.md")
    
    if checklist_path.exists():
        content = checklist_path.read_text(encoding="utf-8")
        
        # Atualizar os status de checkboxes [ ] baseados no resultado do script
        for k, v in results.items():
            is_pass, _ = v
            new_checkbox = "x" if is_pass else " "
            pattern = rf"(\| {k} \|.*?\| )`\[ \]` (\|)"
            import re
            content = re.sub(pattern, rf"\1`[{new_checkbox}]` \2", content)
            
        # Atualizar a tabela de resumo
        sections_summary = {
            "Persona e Contexto": ["1.1", "1.2", "1.3"],
            "Texto (Geral)": ["2.1", "2.2", "2.3"],
            "E-mail": ["4.1", "4.3"],
            "Calendário": ["5.1", "5.3"],
            "Contatos": ["6.1", "6.2"],
            "Pesquisa Web": ["7.1"],
            "Criador de Conteúdo": ["8.1", "8.2"]
        }
        
        for section, keys in sections_summary.items():
            sect_passed = sum(1 for k in keys if results.get(k, (False, ""))[0])
            sect_failed = len(keys) - sect_passed
            
            sect_pattern = rf"(\| {section} \| \d+ \|) (\|) (\|)"
            import re
            content = re.sub(sect_pattern, rf"\1 {sect_passed} \2 {sect_failed} \3", content)
            
        # Atualizar o TOTAL final
        total_pattern = r"(\| \*\*TOTAL\*\* \| \*\*27\*\* \|) (\|) (\|)"
        import re
        content = re.sub(total_pattern, rf"\1 {passed_count} \2 {failed_count} \3", content)
        
        # Gravar de volta
        checklist_path.write_text(content, encoding="utf-8")
        print(f"Checklist atualizado com sucesso em: {checklist_path}")
    else:
        print(f"AVISO: Arquivo do artefato do checklist não encontrado em: {checklist_path}")

if __name__ == "__main__":
    asyncio.run(main())
