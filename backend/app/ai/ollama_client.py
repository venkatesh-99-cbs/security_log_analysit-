"""
Ollama AI Client — real async HTTP calls to local Ollama service.
Includes OllamaClient, IncidentAnalyzer, ThreatExplainer, and ChatService.
"""
import logging
from typing import Any, Dict, List, Optional

import httpx

from ..core.settings import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_ANALYST = """You are an expert cybersecurity analyst for a SOC (Security Operations Center).
Analyze security incidents and provide clear, actionable insights.
Format your responses using markdown with clear sections.
Be concise, technical, and focused on actionable recommendations.
Always include: Summary, Root Cause Analysis, Immediate Actions, and Long-Term Recommendations."""

SYSTEM_PROMPT_EXPLAINER = """You are a cybersecurity educator explaining security alerts to junior analysts.
Use plain English, avoid jargon where possible, explain technical terms when used.
Always include: What Happened, Why It Matters, What To Do Next."""

SYSTEM_PROMPT_CHAT = """You are a cybersecurity AI assistant for a SOC team.
You help analysts investigate security logs, understand threats, and respond to incidents.
You have access to the organization's security knowledge base.
Be helpful, precise, and always recommend caution when unsure.
If context is provided from the knowledge base, use it to ground your response."""


class OllamaClient:
    """Async client for the local Ollama LLM service."""

    def __init__(
        self,
        base_url: str = settings.OLLAMA_BASE_URL,
        model: str = settings.OLLAMA_MODEL,
        timeout: int = 120,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    async def is_available(self) -> bool:
        """Check if Ollama service is reachable."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(f"{self.base_url}/api/tags")
                return r.status_code == 200
        except Exception:
            return False

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
    ) -> str:
        """Send a single-turn generation request to Ollama."""
        payload: Dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": 2048},
        }
        if system_prompt:
            payload["system"] = system_prompt

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
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
            logger.warning("Ollama request timed out")
            return self._fallback_response("Request timed out. The model may be loading — please retry.")
        except Exception as exc:
            logger.error("Ollama generate error: %s", exc)
            return self._fallback_response(f"AI service error: {exc}")

    async def chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.5,
    ) -> str:
        """Send a multi-turn chat request to Ollama."""
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": 2048},
        }
        if system_prompt:
            payload["messages"] = [{"role": "system", "content": system_prompt}] + messages

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                return data.get("message", {}).get("content", "")
        except httpx.ConnectError:
            return self._fallback_response("Ollama service is not available. Please start Ollama locally.")
        except Exception as exc:
            logger.error("Ollama chat error: %s", exc)
            return self._fallback_response(f"AI service error: {exc}")

    async def get_embeddings(self, text: str) -> List[float]:
        """Get embedding vector for text using Ollama."""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{self.base_url}/api/embeddings",
                    json={"model": self.model, "prompt": text},
                )
                response.raise_for_status()
                return response.json().get("embedding", [])
        except Exception as exc:
            logger.error("Ollama embeddings error: %s", exc)
            return []

    def _fallback_response(self, message: str) -> str:
        return f"> ⚠️ **AI Unavailable**\n> {message}\n\nPlease ensure Ollama is running: `ollama serve`"


class IncidentAnalyzer:
    """AI-powered analysis of security incidents."""

    def __init__(self, client: Optional[OllamaClient] = None):
        self.client = client or OllamaClient()

    async def analyze_incident(self, incident_data: Dict[str, Any]) -> str:
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

        prompt = f"""Analyze the following security incident and provide a detailed investigation report:

**Incident Title:** {title}
**Severity:** {severity.upper()}
**Threat Score:** {score}/100
**Source IP:** {source_ip}
**Log Events:** {log_count}

**Description:**
{description}

**MITRE ATT&CK Techniques Detected:**
{mitre_text}

Please provide:
1. **Executive Summary** (2-3 sentences)
2. **Attack Analysis** (what happened, step-by-step)
3. **Immediate Containment Steps** (numbered list)
4. **Investigation Checklist** (what to check next)
5. **Long-Term Hardening Recommendations**
"""
        return await self.client.generate(prompt, system_prompt=SYSTEM_PROMPT_ANALYST)


class ThreatExplainer:
    """Plain-English explanations of threats for junior analysts."""

    def __init__(self, client: Optional[OllamaClient] = None):
        self.client = client or OllamaClient()

    async def explain_alert(self, alert_data: Dict[str, Any]) -> str:
        alert_type = alert_data.get("type", "unknown").replace("_", " ").title()
        description = alert_data.get("description", "")
        severity = alert_data.get("severity", "unknown")

        prompt = f"""Explain this security alert in simple terms for a junior SOC analyst:

Alert Type: {alert_type}
Severity: {severity}
Details: {description}

Explain what this means, why it is concerning, and what immediate actions to take."""
        return await self.client.generate(prompt, system_prompt=SYSTEM_PROMPT_EXPLAINER)


class ChatService:
    """Multi-turn conversational AI for SOC analysts."""

    def __init__(self, client: Optional[OllamaClient] = None):
        self.client = client or OllamaClient()

    async def respond(
        self,
        user_message: str,
        history: List[Dict[str, str]],
        rag_context: Optional[str] = None,
    ) -> str:
        """
        Generate a response to the user message, optionally grounded with RAG context.
        
        Args:
            user_message: The latest user question.
            history: List of {"role": "user"/"assistant", "content": "..."} dicts.
            rag_context: Optional retrieved knowledge base context.
        """
        final_message = user_message
        if rag_context:
            final_message = (
                f"[Knowledge Base Context]\n{rag_context}\n\n"
                f"[User Question]\n{user_message}"
            )

        messages = list(history) + [{"role": "user", "content": final_message}]
        return await self.client.chat(messages, system_prompt=SYSTEM_PROMPT_CHAT)
