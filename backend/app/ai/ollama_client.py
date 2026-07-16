"""
Ollama AI Client — real HTTP calls to local Ollama service.
Includes OllamaClient, IncidentAnalyzer, ThreatExplainer, and ChatService.
"""
import logging
import time
import random
import threading
from typing import Any, Dict, List, Optional

import httpx

from ..core.settings import settings

logger = logging.getLogger(__name__)


SYSTEM_PROMPT_ANALYST = """You are an enterprise-grade, Level-3 Security Analyst, Forensic Investigator, and Incident Response Architect.
Your role is to perform deep technical forensics on security incidents and deliver highly detailed, comprehensive, and accurate investigation reports.
Ensure everything is technically grounded, objective, and realistic. Never hallucinate findings or compromise on details for brevity.

For any analysis, you must ALWAYS use the following structured sections:
1. ## **Executive Summary**
   Provide a concise, high-impact summary (3-4 sentences) outlining the incident scope, critical findings, and business risk.
2. ## **Root Cause Analysis**
   A rigorous deep-dive into how the incident occurred. Identify vulnerability vectors, compromise origins, target hosts, and affected assets.
3. ## **Step-by-Step Attack Timeline**
   Detail the chronological progression of the threat vector. Organize chronologically or logically using bullet points or tables.
4. ## **Immediate Containment & Mitigation Playbook**
   A structured, actionable numbered list of steps that must be executed immediately to isolate, stop, and remediate the threat.
5. ## **Long-Term Hardening & Preventive Recommendations**
   Concrete strategic actions to prevent future recurrences, grouped into network, host, identity, and logging domains.
6. ## **Security & Performance Considerations**
   Outline the security and system performance impact of the incident and of the proposed containment actions.
7. ## **Edge Cases & Pivots**
   Detail any unexpected ways this threat might evolve, bypass defenses, or pivot to other network segments.
8. ## **Future Investigations & Logging Requirements**
   Define which telemetry sources (e.g., Sysmon, CloudTrail, Proxy Logs) should be enhanced or gathered to improve future visibility.

Format all comparisons, incident metadata, and structured statistics using markdown tables."""

SYSTEM_PROMPT_EXPLAINER = """You are a senior cybersecurity educator and threat intelligence researcher.
Your task is to explain complex security alerts, attacks, and technical indicators to junior SOC analysts, elevating their skills while maintaining high professional standards.
Be clear, accurate, and educational. Define advanced terminology (such as 'pass-the-hash', 'mimikatz', or 'process hollowing') whenever introduced.

You must ALWAYS include the following sections:
1. ## **What Happened**
   A clear, plain-English summary of the technical alert or threat behavior.
2. ## **Why It Matters**
   A robust explanation of the risk, business impact, and potential lateral consequences of this threat vector.
3. ## **Step-by-Step Technical Walkthrough**
   A comprehensive breakdown of how the threat operates under the hood, covering process injection, network transport, or credential access mechanisms.
4. ## **Immediate Triage Checklist**
   A logical checklist of tactical things the junior analyst should verify or perform right now.
5. ## **Forensic Indicators of Compromise (IoCs) & Hunt Instructions**
   Specific artifacts, file paths, hashes, or registry keys to hunt for, alongside simple SIEM search concepts (Splunk/KQL/LogQL).

Use clear headings, bold terms, and code formatting to make the output highly readable and engaging."""

SYSTEM_PROMPT_CHAT = """You are an elite, highly reliable Security Operations Center (SOC) Operations Copilot and AI Assistant.
You assist professional cyber defense teams in auditing logs, writing mitigation scripts, mapping telemetry to MITRE ATT&CK, and answering advanced security questions.

Guidelines:
- **Completeness over Brevity**: Prefer deep, thorough, and highly complete explanations. Never truncate, omit details, or summarize key elements unless explicitly asked.
- **Answer All Parts of Multi-Question Prompts**: If the user asks multiple questions, address each one under its own clear, bold markdown heading.
- **No Hallucinations**: Ground your response in the provided knowledge base context where applicable. If unsure, express caution and recommend verification steps rather than inventing facts.
- **Production-Ready Code**: Any scripts, regexes, configs, or queries generated must:
  - Be completely self-contained and run/compile without modification.
  - Follow solid software engineering design principles (SOLID).
  - Be modular, secure, and validate input parameters where relevant.
  - Include structured logging and robust error-handling blocks.
  - Avoid duplicate or redundant logical flow.
- **Beautiful Formatting**: Organize information with headers, indented bullet points, highlighted terms, code blocks, and markdown tables for tabular data.
"""


class OllamaClient:
    """Sync client for the local Ollama LLM service with built-in retry mechanisms and continuation handling."""

    def __init__(
        self,
        base_url: str = settings.OLLAMA_BASE_URL,
        model: str = settings.OLLAMA_MODEL,
        timeout: int = 1200,  # Increased to 10 minutes for longer responses
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model or settings.RECOMMENDED_OLLAMA_MODEL
        self.timeout = timeout
        self.recommended_model = settings.RECOMMENDED_OLLAMA_MODEL

    def _execute_with_retry(self, request_fn, *args, **kwargs) -> httpx.Response:
        """
        Execute an HTTP request with exponential backoff and jitter on transient failures.
        """
        max_retries = 3
        base_delay = 1.0

        for attempt in range(max_retries + 1):
            try:
                return request_fn(*args, **kwargs)
            except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as exc:
                if attempt == max_retries:
                    logger.error(f"Max retries reached. Request failed: {exc}")
                    raise exc

                # Exponential backoff with jitter
                delay = base_delay * (2 ** attempt) + random.uniform(0.1, 0.5)
                logger.warning(f"Transient network/timeout error ({exc}). Retrying in {delay:.2f} seconds (Attempt {attempt + 1}/{max_retries})...")
                time.sleep(delay)
            except httpx.HTTPStatusError as exc:
                # Retry on 5xx status codes (server issues), but not on 4xx (client errors)
                if exc.response.status_code >= 500 and attempt < max_retries:
                    delay = base_delay * (2 ** attempt) + random.uniform(0.1, 0.5)
                    logger.warning(f"Server error {exc.response.status_code}. Retrying in {delay:.2f} seconds (Attempt {attempt + 1}/{max_retries})...")
                    time.sleep(delay)
                else:
                    raise exc

    def is_available(self) -> bool:
        """Check if Ollama service is reachable."""
        try:
            def req():
                with httpx.Client(timeout=5) as client:
                    response = client.get(f"{self.base_url}/api/tags")
                    response.raise_for_status()
                    return response

            r = self._execute_with_retry(req)
            return r.status_code == 200
        except Exception:
            return False

    def list_models(self) -> List[str]:
        """Return the models currently available in Ollama."""
        try:
            def req():
                with httpx.Client(timeout=5) as client:
                    response = client.get(f"{self.base_url}/api/tags")
                    response.raise_for_status()
                    return response

            response = self._execute_with_retry(req)
            data = response.json()
            models = data.get("models", [])
            return [m.get("name", "").strip() for m in models if m.get("name", "").strip()]
        except Exception as exc:
            logger.warning("Unable to list Ollama models: %s", exc)
            return []

    def resolve_model(self, preferred_model: Optional[str] = None) -> str:
        """Pick the best available model, falling back to a fast local default when needed."""
        available_models = self.list_models()
        candidates = []
        if preferred_model:
            candidates.append(preferred_model)
        
        # Read from settings dynamically to capture user setting updates in-memory
        from ..core.settings import settings
        if settings.OLLAMA_MODEL:
            candidates.append(settings.OLLAMA_MODEL)
            
        if self.model:
            candidates.append(self.model)
        candidates.append(self.recommended_model)
        candidates.extend(settings.OLLAMA_MODEL_FALLBACKS)

        for candidate in candidates:
            if candidate and candidate in available_models:
                self.model = candidate
                return candidate

        if available_models:
            self.model = available_models[0]
            return self.model

        if self.model:
            return self.model
        return self.recommended_model

    def _is_truncated(self, text: str) -> bool:
        """
        Check if the text response appears truncated or prematurely cut off.
        """
        if not text:
            return False

        # Clean text to remove trailing whitespace
        text_stripped = text.rstrip()
        if not text_stripped:
            return False

        # 1. Unclosed triple backticks (code blocks)
        if text_stripped.count("```") % 2 != 0:
            logger.info("Truncation detected: Unclosed triple backticks.")
            return True

        # 2. Ends in the middle of a word or incomplete punctuation
        # Complete sentences usually end with ., !, ?, ", ', *, _, etc.
        last_char = text_stripped[-1]
        if last_char.isalnum() or last_char in [",", "-", ":", ";", "("]:
            logger.info(f"Truncation detected: Text ends with suspect character '{last_char}'.")
            return True

        # 3. Check for specific common indicators of partial markdown / unclosed lists
        # If the last line starts with list syntax and is short
        lines = text_stripped.split("\n")
        if lines:
            last_line = lines[-1].strip()
            # If a list item was started but might be cut off
            if last_line.startswith(("-", "*", "+")) and not any(last_line.endswith(p) for p in [".", "!", "?", "```"]):
                if len(last_line) < 15: # very short, likely cut off
                    logger.info("Truncation detected: Possible cut-off list item.")
                    return True

        return False

    def _stitch_responses(self, prefix: str, continuation: str) -> str:
        """Stitch a partial response and its continuation together cleanly."""
        prefix_clean = prefix.rstrip()
        continuation_clean = continuation.lstrip()

        # Remove common introductory phrases from continuation
        intro_phrases = [
            "Continuing exactly where I left off:",
            "Continuing where I left off:",
            "Continuing:",
            "Here is the continuation:",
            "Here is the remaining response:",
        ]
        for phrase in intro_phrases:
            if continuation_clean.lower().startswith(phrase.lower()):
                continuation_clean = continuation_clean[len(phrase):].lstrip()

        # If the continuation starts with ellipsis, remove it
        if continuation_clean.startswith("..."):
            continuation_clean = continuation_clean[3:].lstrip()

        # Ensure proper spacing (e.g. if prefix ends with a word and continuation starts with a word)
        if prefix_clean and continuation_clean:
            last_char = prefix_clean[-1]
            first_char = continuation_clean[0]
            if last_char.isalnum() and first_char.isalnum():
                return f"{prefix_clean} {continuation_clean}"

        return f"{prefix_clean}\n{continuation_clean}"

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
    ) -> str:
        """Send a single-turn generation request to Ollama with automatic continuation."""
        model_name = self.resolve_model()
        payload: Dict[str, Any] = {
            "model": model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": 3072,  # Substantial context budget
                "top_p": 0.9,
                "top_k": 40,
            },
        }
        if system_prompt:
            payload["system"] = system_prompt

        try:
            def req():
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(
                        f"{self.base_url}/api/generate",
                        json=payload,
                    )
                    response.raise_for_status()
                    return response

            response = self._execute_with_retry(req)
            data = response.json()
            response_text = data.get("response", "")
        except httpx.ConnectError:
            logger.warning("Ollama not reachable at %s", self.base_url)
            return self._fallback_response("Ollama service is not available. Please start Ollama locally.")
        except httpx.TimeoutException:
            logger.warning("Ollama request timed out after %d seconds", self.timeout)
            return self._fallback_response("Request timed out. The model is taking longer to respond. Please try again in a moment.")
        except httpx.HTTPStatusError as exc:
            logger.warning("Ollama generate returned %s", exc.response.status_code)
            return self._fallback_response("The selected Ollama model could not be used. The app will try a detected local model automatically when available.")
        except Exception as exc:
            logger.error("Ollama generate error: %s", exc)
            return self._fallback_response(f"AI service error: {exc}")

        # Continuation Loop (Max 3 iterations)
        iter_count = 0
        while self._is_truncated(response_text) and iter_count < 3:
            iter_count += 1
            logger.info(f"Automatically continuing generation, iteration {iter_count}...")
            continuation_prompt = f"{prompt}\n\n[Previous Partial Response]:\n{response_text}\n\n[Instruction]: Your previous response was cut off. Please continue exactly where you left off, without repeating any of your previous text, so that the response is complete."

            payload_continue = {
                "model": model_name,
                "prompt": continuation_prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": 1536,
                    "top_p": 0.9,
                    "top_k": 40,
                }
            }
            if system_prompt:
                payload_continue["system"] = system_prompt

            try:
                def req_cont():
                    with httpx.Client(timeout=self.timeout) as client:
                        resp = client.post(
                            f"{self.base_url}/api/generate",
                            json=payload_continue,
                        )
                        resp.raise_for_status()
                        return resp

                resp_cont = self._execute_with_retry(req_cont)
                cont_text = resp_cont.json().get("response", "")
                if cont_text:
                    response_text = self._stitch_responses(response_text, cont_text)
                else:
                    break
            except Exception as e:
                logger.error(f"Error during generation continuation: {e}")
                break

        return response_text

    def chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.5,
    ) -> str:
        """Send a multi-turn chat request to Ollama with automatic continuation."""
        model_name = self.resolve_model()
        payload: Dict[str, Any] = {
            "model": model_name,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": 3072,  # Substantial context budget
                "top_p": 0.9,
                "top_k": 40,
            },
        }
        if system_prompt:
            payload["messages"] = [{"role": "system", "content": system_prompt}] + messages

        try:
            def req():
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(
                        f"{self.base_url}/api/chat",
                        json=payload,
                    )
                    response.raise_for_status()
                    return response

            response = self._execute_with_retry(req)
            data = response.json()
            if isinstance(data, dict):
                message = data.get("message") or {}
                if isinstance(message, dict):
                    response_text = message.get("content", "")
                else:
                    response_text = ""
            else:
                response_text = ""
        except httpx.ConnectError:
            return self._fallback_response("Ollama service is not available. Please start Ollama locally.")
        except httpx.TimeoutException:
            return self._fallback_response(f"Request timed out after {self.timeout} seconds. Model response is taking longer than expected. Please try again.")
        except httpx.HTTPStatusError as exc:
            logger.warning("Ollama chat returned %s", exc.response.status_code)
            return self._fallback_response("The selected Ollama model was not found. The app will auto-select a compatible local model when one is available.")
        except Exception as exc:
            logger.error("Ollama chat error: %s", exc)
            return self._fallback_response(f"AI service error: {exc}")

        # Continuation Loop (Max 3 iterations)
        iter_count = 0
        while self._is_truncated(response_text) and iter_count < 3:
            iter_count += 1
            logger.info(f"Automatically continuing chat response, iteration {iter_count}...")

            # Formulate the continuation conversation flow
            continuation_messages = list(messages) + [
                {"role": "assistant", "content": response_text},
                {
                    "role": "user",
                    "content": "Your previous response was cut off. Please continue exactly where you left off, without repeating any of your previous text, so that the response is complete."
                }
            ]

            payload_continue = {
                "model": model_name,
                "messages": continuation_messages,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": 1536,
                    "top_p": 0.9,
                    "top_k": 40,
                },
            }
            if system_prompt:
                payload_continue["messages"] = [{"role": "system", "content": system_prompt}] + continuation_messages

            try:
                def req_cont():
                    with httpx.Client(timeout=self.timeout) as client:
                        resp = client.post(
                            f"{self.base_url}/api/chat",
                            json=payload_continue,
                        )
                        resp.raise_for_status()
                        return resp

                resp_cont = self._execute_with_retry(req_cont)
                data_cont = resp_cont.json()
                if isinstance(data_cont, dict):
                    msg_cont = data_cont.get("message") or {}
                    cont_text = msg_cont.get("content", "")
                    if cont_text:
                        response_text = self._stitch_responses(response_text, cont_text)
                    else:
                        break
                else:
                    break
            except Exception as e:
                logger.error(f"Error during chat continuation: {e}")
                break

        return response_text

    def chat_stream(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.5,
    ):
        """Yield tokens from a multi-turn streaming chat request to Ollama."""
        model_name = self.resolve_model()
        payload: Dict[str, Any] = {
            "model": model_name,
            "messages": messages,
            "stream": True,  # Enable streaming
            "options": {
                "temperature": temperature,
                "num_predict": 3072,
                "top_p": 0.9,
                "top_k": 40,
            },
        }
        if system_prompt:
            payload["messages"] = [{"role": "system", "content": system_prompt}] + messages

        try:
            # We use httpx client with stream support
            with httpx.Client(timeout=self.timeout) as client:
                with client.stream("POST", f"{self.base_url}/api/chat", json=payload) as response:
                    response.raise_for_status()
                    for line in response.iter_lines():
                        if not line:
                            continue
                        try:
                            import json
                            data = json.loads(line)
                            if isinstance(data, dict):
                                message = data.get("message") or {}
                                content = message.get("content", "")
                                if content:
                                    yield content
                        except Exception as exc:
                            logger.error("Error parsing stream line: %s", exc)
        except Exception as exc:
            logger.error("Ollama streaming error: %s", exc)
            yield f"\n\n> ⚠️ **AI Streaming Error**: {exc}\n"

    def get_embeddings(self, text: str) -> List[float]:
        """Get embedding vector for text using Ollama."""
        model_name = self.resolve_model()
        try:
            def req():
                with httpx.Client(timeout=60) as client:
                    response = client.post(
                        f"{self.base_url}/api/embeddings",
                        json={"model": model_name, "prompt": text},
                    )
                    response.raise_for_status()
                    return response

            response = self._execute_with_retry(req)
            return response.json().get("embedding", [])
        except Exception as exc:
            logger.error("Ollama embeddings error: %s", exc)
            return []

    def _fallback_response(self, message: str) -> str:
        return (
            f"> ⚠️ **AI Unavailable**\n> {message}\n\n"
            "Try one of these next:\n"
            "- Start Ollama: `ollama serve`\n"
            f"- Pull a fast local model: `ollama pull {self.recommended_model}`"
        )


class IncidentAnalyzer:
    """AI-powered analysis of security incidents."""

    def __init__(self, client: Optional[OllamaClient] = None):
        self.client = client or OllamaClient()

    def analyze_incident(self, incident_data: Dict[str, Any]) -> str:
        title = incident_data.get("title", "Unknown Incident")
        severity = incident_data.get("severity", "unknown")
        description = incident_data.get("description", "")
        mitre = incident_data.get("mitre_mappings", [])
        log_count = incident_data.get("log_count", 0)
        source_ip = incident_data.get("source_ip", "unknown")
        score = incident_data.get("threat_score", 0)

        mitre_text = "\n".join(
            f"  - {m.get('technique_id')}: {m.get('technique_name')} ({m.get('tactic')})"
            for m in (mitre or [])
        ) or "  - None identified"

        prompt = f"""Analyze the following security incident and provide a detailed investigation report with complete information:

**Incident Title:** {title}
**Severity:** {severity.upper()}
**Threat Score:** {score}/100
**Source IP:** {source_ip}
**Log Events:** {log_count}

**Description:**
{description}

**MITRE ATT&CK Techniques Detected:**
{mitre_text}

Please provide a comprehensive analysis with:
1. **Executive Summary** (2-3 sentences)
2. **Attack Analysis** (detailed step-by-step breakdown of what happened)
3. **Immediate Containment Steps** (numbered list with specific actions)
4. **Investigation Checklist** (detailed items to check)
5. **Long-Term Hardening Recommendations** (preventive measures)

Ensure the response is complete and detailed, using markdown formatting with tables where appropriate for clarity."""
        
        result = self.client.generate(prompt, system_prompt=SYSTEM_PROMPT_ANALYST)
        
        # Ensure we got a response
        if not result or result.startswith(">"):
            logger.warning("Empty or error response from incident analysis")
            return f"Unable to analyze incident: {title}. Please ensure Ollama is running and has sufficient resources."
        
        return result


class ThreatExplainer:
    """Plain-English explanations of threats for junior analysts."""

    def __init__(self, client: Optional[OllamaClient] = None):
        self.client = client or OllamaClient()

    def explain_alert(self, alert_data: Dict[str, Any]) -> str:
        alert_type = alert_data.get("type", "unknown").replace("_", " ").title()
        description = alert_data.get("description", "")
        severity = alert_data.get("severity", "unknown")

        prompt = f"""Explain this security alert in simple terms for a junior SOC analyst:

Alert Type: {alert_type}
Severity: {severity}
Details: {description}

Provide a complete explanation with:
1. What Happened - Plain English explanation
2. Why It Matters - Business and security impact
3. What To Do Next - Immediate and follow-up actions

Use clear markdown formatting."""
        return self.client.generate(prompt, system_prompt=SYSTEM_PROMPT_EXPLAINER)


class ChatService:
    """Multi-turn conversational AI for SOC analysts."""

    def __init__(self, client: Optional[OllamaClient] = None):
        self.client = client or OllamaClient()

    def optimize_history(self, history: List[Dict[str, str]], max_tokens: int = 3000) -> List[Dict[str, str]]:
        """
        Optimize conversation history by budgeting tokens, removing duplicate content,
        and summarizing older turns if they exceed limits.
        """
        # 1. Remove consecutive duplicate or redundant messages
        unique_history = []
        seen = set()
        for h in history:
            content_hash = (h["role"], (h["content"] or "").strip())
            if content_hash not in seen:
                seen.add(content_hash)
                unique_history.append(h)

        # 2. Estimate token count (1 token ~= 4 characters)
        total_chars = sum(len(h["content"] or "") for h in unique_history)
        approx_tokens = total_chars // 4

        if approx_tokens <= max_tokens:
            return unique_history

        logger.info("Conversation history (%d tokens) exceeds budget (%d). Compressing...", approx_tokens, max_tokens)

        # 3. Keep the latest 6 messages intact, summarize earlier messages
        keep_count = min(6, len(unique_history))
        if keep_count > 0:
            intact_messages = unique_history[-keep_count:]
            older_messages = unique_history[:-keep_count]
        else:
            intact_messages = unique_history
            older_messages = []

        compressed_history = []
        if older_messages:
            older_text = "\n".join([f"{h['role'].upper()}: {(h['content'] or '')[:150]}" for h in older_messages])
            summary_prompt = f"Summarize the following security conversation history in 2-3 sentences, highlighting key questions and findings:\n\n{older_text}"
            try:
                # Use generate with a tiny temperature to get a fast, precise summary
                summary = self.client.generate(summary_prompt, system_prompt="You are a SOC assistant summarizing earlier chat history. Be extremely brief.", temperature=0.1)
                if summary and not summary.startswith(">"):
                    compressed_history.append({
                        "role": "system",
                        "content": f"[Summary of earlier conversation turns]: {summary}"
                    })
            except Exception as e:
                logger.warning("Conversation summarization failed: %s", e)
                # Fallback: just omit the oldest messages, keep only intact messages
                pass

        compressed_history.extend(intact_messages)
        return compressed_history

    def respond(
        self,
        user_message: str,
        history: List[Dict[str, str]],
        rag_context: Optional[str] = None,
    ) -> str:
        """Generate a response to the user message, optionally grounded with RAG context."""
        optimized_history = self.optimize_history(history)

        final_message = user_message
        if rag_context:
            final_message = (
                f"[Knowledge Base Context]\n{rag_context}\n\n"
                f"[User Question]\n{user_message}"
            )

        messages = list(optimized_history) + [{"role": "user", "content": final_message}]
        return self.client.chat(messages, system_prompt=SYSTEM_PROMPT_CHAT)

    def respond_stream(
        self,
        user_message: str,
        history: List[Dict[str, str]],
        rag_context: Optional[str] = None,
    ):
        """Generate a streaming response to the user message, optionally grounded with RAG context."""
        optimized_history = self.optimize_history(history)

        final_message = user_message
        if rag_context:
            final_message = (
                f"[Knowledge Base Context]\n{rag_context}\n\n"
                f"[User Question]\n{user_message}"
            )

        messages = list(optimized_history) + [{"role": "user", "content": final_message}]
        return self.client.chat_stream(messages, system_prompt=SYSTEM_PROMPT_CHAT)
