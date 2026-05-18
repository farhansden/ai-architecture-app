"""
Rule-based parser for architecture prompts. Handles plot dimensions (WxL and sqft),
bedrooms, bathrooms, floors, style, parking, budget, and furniture. Can be replaced with LLM later.
"""
import re
import math
from typing import Any

# 1 lakh = 100_000, 1 crore = 10_000_000
LAKH = 100_000
CRORE = 10_000_000

# Default plot aspect ratio (width:length) when only area is given
DEFAULT_PLOT_ASPECT = 2 / 3  # width/length

# Word form -> number for "two bedrooms", "three bathrooms"
WORD_NUMBERS: dict[str, int] = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}

# Known furniture terms to detect anywhere in prompt (and after "furniture(s)")
FURNITURE_TERMS = [
    "sofa", "table", "chair", "bed", "desk", "wardrobe", "dining table",
    "bookshelf", "cabinet", "tv unit", "coffee table", "side table",
    "dining chair", "armchair", "ottoman", "bench", "study table",
    "cupboard", "almirah", "rack", "shelves",
]

STYLE_KEYWORDS = [
    "modern",
    "contemporary",
    "traditional",
    "minimalist",
    "classic",
    "villa",
    "colonial",
    "rustic",
    "industrial",
    "luxury",
    "compact",
    "open",
    "scandinavian",
    "mediterranean",
]

PARKING_KEYWORDS = [
    "parking",
    "car parking",
    "garage",
    "car port",
    "parking space",
    "covered parking",
    "2 car",
    "two car",
]


def parse_prompt(text: str) -> dict[str, Any]:
    """
    Extract structured architecture constraints from natural language.
    Returns dict with: plot_width, plot_length, bedrooms, floors, style, parking, budget.
    Handles both "40x60" and "1200 sqft" style plot descriptions.
    """
    if not text or not isinstance(text, str):
        raise ValueError("Prompt must be a non-empty string")

    s = text.strip().lower()
    if not s:
        raise ValueError("Prompt cannot be empty or whitespace only")

    # Normalize: collapse spaces, handle "1200sqft" vs "1200 sqft"
    s = re.sub(r"\s+", " ", s)

    plot_width, plot_length = _parse_plot_dimensions(s)

    return {
        "plot_width": plot_width,
        "plot_length": plot_length,
        "bedrooms": _parse_bedrooms(s),
        "bathrooms": _parse_bathrooms(s),
        "floors": _parse_floors(s),
        "style": _parse_style(s),
        "parking": _parse_parking(s),
        "budget": _parse_budget(s),
        "furniture": _parse_furniture(s),
    }


def _parse_plot_dimensions(s: str) -> tuple[int, int]:
    """
    Return (width, length) in feet. Handles:
    - "40x60", "40 x 60", "40*60"
    - "1200 sqft", "1200sqft", "1200 square feet", "1200 sft"
    When only area is given, derive width/length using default aspect ratio.
    """
    # Explicit dimensions: 40x60, 30 x 40, etc.
    m = re.search(r"(\d+)\s*[xX*×]\s*(\d+)", s)
    if m:
        return (int(m.group(1)), int(m.group(2)))

    # Area in sqft: 1200 sqft, 1200sqft, 1200 square feet, 1200 sft, 1500 sq.ft
    area_m = re.search(
        r"(\d+(?:\.\d+)?)\s*(?:sq\.?\s*ft\.?|sqft|square\s*feet?|sft)\b",
        s,
        re.IGNORECASE,
    )
    if area_m:
        area = float(area_m.group(1))
        if area <= 0:
            return (0, 0)
        # Derive width and length: area = w * l, l = w / aspect => w * (w / aspect) = area => w = sqrt(area * aspect)
        width = math.sqrt(area * DEFAULT_PLOT_ASPECT)
        length = area / width
        return (int(round(width)), int(round(length)))

    return (0, 0)


def _parse_bedrooms(s: str) -> int:
    # 3BHK, 3 BHK, 2bhk
    bhk = 0
    m = re.search(r"(\d+)\s*bhk\b", s)
    if m:
        bhk = int(m.group(1))

    bedrooms = 0
    # 2 bedroom(s), 2 bed
    m = re.search(r"(\d+)\s*bed(?:room)?s?\b", s)
    if m:
        bedrooms = int(m.group(1))
    else:
        # two bedrooms, three bed
        for word, num in WORD_NUMBERS.items():
            if re.search(rf"\b{word}\s+bed(?:room)?s?\b", s):
                bedrooms = num
                break

    # If both are present and conflict (e.g., "1 bhk with 2 bedrooms"), prefer the larger signal.
    return max(bhk, bedrooms)


def _parse_bathrooms(s: str) -> int:
    m = re.search(r"(\d+)\s*bath(?:room)?s?\b", s)
    if m:
        return int(m.group(1))
    for word, num in WORD_NUMBERS.items():
        if re.search(rf"\b{word}\s+bath(?:room)?s?\b", s):
            return num
    return 0


def _parse_furniture(s: str) -> list[str]:
    """Extract furniture items: after 'furniture(s)' and/or known terms in prompt."""
    found: set[str] = set()
    # Words listed after "furniture" or "furnitures"
    m = re.search(r"furnitures?\s+([a-z\s]+?)(?=\s+budget|\s+parking|\s+floors?|\s*\d|$)", s)
    if m:
        for word in m.group(1).split():
            word = word.strip()
            if len(word) > 1 and word not in {"and", "with", "including"}:
                found.add(word)
    # Known furniture terms anywhere in prompt
    for term in FURNITURE_TERMS:
        if term in s:
            found.add(term)
    return sorted(found)


def _parse_floors(s: str) -> int:
    m = re.search(r"(\d+)\s*(?:floor|storey|storeys|storied)", s)
    if m:
        return int(m.group(1))
    m = re.search(r"g\s*\+\s*(\d+)", s)
    if m:
        return 1 + int(m.group(1))
    if any(w in s for w in ["single floor", "one floor", "ground floor only"]):
        return 1
    return 1


def _parse_style(s: str) -> str:
    for style in STYLE_KEYWORDS:
        if style in s:
            return style
    return "unspecified"


def _parse_parking(s: str) -> bool:
    return any(kw in s for kw in PARKING_KEYWORDS)


def _parse_budget(s: str) -> int:
    # "budget 120000", "budget 60 lakh", "budget: 5000000"
    m = re.search(r"budget\s*[:\s]*(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:\s|lakh|lacs|crore|inr|rs\.?|rupees?)?", s)
    if m:
        raw = m.group(1).replace(",", "")
        return int(float(raw))
    # 60 lakh, 60 lakhs, 60lakh, 60 lacs, 60 lac
    m = re.search(r"(\d+(?:\.\d+)?)\s*lakh(?:s)?", s)
    if not m:
        m = re.search(r"(\d+(?:\.\d+)?)\s*lac(?:s)?", s)
    if m:
        return int(float(m.group(1)) * LAKH)
    # 1 crore, 1.5 crore
    m = re.search(r"(\d+(?:\.\d+)?)\s*crore", s)
    if m:
        return int(float(m.group(1)) * CRORE)
    # Raw rupees: 6000000 inr, 60 lakh in numbers
    m = re.search(r"(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:inr|rs\.?|rupees?)\b", s)
    if m:
        return int(float(m.group(1).replace(",", "")))
    return 0
