import os
import json
import re
from datetime import datetime
from pathlib import Path
import httpx

from harness.logger import logger
from harness.memory import JarvisMemory
from harness.security import JarvisSecurity
from config import config

# Importar as ferramentas encapsuladas
import tools.gmail_tool as gmail
import tools.contacts_tool as contacts
import tools.calendar_tool as calendar
import tools.tavily_tool as tavily
import tools.linkedin_tool as linkedin
import tools.weather_tool as weather
import tools.image_tool as image

class JarvisOrchestrator:
    def __init__(self):
        self.memory = JarvisMemory()
        self.security = JarvisSecurity()
        self.groq_api_key = config.api.groq_api_key or os.environ.get("GROQ_API_KEY", "")
        self.openrouter_api_key = config.api.openrouter_api_key or os.environ.get("OPENROUTER_API_KEY", "")
        self.gemini_api_key = config.api.gemini_api_key or os.environ.get("GEMINI_API_KEY", "")
        
        # Caminho absoluto para o system prompt
        self.prompt_path = Path(__file__).parent.parent / "llm_persona" / "system_prompt.txt"
        
        # Carregar o prompt base
        if self.prompt_path.exists():
            self.base_prompt = self.prompt_path.read_text(encoding="utf-8")
            logger.info("Persona (system_prompt.txt) carregada com sucesso no Orquestrador.")
        else:
            logger.error(f"Arquivo de persona não encontrado em: {self.prompt_path}")
            self.base_prompt = "Você é o JARVIS 2.0. Responda em JSON."

    def update_memory(self, chat_id: int, role: str, content: str) -> None:
        """Interface para gerenciar e persistir o histórico de conversação do chat"""
        self.memory.add_message(chat_id, role, content)

    async def classify_intent(self, chat_id: int, text: str, save_to_history: bool = True, ignore_history: bool = False, force_json: bool = True) -> dict | str:
        """
        Classifica a intenção do usuário chamando o Groq API em formato JSON estruturado.
        Substitui dinamicamente as variáveis de prompt (data/hora e URL de auth).
        """
        # Dia da semana e fuso horário
        weekdays = ["segunda-feira", "terca-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sabado", "domingo"]
        today_weekday = weekdays[datetime.now().weekday()]
        datetime_now_str = datetime.now().strftime('%d/%m/%Y %H:%M')
        
        # URL de autenticação local do FastAPI
        auth_url = f"http://localhost:{config.server.port}/api/gmail/auth-url"
        
        # Formatar o prompt do sistema dinamicamente
        system_prompt = self.base_prompt.format(
            today_weekday=today_weekday,
            auth_url=auth_url,
            datetime_now=datetime_now_str
        )
        
        # Se for salvar na memória principal (fluxo padrão)
        if save_to_history:
            self.update_memory(chat_id, "user", text)
            
        history = [] if ignore_history else self.memory.get_history(chat_id)
        
        # Se save_to_history for False (ex: chamada recursiva da busca web),
        # incluímos a query de instrução temporariamente no payload enviado à API do Groq
        if save_to_history:
            messages = [{"role": "system", "content": system_prompt}] + history
        else:
            messages = [{"role": "system", "content": system_prompt}] + history + [{"role": "user", "content": text}]
            
        # Definir a cadeia de provedores a tentar
        attempts = []
        if self.openrouter_api_key:
            attempts.append(("openrouter", "meta-llama/llama-3.3-70b-instruct"))
        if self.groq_api_key:
            attempts.append(("groq", "llama-3.3-70b-versatile"))
            attempts.append(("groq", "llama-3.1-8b-instant"))
        if self.gemini_api_key:
            attempts.append(("gemini", "gemini-flash-latest"))

        last_error = None
        
        async with httpx.AsyncClient() as client:
            for provider, model_name in attempts:
                logger.info(f"Tentando classificar intenção com {provider} ({model_name})...")
                try:
                    if provider == "gemini":
                        result = await self._call_gemini_api(system_prompt, messages, force_json)
                        logger.info(f"Classificação com Gemini ({model_name}) realizada com sucesso.")
                        return result
                        
                    if provider == "openrouter":
                        url = "https://openrouter.ai/api/v1/chat/completions"
                        headers = {
                            "Authorization": f"Bearer {self.openrouter_api_key}",
                            "Content-Type": "application/json",
                            "HTTP-Referer": "https://github.com/claudemirpc68-del/jarvis-2.0",
                            "X-Title": "JARVIS 2.0"
                        }
                    else:  # groq
                        url = "https://api.groq.com/openai/v1/chat/completions"
                        headers = {
                            "Authorization": f"Bearer {self.groq_api_key}",
                            "Content-Type": "application/json"
                        }
                        
                    payload = {
                        "model": model_name,
                        "messages": messages,
                        "temperature": 0.7,
                        "max_tokens": 2048
                    }
                    if force_json:
                        payload["response_format"] = {"type": "json_object"}
                        
                    resp = await client.post(url, headers=headers, json=payload, timeout=30)
                    
                    if resp.status_code != 200:
                        logger.error(f"Erro na API {provider} ({model_name}): Status {resp.status_code} - {resp.text}")
                        raise Exception(f"API {provider} retornou status {resp.status_code}")
                        
                    content = resp.json()["choices"][0]["message"]["content"]
                    logger.debug(f"Retorno bruto de {provider} ({model_name}): {content}")
                    
                    if not force_json:
                        return content
                        
                    # Tentar carregar como JSON
                    try:
                        parsed_json = json.loads(content)
                    except json.JSONDecodeError as jde:
                        logger.warning(f"Falha ao parsear JSON direto de {provider}, tentando extrair bloco ou braces: {jde}")
                        # 1. Tentar extrair de blocos de código markdown
                        if "```" in content:
                            m = re.search(r'```(?:json)?\s*(.*?)\s*```', content, re.DOTALL)
                            if m:
                                try:
                                    parsed_json = json.loads(m.group(1).strip())
                                    return parsed_json
                                except json.JSONDecodeError:
                                    pass
                        # 2. Tentar encontrar braces
                        first_brace = content.find('{')
                        last_brace = content.rfind('}')
                        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
                            try:
                                parsed_json = json.loads(content[first_brace:last_brace+1])
                                return parsed_json
                            except json.JSONDecodeError:
                                pass
                        raise jde
                        
                    if isinstance(parsed_json, list) and len(parsed_json) > 0:
                        parsed_json = parsed_json[0]
                        
                    logger.info(f"Intenção classificada com {provider} ({model_name}): {parsed_json.get('action')}")
                    return parsed_json
                    
                except Exception as attempt_err:
                    logger.warning(f"Falha na tentativa com {provider} ({model_name}): {attempt_err}")
                    last_error = attempt_err
                    
        # Se saiu do loop, todos falharam
        logger.error(f"Todos os provedores na cadeia de classificação falharam. Último erro: {last_error}")
        if force_json:
            return {"action": "chat", "response": f"Erro interno de processamento da IA: todos os provedores falharam. Detalhe: {last_error}"}
        return f"Erro interno de processamento da IA: todos os provedores falharam. Detalhe: {last_error}"

    async def _call_gemini_api(self, system_prompt: str, messages: list, force_json: bool = True) -> dict | str:
        """
        Chama a API do Google Gemini (usando gemini-1.5-flash) como fallback.
        Traduz o formato das mensagens e força o retorno em JSON se necessário.
        """
        import httpx
        
        # Filtrar o prompt do sistema e converter o resto das mensagens para o formato do Gemini
        gemini_contents = []
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content")
            
            if role == "system":
                continue
                
            gemini_role = "user" if role == "user" else "model"
            gemini_contents.append({
                "role": gemini_role,
                "parts": [{"text": content}]
            })
            
        model_name = "gemini-flash-latest"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.gemini_api_key}"
        
        payload = {
            "contents": gemini_contents,
            "systemInstruction": {
                "parts": [{"text": system_prompt}]
            },
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 2048
            }
        }
        
        if force_json:
            payload["generationConfig"]["responseMimeType"] = "application/json"
            
        logger.info(f"Chamando a API do Google Gemini ({model_name})...")
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, timeout=30)
            
            if resp.status_code == 200:
                resp_json = resp.json()
                try:
                    content = resp_json["candidates"][0]["content"]["parts"][0]["text"]
                except (KeyError, IndexError) as parse_err:
                    logger.error(f"Erro ao analisar resposta estruturada do Gemini: {parse_err}. Resposta bruta: {resp_json}")
                    raise ValueError(f"Resposta inválida do Gemini: {parse_err}")
                
                logger.debug(f"Retorno bruto do Gemini: {content}")
                
                if not force_json:
                    return content
                
                # Tratar parseamento do JSON
                try:
                    parsed_json = json.loads(content)
                    if isinstance(parsed_json, list) and len(parsed_json) > 0:
                        parsed_json = parsed_json[0]
                    return parsed_json
                except json.JSONDecodeError as jde:
                    logger.warning(f"Falha ao parsear JSON direto do Gemini, tentando extrair objeto: {jde}")
                    if "```" in content:
                        m = re.search(r'```(?:json)?\s*(.*?)\s*```', content, re.DOTALL)
                        if m:
                            try:
                                return json.loads(m.group(1).strip())
                            except json.JSONDecodeError:
                                pass
                    first_brace = content.find('{')
                    last_brace = content.rfind('}')
                    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
                        try:
                            return json.loads(content[first_brace:last_brace+1])
                        except json.JSONDecodeError:
                            pass
                    raise jde
            else:
                logger.error(f"Erro na API do Gemini: Status {resp.status_code} - {resp.text}")
                raise httpx.HTTPStatusError(f"API do Gemini retornou {resp.status_code}", request=None, response=resp)

    def validate_action(self, chat_id: int, action: dict) -> tuple[bool, dict]:
        """
        Valida se a ação estruturada gerada pelo Groq atende às regras de segurança do Harness.
        Verifica confirmações para ações críticas e envios de e-mails sensíveis.
        """
        action_type = action.get("action", "chat")
        
        # 1. Verificar ações críticas de exclusão no security.py
        if self.security.requires_confirmation(action_type):
            history = self.memory.get_history(chat_id)
            if not self.security.has_user_confirmed(history):
                logger.warning(f"Ação crítica '{action_type}' bloqueada por falta de confirmação do usuário.")
                return False, {
                    "action": "chat",
                    "response": "Esta é uma ação crítica (exclusão). Você confirma que deseja prosseguir com isso?"
                }

        # 2. Regra Crítica de Segurança de E-mail (Gmail)
        if action_type == "send":
            to_field = action.get("to", "").strip()
            
            # Verificar se há e-mail válido com @
            if "@" not in to_field:
                # Se não for e-mail completo, tenta resolver pelo Contacts
                resolved_email, name, err = contacts.resolve_email_address(to_field)
                if err:
                    logger.warning(f"Falha de validação de destinatário para '{to_field}': {err}")
                    return False, {"action": "chat", "response": err}
                action["to"] = resolved_email
                logger.info(f"Destinatário resolvido e atualizado de '{to_field}' para '{resolved_email}'")
            
            # Verificar se o usuário confirmou explicitamente o envio de e-mail recente
            history = self.memory.get_history(chat_id)
            if not self.security.has_user_confirmed(history):
                logger.warning("Envio de e-mail bloqueado: Usuário ainda não deu aprovação do texto.")
                subject = action.get("subject", "Sem assunto")
                body = action.get("body", "Sem corpo de mensagem")
                return False, {
                    "action": "chat",
                    "response": (
                        f"Olá, Claudemir! Preparei o e-mail abaixo:\\n\\n"
                        f"**Para:** {action.get('to')}\\n"
                        f"**Assunto:** {subject}\\n"
                        f"**Mensagem:**\\n{body}\\n\\n"
                        f"Você confirma o envio?"
                    )
                }
                
        return True, action

    def feedback_loop(self, action_type: str, err_msg: str) -> dict:
        """
        Interfere de forma autônoma em caso de falha na execução de alguma ferramenta,
        auditando o erro e formatando um fallback amigável ao usuário.
        """
        logger.error(f"Feedback Loop ativado para a ação '{action_type}'. Erro: {err_msg}")
        return {
            "action": "chat",
            "response": f"Desculpe, Claudemir. Encontrei um problema ao tentar executar essa tarefa no meu sistema. (Detalhe: {err_msg})"
        }

    async def process(self, chat_id: int, user_input: str, on_action_start=None) -> dict:
        """
        Ponto de entrada central do Harness.
        Recebe a mensagem bruta do usuário, aplica moderação, rate limit, resolve a ação e executa a ferramenta.
        """
        # 1. Sanitizar entrada
        cleaned_input = self.security.sanitize_input(user_input)
        
        # 2. Verificar Rate Limiting
        allowed, wait_time = self.security.check_rate_limit(chat_id)
        if not allowed:
            return {
                "action": "chat",
                "response": f"⚠️ Você está enviando mensagens rápido demais. Por favor, aguarde {wait_time} segundos."
            }
            
        # 3. Moderar conteúdo
        if not self.security.moderate_content(cleaned_input):
            return {
                "action": "chat",
                "response": "⚠️ Não posso processar mensagens contendo esse tipo de conteúdo ou instruções perigosas."
            }

        # Interceptor da Skill LinkedIn Post Expert Interativa (Máquina de Estados)
        history = self.memory.get_history(chat_id)
        last_assistant_msg = None
        for msg in reversed(history):
            if msg["role"] == "assistant":
                last_assistant_msg = msg["content"]
                break

        if last_assistant_msg:
            # Etapa 1: Confirmar o assunto do post
            m_topic = re.search(r"Confirma que o assunto do post é '([^']+)'\?", last_assistant_msg)
            if m_topic:
                if self.security.has_user_confirmed(history + [{"role": "user", "content": cleaned_input}]):
                    topic = m_topic.group(1)
                    self.update_memory(chat_id, "user", cleaned_input)
                    
                    if on_action_start:
                        await on_action_start("linkedin_post", {"topic": topic})
                        
                    prompt = linkedin.VIRAL_POST_TEMPLATE.format(topic=topic)
                    draft_result = await self.classify_intent(chat_id, prompt, save_to_history=False, ignore_history=True, force_json=False)
                    draft_text = draft_result if isinstance(draft_result, str) else draft_result.get("response", str(draft_result))
                    
                    response_text = f"Aqui está um rascunho do post:\n\n{draft_text}\n\nDeseja confirmar ou ajustar antes de finalizar?"
                    return {
                        "action": "chat",
                        "response": response_text
                    }
                elif "não" in cleaned_input.lower() or "nao" in cleaned_input.lower() or "cancelar" in cleaned_input.lower():
                    self.update_memory(chat_id, "user", cleaned_input)
                    return {
                        "action": "chat",
                        "response": "Entendido, Claudemir. Cancelei a criação do post. O que gostaria de fazer agora?"
                    }

            # Etapa 2: Confirmar o rascunho do post
            if "Deseja confirmar ou ajustar antes de finalizar?" in last_assistant_msg:
                if self.security.has_user_confirmed(history + [{"role": "user", "content": cleaned_input}]):
                    self.update_memory(chat_id, "user", cleaned_input)
                    
                    # Extrair o rascunho
                    draft_start = last_assistant_msg.find("Aqui está um rascunho do post:\n\n")
                    draft_end = last_assistant_msg.find("\n\nDeseja confirmar ou ajustar antes de finalizar?")
                    
                    if draft_start != -1 and draft_end != -1:
                        draft_start += len("Aqui está um rascunho do post:\n\n")
                        draft_text = last_assistant_msg[draft_start:draft_end].strip()
                    else:
                        draft_text = last_assistant_msg
                    
                    # Encontrar o assunto no histórico anterior para saber quais hashtags usar
                    topic = "TI"
                    for msg in reversed(history):
                        if msg["role"] == "assistant" and "Confirma que o assunto do post é" in msg["content"]:
                            m = re.search(r"Confirma que o assunto do post é '([^']+)'\?", msg["content"])
                            if m:
                                topic = m.group(1)
                                break
                    
                    # Gerar as hashtags
                    tags = ["#TI", "#CarreiraEmTI"]
                    topic_lower = topic.lower()
                    if "logis" in topic_lower or "logís" in topic_lower or "logist" in topic_lower:
                        tags.append("#Logística")
                    if "ia" in topic_lower or "intelig" in topic_lower or "artificial" in topic_lower:
                        tags.append("#InteligênciaArtificial")
                        
                    ordered_tags = []
                    if "#Logística" in tags:
                        ordered_tags.append("#Logística")
                    if "#InteligênciaArtificial" in tags:
                        ordered_tags.append("#InteligênciaArtificial")
                    ordered_tags.append("#TI")
                    ordered_tags.append("#CarreiraEmTI")
                    
                    tags_str = " ".join(ordered_tags)
                    final_post = f"{draft_text}\n\n{tags_str}"
                    
                    # Salvar tópico no histórico do LinkedIn
                    linkedin.save_topic(topic)
                    
                    return {
                        "action": "chat",
                        "response": final_post
                    }
                elif "não" in cleaned_input.lower() or "nao" in cleaned_input.lower() or "cancelar" in cleaned_input.lower():
                    self.update_memory(chat_id, "user", cleaned_input)
                    return {
                        "action": "chat",
                        "response": "Sem problemas, Claudemir. Cancelei a criação do post. Se quiser ajustar, me diga o que mudar."
                    }

        # 4. Classificar Intenção via Groq (Salva no histórico de conversação)
        result = await self.classify_intent(chat_id, cleaned_input, save_to_history=True)
        
        # 5. Validar Ação
        is_safe, validated_action = self.validate_action(chat_id, result)
        if not is_safe:
            # Retorna a mensagem de aviso/confirmação gerada pela validação
            return validated_action
            
        action_type = validated_action.get("action", "chat")
        
        # Invocar callback de ação se fornecido para feedback visual (UX)
        if on_action_start:
            try:
                await on_action_start(action_type, validated_action)
            except Exception as e:
                logger.warning(f"Erro ao executar callback on_action_start: {e}")
        
        # 6. Execução das Ferramentas
        try:
            if action_type == "send":
                to = validated_action.get("to", "")
                subject = validated_action.get("subject", "")
                body = validated_action.get("body", "")
                
                # Anexar assinatura do config (Claudemir Pedroso Cubas)
                signature = os.environ.get("SIGNATURE", "Claudemir Pedroso Cubas")
                body_with_sig = f"{body}<br><br>---<br><i>{signature}</i>"
                
                msg_id, err = gmail.send_email(to, subject, body_with_sig)
                if err:
                    return self.feedback_loop(action_type, err)
                return {
                    "action": "chat",
                    "response": f"✅ E-mail enviado com sucesso para {to}! (ID: {msg_id})"
                }
                
            elif action_type == "list":
                limit = validated_action.get("limit", 5)
                emails, err = gmail.get_emails(limit)
                if err:
                    return self.feedback_loop(action_type, err)
                if not emails:
                    return {"action": "chat", "response": "Nenhum e-mail encontrado na sua caixa de entrada."}
                return {
                    "action": "chat",
                    "response": "📧 **Seus últimos e-mails:**\n\n" + "\n---\n".join(emails)[:4000]
                }
                
            elif action_type == "contacts":
                query = validated_action.get("query", "")
                results, err = contacts.search_contacts(query)
                if err:
                    return self.feedback_loop(action_type, err)
                if not results:
                    return {"action": "chat", "response": f"Nenhum contato encontrado correspondente a '{query}'."}
                
                # Verificar se há intenção de envio associada (subject/body na ação ou na última msg)
                subject = validated_action.get("subject", "")
                body = validated_action.get("body", "")
                
                if len(results) == 1 and (subject or body):
                    # Encontrou exatamente um contato e há contexto de e-mail: apresentar rascunho para aprovação
                    resolved_email = results[0]["email"]
                    contact_name = results[0]["name"]
                    subject_display = subject or "(Sem assunto)"
                    body_display = body or "(Sem corpo de mensagem)"
                    return {
                        "action": "chat",
                        "response": (
                            f"Olá, Claudemir! Encontrei o contato e preparei o e-mail abaixo:\n\n"
                            f"**Para:** {contact_name} ({resolved_email})\n"
                            f"**Assunto:** {subject_display}\n"
                            f"**Mensagem:**\n{body_display}\n\n"
                            f"Você confirma o envio?"
                        )
                    }
                
                # Caso padrão: listar contatos encontrados
                lines = [f"• **{c['name']}**: {c['email']}" for c in results]
                return {
                    "action": "chat",
                    "response": f"👤 **Contatos encontrados para '{query}':**\n\n" + "\n".join(lines)
                }
                
            elif action_type == "calendar_create":
                title = validated_action.get("title", "")
                start = validated_action.get("start", "")
                end = validated_action.get("end", "")
                desc = validated_action.get("description", "")
                atts = validated_action.get("attendees", [])
                
                event, err = calendar.create_event(title, start, end, desc, atts)
                if err:
                    return self.feedback_loop(action_type, err)
                return {
                    "action": "chat",
                    "response": f"📅 **Evento criado com sucesso!**\n\n**Título:** {event.get('summary')}\n**Link:** {event.get('htmlLink')}"
                }
                
            elif action_type == "calendar_list":
                start = validated_action.get("start", "")
                end = validated_action.get("end", "")
                events, err = calendar.list_events(start, end)
                if err:
                    return self.feedback_loop(action_type, err)
                if not events:
                    return {"action": "chat", "response": "Nenhum compromisso agendado para o período solicitado."}
                
                lines = []
                for ev in events:
                    start_time = ev.get('start', {}).get('dateTime') or ev.get('start', {}).get('date')
                    try:
                        dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                        dt_str = dt.strftime('%d/%m às %H:%M')
                    except:
                        dt_str = start_time
                    lines.append(f"• **{ev.get('summary')}** — {dt_str}")
                return {
                    "action": "chat",
                    "response": "📅 **Seus compromissos:**\n\n" + "\n".join(lines)
                }
                
            elif action_type == "linkedin_post":
                topic = validated_action.get("topic", "")
                return {
                    "action": "chat",
                    "response": f"Confirma que o assunto do post é '{topic}'?"
                }
                
            elif action_type == "linkedin_article":
                topic = validated_action.get("topic", "")
                style = "article"
                
                logger.info(f"Harness LinkedIn: Gerando conteúdo do tipo '{style}' para o tema '{topic}'")
                
                # 1. Verificar duplicidade de temas
                is_dup, alert_msg = linkedin.is_topic_duplicate(topic)
                
                # 2. Selecionar o template de prompt
                prompt = linkedin.TECHNICAL_ARTICLE_TEMPLATE.format(topic=topic)
                    
                if is_dup:
                    prompt += "\n\nNOTA DE EVITAR DUPLICIDADE: Você já gerou um post/artigo sobre este tema. Crie um conteúdo sob uma perspectiva completamente diferente para não ser repetitivo!"
                
                # 3. Chamar a LLM (Groq) sem salvar esta instrução de escrita no histórico de conversação
                final_result = await self.classify_intent(chat_id, prompt, save_to_history=False, ignore_history=True, force_json=False)
                generated_content = ""
                
                if isinstance(final_result, dict):
                    # 1. Procurar na chave padrão "response" ou chaves de texto direto comuns
                    for k in ["response", "post", "post_content", "content", "text", "article", "article_content"]:
                        if k in final_result and final_result[k]:
                            generated_content = final_result[k]
                            break
                            
                    # 2. Se não achou texto direto, mas o JSON está quebrado nas seções típicas de artigo
                    if not generated_content and ("title" in final_result or "introduction" in final_result):
                        markdown_parts = []
                        if "title" in final_result:
                            markdown_parts.append(f"# {final_result['title']}")
                        if "introduction" in final_result:
                            markdown_parts.append(f"## Introdução\n{final_result['introduction']}")
                        if "development" in final_result:
                            dev = final_result["development"]
                            if isinstance(dev, list):
                                for section in dev:
                                    if isinstance(section, dict):
                                        sec_title = section.get("title", "")
                                        sec_content = section.get("content", "")
                                        if sec_title:
                                            if sec_title.startswith("#"):
                                                markdown_parts.append(f"{sec_title}\n{sec_content}")
                                            else:
                                                markdown_parts.append(f"### {sec_title}\n{sec_content}")
                                    else:
                                        markdown_parts.append(str(section))
                            else:
                                markdown_parts.append(f"## Desenvolvimento\n{dev}")
                        if "conclusion" in final_result:
                            conclusion = final_result["conclusion"]
                            if isinstance(conclusion, dict):
                                markdown_parts.append(f"## Conclusão\n{conclusion.get('content', '') or conclusion.get('response', '')}")
                            else:
                                markdown_parts.append(f"## Conclusão\n{conclusion}")
                        
                        generated_content = "\n\n".join(markdown_parts)
                        
                    # 3. Fallback final: representação de string se nada acima funcionar
                    if not generated_content:
                        generated_content = str(final_result)
                else:
                    generated_content = str(final_result)
                
                # 4. Validar tamanho dos caracteres do LinkedIn
                is_valid, size, limit = linkedin.validate_content(generated_content, style)
                if not is_valid:
                    logger.warning(f"Conteúdo do LinkedIn gerado ({size} chars) excede o limite ({limit} chars). Solicitando re-escrita curta...")
                    # Feedback loop autônomo para encurtar o texto
                    shorten_instruction = f"Seu texto anterior excedeu o limite de caracteres do LinkedIn (tamanho atual: {size}, limite: {limit}). Por favor, reescreva-o de forma mais objetiva e concisa, sem perder a qualidade, garantindo que fique com menos de {limit} caracteres."
                    self.update_memory(chat_id, "system", f"[SISTEMA: Rascunho anterior de tamanho inválido]\n\n{generated_content}")
                    
                    final_result = await self.classify_intent(chat_id, shorten_instruction, save_to_history=False, force_json=False)
                    generated_content = final_result if isinstance(final_result, str) else final_result.get("response", generated_content)
                    
                    # Remover rascunho inválido da memória
                    history = self.memory.get_history(chat_id)
                    if history and history[-1]["role"] == "system":
                        history.pop()
                
                # 5. Salvar o tópico no histórico persistente do LinkedIn
                linkedin.save_topic(topic)
                
                # Se for duplicado, adicionar um aviso discreto ao usuário
                response_text = generated_content
                if is_dup and alert_msg:
                    response_text = f"{alert_msg}\n\n{generated_content}"
                    
                return {
                    "action": "chat",
                    "response": response_text
                }
                
            elif action_type == "web_search":
                # LÓGICA REACT (Agentic Loop de busca web)
                search_query = validated_action.get("query", "")
                logger.info(f"Harness ReAct: Iniciando busca no Tavily para '{search_query}'")
                
                # Executar busca web
                search_results = tavily.search_web_tavily(search_query)
                
                # Inserir os resultados temporariamente na memória como mensagem do sistema
                temp_context = f"[SISTEMA: Resultados da pesquisa na internet para '{search_query}']\n\n{search_results}"
                self.update_memory(chat_id, "system", temp_context)
                
                # Chamar novamente o Groq (IA) com save_to_history=False para obter o resumo/resposta final
                instruction = f"Por favor, formule a resposta final para a pergunta original ('{cleaned_input}') utilizando as informações da internet acima."
                final_result = await self.classify_intent(chat_id, instruction, save_to_history=False, force_json=False)
                if isinstance(final_result, str):
                    try:
                        # Limpar espaços em branco e tentar decodificar JSON
                        cleaned_res = final_result.strip()
                        parsed = json.loads(cleaned_res)
                        if isinstance(parsed, dict):
                            response_text = parsed.get("response") or parsed.get("text") or parsed.get("response_text") or final_result
                            final_result = {"action": "chat", "response": response_text}
                        else:
                            final_result = {"action": "chat", "response": final_result}
                    except Exception:
                        final_result = {"action": "chat", "response": final_result}
                
                # Remover o contexto temporário do histórico
                history = self.memory.get_history(chat_id)
                if history and history[-1]["role"] == "system":
                    history.pop()
                    logger.debug("Removido o contexto temporário do histórico de mensagens.")
                
                # Retorna o resultado refinado finalizado
                return final_result
                
            elif action_type == "weather":
                location = validated_action.get("location", "Curitiba")
                logger.info(f"Harness Weather: Consultando clima para '{location}'")
                
                # Executar consulta meteorológica
                weather_report = await weather.get_weather(location)
                
                return {
                    "action": "chat",
                    "response": weather_report
                }
                
            elif action_type == "image_generate":
                prompt = validated_action.get("prompt", "")
                logger.info(f"Harness Image: Gerando imagem para prompt '{prompt[:80]}'")
                
                # Gerar imagem via Pollinations.ai
                image_path, err = await image.generate_image(prompt, chat_id=chat_id)
                
                if err:
                    return self.feedback_loop(action_type, err)
                
                return {
                    "action": "chat",
                    "response": f"\U0001f3a8 Aqui está a imagem gerada para: *{prompt}*",
                    "image_path": image_path
                }
                
            else:
                # Chat Geral / Outras Ações não mapeadas
                # Tratamento robusto para concatenar chaves adicionais geradas pela LLM na resposta final
                response_text = validated_action.get("response", "")
                extra_parts = []
                for key, val in validated_action.items():
                    if key in ["action", "response", "image_path"]:
                        continue
                    if isinstance(val, list):
                        formatted_list = "\n".join([f"• {item}" for item in val])
                        extra_parts.append(formatted_list)
                    elif isinstance(val, dict):
                        formatted_dict = "\n".join([f"• **{k}**: {v}" for k, v in val.items()])
                        extra_parts.append(formatted_dict)
                    elif val:
                        extra_parts.append(str(val))
                
                if extra_parts:
                    response_text += "\n\n" + "\n\n".join(extra_parts)
                    validated_action["response"] = response_text
                    
                return validated_action
                
        except Exception as e:
            logger.error(f"Erro não tratado na execução da ferramenta: {e}")
            return self.feedback_loop(action_type, str(e))
