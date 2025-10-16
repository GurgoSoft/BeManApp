import re
import unicodedata
from functools import lru_cache
from typing import Iterable, List, Optional, Sequence, Set, Tuple
from django.conf import settings

# Listas multilingües (no exhaustivas) de insultos/profanidades genéricas
# Importante: evita incluir ataques a colectivos protegidos; estas listas buscan obscenidades generales.
_BANNED_WORDS: dict[str, Set[str]] = {
    "es": {
        # Español
        "mierda", "mierdita", "puta", "puto", "putear", "putita",
        "idiota", "idiotez", "imbecil", "estupido", "estupida",
        "pendejo", "pendeja", "pendejada",
        "tarado", "tonto", "tonta", "bobo", "boba",
        "gilipollas", "cabron", "cabrona", "cabronazo",
        "boludo", "boluda", "carajo",
        "chinga", "chingada", "chingado", "chingar", "chingadera",
        "cojones", "cojon", "cojuda", "cojudo",
        "joder", "coño", "coñazo",
        "verga", "culo", "zorra", "perra",
        "huevon", "huevona",
        "pelotudo", "pelotuda",
        "cagar", "cagada", "cagado", "cagon", "cagona",
        "mamon", "mamona",
        "pajero", "pajera",
        "malparido", "malparida", "marica", "maricón",
        "puta madre", "hijo de puta", "gonorrea", "carechimba",
        "la concha de tu madre", "me cago en",  # frases comunes
        # abreviaturas/regionalismos sin espacios
        "hijodeputa", "hijueputa", "conchesumadre", "conchatumadre",
        "ptm", "ctm", "csm",
        # regionalismos adicionales
        "pirobo", "piroba",
    },
    "en": {
        # Inglés
        "fuck", "fucking", "motherfucker", "mf", "shit", "bullshit", "asshole",
        "dick", "bastard", "bitch", "crap", "piss", "wanker", "prick", "jerk",
        "cunt",
    },
    "pt": {
        # Portugués
        "merda", "porra", "caralho", "puta", "puto", "idiota", "imbecil", "otario",
        "otaria", "babaca", "bosta", "cu",
    },
    "fr": {
        # Francés
        "merde", "putain", "con", "connard", "connasse", "salope", "encule",
        "batard",
    },
}

_SEPARATORS = r"[^a-z0-9]"  # Separadores tolerados tras normalizar a ASCII

_LEET_MAP = str.maketrans({
    "@": "a", "4": "a", "3": "e", "1": "i", "!": "i", "|": "i",
    "0": "o", "$": "s", "5": "s", "7": "t", "8": "b", "9": "g",
})

def _normalize(text: str) -> str:
    """Normaliza a ASCII en minúsculas y aplica un mapeo básico de leet-speak."""
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode("ascii")
    text = text.translate(_LEET_MAP)
    return text.lower()

def _squeeze_repeats(text: str, keep: int = 2) -> str:
    """Reduce repeticiones consecutivas de un mismo carácter (p. ej., miiierda → miierda)."""
    return re.sub(rf"(.)\1{{{keep},}}", r"\1" * keep, text)

def _build_word_regex(word: str, aggressive: bool) -> str:
    """Crea un patrón para una palabra. En modo agresivo tolera 0-1 separadores entre letras y plural común."""
    if aggressive:
        letters = list(word)
        # tolera 0-1 separadores entre letras: p[^a-z0-9]?u[^a-z0-9]?t... y plural típico (s|es)
        core = letters[0] + ''.join(fr"{_SEPARATORS}?{re.escape(ch)}" for ch in letters[1:])
        suffix = r"(?:s|es)?"  # plural simple
        return rf"(?<![a-z0-9])(?:{core}){suffix}(?![a-z0-9])"
    else:
        # coincidencia exacta por palabra completa con plural opcional simple
        return rf"\b{re.escape(word)}(?:s|es)?\b"

def _prepare_words(languages: Optional[Sequence[str]]) -> List[str]:
    if not languages:
        # Todas las lenguas por defecto
        langs = _BANNED_WORDS.keys()
    else:
        langs = languages
    words: Set[str] = set()
    for lang in langs:
        base = set(_BANNED_WORDS.get(lang, set()))
        # Permitir extender vía settings: EXTRA_BANNED_WORDS = {"es": ["...", ...], "en": ["..."]}
        extras_cfg = getattr(settings, "EXTRA_BANNED_WORDS", {}) or {}
        extras = set(map(str.lower, extras_cfg.get(lang, [])))
        words.update(base | extras)
    # Normaliza palabras base para construir el regex sobre texto normalizado
    return sorted({_normalize(w) for w in words}, key=len, reverse=True)

@lru_cache(maxsize=64)
def _compiled_pattern(langs_key: Tuple[str, ...], aggressive: bool) -> re.Pattern:
    words = _prepare_words(langs_key)
    if not words:
        # patrón que nunca coincide
        return re.compile(r"a^")
    pattern = "|".join(_build_word_regex(w, aggressive=aggressive) for w in words)
    flags = re.IGNORECASE
    return re.compile(pattern, flags)

def contains_banned_words(text: str, languages: Optional[Sequence[str]] = None, aggressive: bool = True) -> bool:
    """Devuelve True si el texto contiene palabras ofensivas.

    - languages: lista de códigos ("es", "en", "pt", "fr"); None = todas.
    - aggressive: tolera ofuscaciones típicas (leet, separadores, repeticiones).
    """
    if not text:
        return False
    norm = _normalize(text)
    if aggressive:
        norm = _squeeze_repeats(norm, keep=2)
    langs_key = tuple(sorted(languages)) if languages else tuple(sorted(_BANNED_WORDS.keys()))
    pattern = _compiled_pattern(langs_key, aggressive)
    return bool(pattern.search(norm))

def get_banned_matches(text: str, languages: Optional[Sequence[str]] = None, aggressive: bool = True) -> List[str]:
    """Devuelve una lista de fragmentos (normalizados) que coincidieron con el patrón de prohibidas."""
    if not text:
        return []
    norm = _normalize(text)
    if aggressive:
        norm = _squeeze_repeats(norm, keep=2)
    langs_key = tuple(sorted(languages)) if languages else tuple(sorted(_BANNED_WORDS.keys()))
    pattern = _compiled_pattern(langs_key, aggressive)
    return [m.group(0) for m in pattern.finditer(norm)]

def censor_text(text: str, languages: Optional[Sequence[str]] = None, aggressive: bool = True) -> str:
    """Censura aproximada (sobre texto normalizado). Útil para logs internos, no para mostrar al usuario."""
    if not text:
        return text
    norm = _normalize(text)
    if aggressive:
        norm = _squeeze_repeats(norm, keep=2)
    langs_key = tuple(sorted(languages)) if languages else tuple(sorted(_BANNED_WORDS.keys()))
    pattern = _compiled_pattern(langs_key, aggressive)
    return pattern.sub(lambda m: "*" * len(m.group(0)), norm)
