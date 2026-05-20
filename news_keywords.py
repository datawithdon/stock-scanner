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
    "going private", "management buyout", "mbo",
    "special committee", "exploration of strategic",
]

ANALYST = [
    "upgrade", "upgraded",
    "outperform", "overweight",
    "strong buy", "initiates coverage", "initiate",
    "price target raise", "price target increase", "pt raise",
    "top pick", "double upgrade", "best idea",
    "catalyst call", "out of consensus",
    "buy rating", "reiterate buy", "raised target",
    "price target lifted", "new coverage",
    "bullish", "conviction buy",
]

EARNINGS = [
    "beat estimates", "beat expectations", "earnings beat",
    "eps beat", "earnings surprise", "blowout quarter",
    "raised guidance", "raised outlook", "raised forecast",
    "revenue beat", "above consensus", "record revenue",
    "record earnings", "record quarter", "strong results",
    "raised full year", "raised annual",
]

CATALYST = [
    "fda approval", "fda approved", "fda clearance",
    "phase 3", "phase iii", "clinical trial results",
    "regulatory approval", "breakthrough therapy",
    "emergency use", "fast track designation",
    "contract awarded", "awarded contract", "major contract",
    "government contract", "dod contract", "defense contract",
    "partnership agreement", "licensing deal", "licensing agreement",
    "product launch", "commercial launch", "new product",
    "patent granted", "patent approval", "patent awarded",
    "share buyback", "stock repurchase", "buyback program",
    "special dividend", "dividend increase", "dividend hike",
    "short squeeze", "heavily shorted", "high short interest",
    "going concern removed", "debt refinanced",
]

SECTOR = [
    "artificial intelligence", " ai ", "ai-powered", "llm", "large language model",
    "data center", "hyperscaler", "gpu cluster",
    "optical networking", "silicon photonics", "coherent optics",
    "glp-1", "obesity drug", "weight loss drug", "semaglutide",
    "quantum computing", "quantum chip",
    "nuclear power", "small modular reactor", "smr",
    "power grid", "energy storage", "battery technology",
    "autonomous vehicle", "self-driving", "robotaxi",
    "semiconductor shortage", "chip shortage", "onshoring",
    "tariff", "reshoring", "nearshoring",
    "cybersecurity", "cyber attack", "ransomware",
    "electric vehicle", " ev ", "ev battery",
    "robotics", "automation", "humanoid",
    "space", "satellite", "launch vehicle",
    "rare earth", "lithium", "critical minerals",
    "mrna", "gene therapy", "crispr",
    "blockchain", "crypto", "bitcoin", "ethereum",
    "defense spending", "military contract",
]

INSIDER = [
    "insider buying", "insider purchase",
    "form 4", "beneficial owner",
    "sc 13d", "sc 13g",
    "cluster buy", "director bought", "ceo bought", "cfo bought",
    "10% stake", "activist investor", "activist stake",
    "schedule 13d", "significant shareholder",
    "increased stake", "bought shares",
]

_ALL = MA + ANALYST + EARNINGS + CATALYST + SECTOR + INSIDER


def passes_filter(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in _ALL)


def classify(text: str) -> str:
    t = text.lower()
    if any(kw in t for kw in MA):
        return "M&A"
    if any(kw in t for kw in ANALYST):
        return "analyst"
    if any(kw in t for kw in EARNINGS):
        return "earnings"
    if any(kw in t for kw in CATALYST):
        return "catalyst"
    if any(kw in t for kw in SECTOR):
        return "sector"
    if any(kw in t for kw in INSIDER):
        return "insider"
    return "other"
