"""
Ollama AI Client — real HTTP calls to local Ollama service.
Includes OllamaClient, IncidentAnalyzer, ThreatExplainer, and ChatService.
"""
import logging
from typing import Any, Dict, List, Optional

import httpx

from ..core.settings import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_ANALYST = """You are an expert cybersecurity analyst for a SOC (Security Operations Center).
Analyze security incidents and provide clear, actionable insights.
Format your responses using markdown with clear sections, tables, and bullet points.
Be concise, technical, and focused on actionable recommendations.
Always include: Summary, Root Cause Analysis, Immediate Actions, and Long-Term Recommendations.
Use markdown tables for comparisons and detailed information."""

SYSTEM_PROMPT_EXPLAINER = """You are a cybersecurity educator explaining security alerts to junior analysts.
Use plain English, avoid jargon where possible, explain technical terms when used.
Always include: What Happened, Why It Matters, What To Do Next.
Format with clear markdown sections."""

SYSTEM_PROMPT_CHAT = """You are a cybersecurity AI assistant for a SOC team.
You help analysts investigate security logs, understand threats, and respond to incidents.
You have access to the organization's security knowledge base.
Be helpful, precise, and always recommend caution when unsure.
If context is provided from the knowledge base, use it to ground your response.
Format responses with markdown for clarity: use headers, bullet points, tables, and code blocks where appropriate.
Provide complete, detailed responses without truncation."""


class OllamaClient:
    """Sync client for the local Ollama LLM service."""

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

    def is_available(self) -> bool:
        """Check if Ollama service is reachable."""
        try:
            with httpx.Client(timeout=5) as client:
                r = client.get(f"{self.base_url}/api/tags")
                return r.status_code == 200
        except Exception:
            return False

    def list_models(self) -> List[str]:
        """Return the models currently available in Ollama."""
        try:
            with httpx.Client(timeout=5) as client:
                response = client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
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

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
    ) -> str:
        """Send a single-turn generation request to Ollama."""
        model_name = self.resolve_model()
        payload: Dict[str, Any] = {
            "model": model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": 5000,  # Increased from 512 to 2048 for longer responses
                "top_p": 0.9,
                "top_k": 40,
            },
        }
        if system_prompt:
            payload["system"] = system_prompt

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                return data.get("response", "")
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

    def chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.5,
    ) -> str:
        """Send a multi-turn chat request to Ollama."""
        model_name = self.resolve_model()
        payload: Dict[str, Any] = {
            "model": model_name,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": 2048,  # Increased from 512 to 2048
                "top_p": 0.9,
                "top_k": 40,
            },
        }
        if system_prompt:
            payload["messages"] = [{"role": "system", "content": system_prompt}] + messages

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                if isinstance(data, dict):
                    message = data.get("message") or {}
                    if isinstance(message, dict):
                        return message.get("content", "")
                return ""
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

    def get_embeddings(self, text: str) -> List[float]:
        """Get embedding vector for text using Ollama."""
        model_name = self.resolve_model()
        try:
            with httpx.Client(timeout=60) as client:
                response = client.post(
                    f"{self.base_url}/api/embeddings",
                    json={"model": model_name, "prompt": text},
                )
                response.raise_for_status()
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

    def respond(
        self,
        user_message: str,
        history: List[Dict[str, str]],
        rag_context: Optional[str] = None,
    ) -> str:
        """Generate a response to the user message, optionally grounded with RAG context."""
        final_message = user_message
        if rag_context:
            final_message = (
                f"[Knowledge Base Context]\n{rag_context}\n\n"
                f"[User Question]\n{user_message}"
            )

        messages = list(history) + [{"role": "user", "content": final_message}]
        return self.client.chat(messages, system_prompt=SYSTEM_PROMPT_CHAT)
