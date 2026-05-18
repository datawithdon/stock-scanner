"""
Keyword lists for fast pre-filtering of news articles before Claude scoring.
Organized by catalyst type so we can label signals before sending to the API.
"""

MA = [
    "acquisition", "acquire", "acquired", "acquires",
    "merger", "merging", "merge",
    "buyout", "buy out",
    "spin-off", "spinoff", "spin off", "spinout",
    "strategic alternatives", "strategic review",
    "go-private", "take private", "taken private",
    "tender offer", "all-cash deal",
    "joint venture", "divestiture", "divest",
]

ANALYST = [
    "upgrade", "upgraded",
    "outperform", "overweight",
    "strong buy", "initiates coverage", "initiate",
    "price target raise", "price target increase", "pt raise",
    "top pick", "double upgrade", "best idea",
    "catalyst call", "out of consensus",
]

SECTOR = [
    "artificial intelligence", " ai ", "ai-powered", "llm", "large language model",
    "data center", "hyperscaler", "gpu cluster",
    "optical networking", "silicon photonics", "coherent optics",
    "glp-1", "obesity drug", "weight loss drug", "semaglutide",
    "quantum computing", "quantum chip",
    "nuclear power", "small modular reactor", "smr",
    "power grid", "energy storage", "battery",
    "autonomous vehicle", "self-driving", "robotaxi",
    "semiconductor shortage", "chip shortage", "onshoring",
    "tariff", "reshoring", "nearshoring",
]

INSIDER = [
    "insider buying", "insider purchase",
    "form 4", "beneficial owner",
    "sc 13d", "sc 13g",
    "cluster buy", "director bought", "ceo bought", "cfo bought",
    "10% stake", "activist investor", "activist stake",
    "schedule 13d",
]

_ALL = MA + ANALYST + SECTOR + INSIDER


def passes_filter(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in _ALL)


def classify(text: str) -> str:
    t = text.lower()
    if any(kw in t for kw in MA):
        return "M&A"
    if any(kw in t for kw in ANALYST):
        return "analyst"
    if any(kw in t for kw in SECTOR):
        return "sector"
    if any(kw in t for kw in INSIDER):
        return "insider"
    return "other"
