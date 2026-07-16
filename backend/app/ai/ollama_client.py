"""
Ollama AI Client — real HTTP calls to local Ollama service.
Includes OllamaClient, IncidentAnalyzer, ThreatExplainer, and ChatService.

Key fixes vs the previous version:
  * Responses no longer get cut off mid-sentence for long reports. The old code
    set num_predict=-1 but never set num_ctx, so Ollama silently truncated once
    the (default, small) context window filled up. We now size num_ctx per
    request based on the model's real max context + prompt length + desired
    output budget.
  * Truncation is detected using Ollama's own `done_reason` field
    ("length" = cut off by context/predict limit, "stop" = natural end)
    instead of guessing from the last character of the text.
  * Model selection can now actually compare installed models by their real
    context length and parameter size (via /api/show) and pick the best fit,
    instead of just returning the first name that matches a candidate list.
  * Streaming chat now auto-continues on truncation too (previously only the
    non-streaming generate()/chat() methods did).
"""
import json
import logging
import threading
import time
import random
from typing import Any, Dict, List, Optional

import httpx

from ..core.settings import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Context-window tuning. These read from settings if present, otherwise fall
# back to sane defaults, so nothing breaks if settings.py isn't updated.
# ---------------------------------------------------------------------------
DEFAULT_MAX_CONTEXT = getattr(settings, "OLLAMA_MAX_CONTEXT", 16384)
DEFAULT_MIN_CONTEXT = getattr(settings, "OLLAMA_MIN_CONTEXT", 4096)
DEFAULT_AUTO_SELECT_MODEL = getattr(settings, "OLLAMA_AUTO_SELECT_MODEL", True)


SYSTEM_PROMPT_ANALYST = """You are an enterprise-grade, Level-3 Security Analyst, Forensic Investigator, and Incident Response Architect.
Your role is to perform deep technical forensics on security incidents and deliver highly detailed, comprehensive, and accurate investigation reports.
Ensure everything is technically grounded, objective, and realistic. Never hallucinate findings or compromise on details for brevity.
Always finish every section you start. Never end a report mid-sentence, mid-list, or mid-table — if you are running low on room, wrap up the current section cleanly rather than trailing off.

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
Always finish every section you start; never trail off mid-sentence or mid-list.

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
- **Finish what you start**: never end a response mid-sentence, mid-code-block, or mid-list.
- **SOC operating discipline**: separate Confirmed Evidence, Analyst Inference, and Unknowns. Never claim that an
  attacker accessed data, achieved persistence, or compromised an organization unless the supplied telemetry proves it.
- For incident questions, answer in this order when relevant: Situation, Evidence, Attack Path, Impacted Assets,
  Confidence, Immediate Actions, Investigation Queries, and Closure Criteria.
- Ask for the missing log source, time range, host, user, or event ID when those facts are required for a reliable conclusion.
"""


class OllamaClient:
    """Sync client for the local Ollama LLM service with built-in retry mechanisms,
    capability-aware model selection, and reliable continuation handling."""

    def __init__(
        self,
        base_url: str = settings.OLLAMA_BASE_URL,
        model: str = settings.OLLAMA_MODEL,
        timeout: int = 1200,  # 10 minutes, for long structured reports
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model or settings.RECOMMENDED_OLLAMA_MODEL
        self.timeout = timeout
        self.recommended_model = settings.RECOMMENDED_OLLAMA_MODEL

        # Cache of /api/show results so we don't re-fetch model metadata on
        # every single request.
        self._model_info_cache: Dict[str, Dict[str, Any]] = {}
        self._model_info_lock = threading.Lock()

    # ------------------------------------------------------------------
    # Low-level request helpers
    # ------------------------------------------------------------------
    def _execute_with_retry(self, request_fn, *args, **kwargs) -> httpx.Response:
        """Execute an HTTP request with exponential backoff and jitter on transient failures."""
        max_retries = 3
        base_delay = 1.0

        for attempt in range(max_retries + 1):
            try:
                return request_fn(*args, **kwargs)
            except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as exc:
                if attempt == max_retries:
                    logger.error(f"Max retries reached. Request failed: {exc}")
                    raise exc
                delay = base_delay * (2 ** attempt) + random.uniform(0.1, 0.5)
                logger.warning(
                    f"Transient network/timeout error ({exc}). Retrying in {delay:.2f}s "
                    f"(Attempt {attempt + 1}/{max_retries})..."
                )
                time.sleep(delay)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code >= 500 and attempt < max_retries:
                    delay = base_delay * (2 ** attempt) + random.uniform(0.1, 0.5)
                    logger.warning(
                        f"Server error {exc.response.status_code}. Retrying in {delay:.2f}s "
                        f"(Attempt {attempt + 1}/{max_retries})..."
                    )
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

    # ------------------------------------------------------------------
    # Model capability inspection + selection
    # ------------------------------------------------------------------
    def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """
        Fetch a model's real capabilities (context length, parameter size, family)
        via /api/show, with in-memory caching so repeated calls are cheap.
        """
        with self._model_info_lock:
            cached = self._model_info_cache.get(model_name)
        if cached:
            return cached

        info = {"context_length": DEFAULT_MIN_CONTEXT, "parameter_size": "", "family": "", "quantization": ""}
        try:
            def req():
                with httpx.Client(timeout=10) as client:
                    response = client.post(f"{self.base_url}/api/show", json={"name": model_name})
                    response.raise_for_status()
                    return response

            response = self._execute_with_retry(req)
            data = response.json()
            details = data.get("details", {}) or {}
            info = {
                "context_length": self._extract_context_length(data),
                "parameter_size": details.get("parameter_size", ""),
                "family": details.get("family", ""),
                "quantization": details.get("quantization_level", ""),
            }
        except Exception as exc:
            logger.warning("Unable to fetch model info for %s: %s", model_name, exc)

        with self._model_info_lock:
            self._model_info_cache[model_name] = info
        return info

    @staticmethod
    def _extract_context_length(show_data: Dict[str, Any]) -> int:
        """
        Ollama's /api/show returns architecture-specific keys inside `model_info`,
        e.g. "llama.context_length" or "qwen2.context_length". Find whichever
        one is present rather than hardcoding an architecture name.
        """
        model_info = show_data.get("model_info", {}) or {}
        for key, value in model_info.items():
            if key.endswith("context_length") and isinstance(value, int) and value > 0:
                return value
        return DEFAULT_MIN_CONTEXT

    @staticmethod
    def _parse_param_size(size_str: str) -> float:
        """Parse a string like '7b' / '13.4B' / '70b' into a float count of billions."""
        if not size_str:
            return 0.0
        cleaned = size_str.strip().lower().rstrip("b")
        try:
            return float(cleaned)
        except ValueError:
            return 0.0

    def resolve_model(self, preferred_model: Optional[str] = None) -> str:
        """Pick the best available model from a fixed candidate/fallback list
        (kept for backward compatibility and for callers, like embeddings,
        that don't want capability-based auto-selection)."""
        all_models = self.list_models()
        # Filter out embedding models
        available_models = [m for m in all_models if "embed" not in m.lower()]
        
        candidates = []
        if preferred_model:
            candidates.append(preferred_model)

        from ..core.settings import settings as live_settings
        if live_settings.OLLAMA_MODEL:
            candidates.append(live_settings.OLLAMA_MODEL)

        if self.model:
            candidates.append(self.model)
        candidates.append(self.recommended_model)
        candidates.extend(live_settings.OLLAMA_MODEL_FALLBACKS)

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

    def resolve_best_model(self) -> str:
        """
        Inspect every locally installed model and score it, then pick the best
        fit for long-form, structured security analysis. Scoring favors context
        window size (the #1 cause of truncated reports) and parameter count
        (reasoning/formatting quality) roughly equally weighted.
        """
        all_models = self.list_models()
        # Filter out embedding models
        available_models = [m for m in all_models if "embed" not in m.lower()]
        
        if not available_models:
            return self.model or self.recommended_model

        scored = []
        for name in available_models:
            info = self.get_model_info(name)
            ctx = info.get("context_length", DEFAULT_MIN_CONTEXT)
            params = self._parse_param_size(info.get("parameter_size", ""))
            # Normalize roughly: context in the thousands, params in single/double
            # digits of billions, so scale params up so it meaningfully competes.
            score = (ctx / 1000.0) + (params * 4.0)
            scored.append((score, name, ctx, params))

        scored.sort(key=lambda x: x[0], reverse=True)
        best_score, best_name, best_ctx, best_params = scored[0]
        logger.info(
            "Auto-selected model '%s' (context=%d tokens, params=%sB, score=%.1f)",
            best_name, best_ctx, best_params or "?", best_score,
        )
        self.model = best_name
        return best_name

    def _select_model(self) -> str:
        """
        Unified model-selection entry point used by generate()/chat()/chat_stream().
        An explicit settings.OLLAMA_MODEL always wins if it's actually installed
        (manual override). Otherwise, if auto-selection is enabled, pick the best
        fit by capability; falls back to the legacy candidate-list behavior.
        """
        from ..core.settings import settings as live_settings
        available = self.list_models()
        preferred = getattr(live_settings, "OLLAMA_MODEL", None)

        if preferred and preferred in available:
            self.model = preferred
            return preferred

        if DEFAULT_AUTO_SELECT_MODEL and available:
            return self.resolve_best_model()

        return self.resolve_model()

    # ------------------------------------------------------------------
    # Context-window sizing (this is what actually fixes truncation)
    # ------------------------------------------------------------------
    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """Rough token estimate (~4 chars/token) — good enough for sizing num_ctx."""
        return max(1, len(text or "") // 4)

    def _compute_context_window(
        self,
        model_info: Dict[str, Any],
        prompt_text: str,
        desired_output_tokens: int = 4096,
    ) -> int:
        """
        Size num_ctx so the model has enough room for the prompt AND a full,
        complete answer, without exceeding the model's real max context or
        an admin-configurable ceiling (to protect memory on smaller machines).
        """
        model_max = model_info.get("context_length", DEFAULT_MIN_CONTEXT)
        prompt_tokens = self._estimate_tokens(prompt_text)
        needed = prompt_tokens + desired_output_tokens + 256  # safety margin
        window = max(DEFAULT_MIN_CONTEXT, min(needed, model_max, DEFAULT_MAX_CONTEXT))
        return window

    # ------------------------------------------------------------------
    # Truncation detection / stitching
    # ------------------------------------------------------------------
    def _is_truncated(self, text: str) -> bool:
        """
        Fallback truncation heuristic, used only when `done_reason` isn't
        available (e.g. an older Ollama version). Prefer done_reason=="length"
        wherever possible — it's what Ollama itself reports.
        """
        if not text:
            return False

        text_stripped = text.rstrip()
        if not text_stripped:
            return False

        if text_stripped.count("```") % 2 != 0:
            logger.info("Truncation heuristic: unclosed triple backticks.")
            return True

        last_char = text_stripped[-1]
        if last_char.isalnum() or last_char in [",", "-", ":", ";", "("]:
            logger.info(f"Truncation heuristic: text ends with suspect character '{last_char}'.")
            return True

        lines = text_stripped.split("\n")
        if lines:
            last_line = lines[-1].strip()
            if last_line.startswith(("-", "*", "+")) and not any(
                last_line.endswith(p) for p in [".", "!", "?", "```"]
            ):
                if len(last_line) < 15:
                    logger.info("Truncation heuristic: possible cut-off list item.")
                    return True

        return False

    def _stitch_responses(self, prefix: str, continuation: str) -> str:
        """Stitch a partial response and its continuation together cleanly."""
        prefix_clean = prefix.rstrip()
        continuation_clean = continuation.lstrip()

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

        if continuation_clean.startswith("..."):
            continuation_clean = continuation_clean[3:].lstrip()

        if prefix_clean and continuation_clean:
            last_char = prefix_clean[-1]
            first_char = continuation_clean[0]
            if last_char.isalnum() and first_char.isalnum():
                return f"{prefix_clean} {continuation_clean}"

        return f"{prefix_clean}\n{continuation_clean}"

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_output_tokens: int = 4096,
    ) -> str:
        """Send a single-turn generation request to Ollama with correctly-sized
        context and automatic, reason-aware continuation."""
        model_name = self._select_model()
        model_info = self.get_model_info(model_name)
        full_prompt_text = (system_prompt or "") + prompt
        num_ctx = self._compute_context_window(model_info, full_prompt_text, max_output_tokens)

        payload: Dict[str, Any] = {
            "model": model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": -1,
                "num_ctx": num_ctx,
                "top_p": 0.9,
                "top_k": 40,
            },
        }
        if system_prompt:
            payload["system"] = system_prompt

        try:
            def req():
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(f"{self.base_url}/api/generate", json=payload)
                    response.raise_for_status()
                    return response

            response = self._execute_with_retry(req)
            data = response.json()
            response_text = data.get("response", "")
            done_reason = data.get("done_reason", "stop")
        except httpx.ConnectError:
            logger.warning("Ollama not reachable at %s", self.base_url)
            return self._fallback_response("Ollama service is not available. Please start Ollama locally.")
        except httpx.TimeoutException:
            logger.warning("Ollama request timed out after %d seconds", self.timeout)
            return self._fallback_response(
                "Request timed out. The model is taking longer to respond. Please try again in a moment."
            )
        except httpx.HTTPStatusError as exc:
            logger.warning("Ollama generate returned %s", exc.response.status_code)
            return self._fallback_response(
                "The selected Ollama model could not be used. The app will try a detected local model automatically when available."
            )
        except Exception as exc:
            logger.error("Ollama generate error: %s", exc)
            return self._fallback_response(f"AI service error: {exc}")

        iter_count = 0
        while (done_reason == "length" or self._is_truncated(response_text)) and iter_count < 3:
            iter_count += 1
            logger.info(f"Auto-continuing generation (context/length limit hit), iteration {iter_count}...")
            continuation_prompt = (
                f"{prompt}\n\n[Previous Partial Response]:\n{response_text}\n\n"
                f"[Instruction]: Your previous response was cut off. Continue exactly where you left off, "
                f"without repeating any of your previous text, so the response is fully complete."
            )
            # Re-size num_ctx for the growing conversation each time.
            num_ctx_cont = self._compute_context_window(
                model_info, (system_prompt or "") + continuation_prompt, max_output_tokens
            )
            payload_continue = {
                "model": model_name,
                "prompt": continuation_prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": -1,
                    "num_ctx": num_ctx_cont,
                    "top_p": 0.9,
                    "top_k": 40,
                },
            }
            if system_prompt:
                payload_continue["system"] = system_prompt

            try:
                def req_cont():
                    with httpx.Client(timeout=self.timeout) as client:
                        resp = client.post(f"{self.base_url}/api/generate", json=payload_continue)
                        resp.raise_for_status()
                        return resp

                resp_cont = self._execute_with_retry(req_cont)
                data_cont = resp_cont.json()
                cont_text = data_cont.get("response", "")
                done_reason = data_cont.get("done_reason", "stop")
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
        max_output_tokens: int = 4096,
    ) -> str:
        """Send a multi-turn chat request to Ollama with correctly-sized context
        and automatic, reason-aware continuation."""
        model_name = self._select_model()
        model_info = self.get_model_info(model_name)
        prompt_text = (system_prompt or "") + "\n".join(m.get("content", "") for m in messages)
        num_ctx = self._compute_context_window(model_info, prompt_text, max_output_tokens)

        payload: Dict[str, Any] = {
            "model": model_name,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": -1,
                "num_ctx": num_ctx,
                "top_p": 0.9,
                "top_k": 40,
            },
        }
        if system_prompt:
            payload["messages"] = [{"role": "system", "content": system_prompt}] + messages

        try:
            def req():
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(f"{self.base_url}/api/chat", json=payload)
                    response.raise_for_status()
                    return response

            response = self._execute_with_retry(req)
            data = response.json()
            message = data.get("message") or {} if isinstance(data, dict) else {}
            response_text = message.get("content", "") if isinstance(message, dict) else ""
            done_reason = data.get("done_reason", "stop") if isinstance(data, dict) else "stop"
        except httpx.ConnectError:
            return self._fallback_response("Ollama service is not available. Please start Ollama locally.")
        except httpx.TimeoutException:
            return self._fallback_response(
                f"Request timed out after {self.timeout} seconds. Model response is taking longer than expected. Please try again."
            )
        except httpx.HTTPStatusError as exc:
            logger.warning("Ollama chat returned %s", exc.response.status_code)
            return self._fallback_response(
                "The selected Ollama model was not found. The app will auto-select a compatible local model when one is available."
            )
        except Exception as exc:
            logger.error("Ollama chat error: %s", exc)
            return self._fallback_response(f"AI service error: {exc}")

        iter_count = 0
        current_messages = list(messages)
        while (done_reason == "length" or self._is_truncated(response_text)) and iter_count < 3:
            iter_count += 1
            logger.info(f"Auto-continuing chat response (context/length limit hit), iteration {iter_count}...")

            continuation_messages = current_messages + [
                {"role": "assistant", "content": response_text},
                {
                    "role": "user",
                    "content": "Your previous response was cut off. Continue exactly where you left off, "
                    "without repeating any of your previous text, so the response is fully complete.",
                },
            ]
            cont_prompt_text = (system_prompt or "") + "\n".join(
                m.get("content", "") for m in continuation_messages
            )
            num_ctx_cont = self._compute_context_window(model_info, cont_prompt_text, max_output_tokens)

            payload_continue = {
                "model": model_name,
                "messages": continuation_messages,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": -1,
                    "num_ctx": num_ctx_cont,
                    "top_p": 0.9,
                    "top_k": 40,
                },
            }
            if system_prompt:
                payload_continue["messages"] = [{"role": "system", "content": system_prompt}] + continuation_messages

            try:
                def req_cont():
                    with httpx.Client(timeout=self.timeout) as client:
                        resp = client.post(f"{self.base_url}/api/chat", json=payload_continue)
                        resp.raise_for_status()
                        return resp

                resp_cont = self._execute_with_retry(req_cont)
                data_cont = resp_cont.json()
                if isinstance(data_cont, dict):
                    msg_cont = data_cont.get("message") or {}
                    cont_text = msg_cont.get("content", "")
                    done_reason = data_cont.get("done_reason", "stop")
                    if cont_text:
                        response_text = self._stitch_responses(response_text, cont_text)
                        current_messages = continuation_messages
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
        max_output_tokens: int = 4096,
    ):
        """Yield tokens from a multi-turn streaming chat request to Ollama, with
        correctly-sized context and automatic continuation if the stream ends
        because the model hit its length/context limit rather than a natural stop."""
        model_name = self._select_model()
        model_info = self.get_model_info(model_name)
        prompt_text = (system_prompt or "") + "\n".join(m.get("content", "") for m in messages)
        num_ctx = self._compute_context_window(model_info, prompt_text, max_output_tokens)

        def build_payload(msgs: List[Dict[str, str]]) -> Dict[str, Any]:
            payload = {
                "model": model_name,
                "messages": msgs,
                "stream": True,
                "options": {
                    "temperature": temperature,
                    "num_predict": -1,
                    "num_ctx": num_ctx,
                    "top_p": 0.9,
                    "top_k": 40,
                },
            }
            if system_prompt:
                payload["messages"] = [{"role": "system", "content": system_prompt}] + msgs
            return payload

        current_messages = list(messages)
        max_continuations = 3
        iter_count = 0

        while True:
            done_reason = "stop"
            chunk_text = ""
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    with client.stream("POST", f"{self.base_url}/api/chat", json=build_payload(current_messages)) as response:
                        response.raise_for_status()
                        for line in response.iter_lines():
                            if not line:
                                continue
                            try:
                                data = json.loads(line)
                            except Exception as exc:
                                logger.error("Error parsing stream line: %s", exc)
                                continue
                            if not isinstance(data, dict):
                                continue
                            message = data.get("message") or {}
                            content = message.get("content", "")
                            if content:
                                chunk_text += content
                                yield content
                            if data.get("done"):
                                done_reason = data.get("done_reason", "stop")
            except Exception as exc:
                logger.error("Ollama streaming error: %s", exc)
                yield f"\n\n> ⚠️ **AI Streaming Error**: {exc}\n"
                return

            if done_reason == "length" and iter_count < max_continuations:
                iter_count += 1
                logger.info(f"Stream hit context/length limit, auto-continuing, iteration {iter_count}...")
                current_messages = current_messages + [
                    {"role": "assistant", "content": chunk_text},
                    {
                        "role": "user",
                        "content": "Continue exactly where you left off, without repeating any previous "
                        "text, until the response is fully complete.",
                    },
                ]
                continue

            break

    def get_embeddings(self, text: str) -> List[float]:
        """Get embedding vector for text using Ollama. Uses the legacy resolve_model
        path since embedding models aren't scored the same way as chat models."""
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

**Evidence discipline:**
Do not invent affected assets, successful compromise, data access, persistence, or attacker identity. Clearly label
confirmed evidence, reasonable inference, and unknowns. Explain the likely attack path from the supplied telemetry.

Please provide a comprehensive analysis with:
1. **Executive Summary** (2-3 sentences)
2. **Attack Analysis** (detailed step-by-step breakdown of what happened)
3. **Immediate Containment Steps** (numbered list with specific actions)
4. **Investigation Checklist** (detailed items to check)
5. **Long-Term Hardening Recommendations** (preventive measures)
6. **Confirmed Evidence vs. Analyst Inference**
7. **Attacker Objective and Potential Organizational Impact** (only where supported; otherwise state what must be verified)

Ensure the response is complete and detailed, using markdown formatting with tables where appropriate for clarity."""

        # Incident reports are long and structured — give them a larger output budget.
        result = self.client.generate(prompt, system_prompt=SYSTEM_PROMPT_ANALYST, max_output_tokens=6000)

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
        return self.client.generate(prompt, system_prompt=SYSTEM_PROMPT_EXPLAINER, max_output_tokens=4096)


class ChatService:
    """Multi-turn conversational AI for SOC analysts."""

    def __init__(self, client: Optional[OllamaClient] = None):
        self.client = client or OllamaClient()

    def optimize_history(self, history: List[Dict[str, str]], max_tokens: int = 3000) -> List[Dict[str, str]]:
        """
        Optimize conversation history by budgeting tokens, removing duplicate content,
        and summarizing older turns if they exceed limits.
        """
        unique_history = []
        seen = set()
        for h in history:
            content_hash = (h["role"], (h["content"] or "").strip())
            if content_hash not in seen:
                seen.add(content_hash)
                unique_history.append(h)

        total_chars = sum(len(h["content"] or "") for h in unique_history)
        approx_tokens = total_chars // 4

        if approx_tokens <= max_tokens:
            return unique_history

        logger.info("Conversation history (%d tokens) exceeds budget (%d). Compressing...", approx_tokens, max_tokens)

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
            summary_prompt = (
                "Summarize the following security conversation history in 2-3 sentences, "
                f"highlighting key questions and findings:\n\n{older_text}"
            )
            try:
                summary = self.client.generate(
                    summary_prompt,
                    system_prompt="You are a SOC assistant summarizing earlier chat history. Be extremely brief.",
                    temperature=0.1,
                    max_output_tokens=256,
                )
                if summary and not summary.startswith(">"):
                    compressed_history.append({
                        "role": "system",
                        "content": f"[Summary of earlier conversation turns]: {summary}"
                    })
            except Exception as e:
                logger.warning("Conversation summarization failed: %s", e)

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
            final_message = f"[Knowledge Base Context]\n{rag_context}\n\n[User Question]\n{user_message}"

        messages = list(optimized_history) + [{"role": "user", "content": final_message}]
        return self.client.chat(messages, system_prompt=SYSTEM_PROMPT_CHAT, max_output_tokens=4096)

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
            final_message = f"[Knowledge Base Context]\n{rag_context}\n\n[User Question]\n{user_message}"

        messages = list(optimized_history) + [{"role": "user", "content": final_message}]
        return self.client.chat_stream(messages, system_prompt=SYSTEM_PROMPT_CHAT, max_output_tokens=4096)
