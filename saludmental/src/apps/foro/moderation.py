from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Literal, Tuple
from django.conf import settings
from .profanity import contains_banned_words, get_banned_matches
import json
from urllib import request as _urlreq
from urllib.error import URLError, HTTPError
from urllib.parse import urlencode

Backend = Literal["local", "azure"]

@dataclass
class ModerationResult:
    allowed: bool
    reason: str = ""
    details: Optional[dict] = None


def _moderate_local(text: str) -> ModerationResult:
    if contains_banned_words(text):
        matches = get_banned_matches(text)
        return ModerationResult(False, reason="profanity", details={"matches": matches})
    return ModerationResult(True)


def _moderate_azure(text: str) -> ModerationResult:
    """
    Placeholder de integración con Azure AI Content Safety.
    Para habilitar:
      - Configurar en settings: AZURE_CONTENT_SAFETY_ENDPOINT, AZURE_CONTENT_SAFETY_KEY
      - Elegir backend "azure"
    """
    endpoint = getattr(settings, "AZURE_CONTENT_SAFETY_ENDPOINT", "").rstrip("/")
    key = getattr(settings, "AZURE_CONTENT_SAFETY_KEY", "")
    if not endpoint or not key:
        # Fallback seguro: si no está configurado, usa local
        return _moderate_local(text)
    api_version = "2023-10-01"
    url = f"{endpoint}/contentsafety/text:analyze?api-version={api_version}"
    categories = getattr(settings, "AZURE_CONTENT_SAFETY_CATEGORIES", [
        "Hate", "Sexual", "Violence", "SelfHarm"
    ])
    threshold = int(getattr(settings, "AZURE_CONTENT_SAFETY_THRESHOLD", 2))

    payload = {
        "text": text,
        "categories": categories,
        "outputType": "FourSeverity"
    }
    data = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Ocp-Apim-Subscription-Key": key,
    }

    req = _urlreq.Request(url, data=data, headers=headers, method="POST")
    try:
        with _urlreq.urlopen(req, timeout=3.5) as resp:
            raw = resp.read().decode("utf-8")
            result = json.loads(raw)
            # Esperado: result["categoriesAnalysis"] = [{"category": "Hate", "severity": 0..4}, ...]
            analysis = result.get("categoriesAnalysis", []) or result.get("category", [])
            details = {"categoriesAnalysis": analysis}
            # Si cualquier categoría alcanza el umbral, bloquear
            for item in analysis:
                sev = int(item.get("severity", 0))
                if sev >= threshold:
                    return ModerationResult(False, reason=item.get("category", "azure:blocked"), details=details)
            return ModerationResult(True, details=details)
    except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError):
        # Fallback conservador: si la IA falla, usar local para no bloquear indebidamente
        return _moderate_local(text)


def moderate_text(text: str) -> ModerationResult:
    backend: Backend = getattr(settings, "MODERATION_BACKEND", "local")  # type: ignore
    if backend == "azure":
        return _moderate_azure(text)
    return _moderate_local(text)
