"""
LLM-based prompt parser. Extracts all architecture-related key-value pairs from
natural language, with sensible defaults for missing fields. Used when OPENAI_API_KEY is set.
"""
import json
import re
from typing import Any

# Core schema: always present in output, with defaults when not in prompt
CORE_DEFAULTS: dict[str, Any] = {
    "plot_width": 0,
    "plot_length": 0,
    "bedrooms": 0,
    "bathrooms": 0,
    "floors": 1,
    "style": "unspecified",
    "parking": False,
    "budget": 0,
    "furniture": [],
}

SYSTEM_PROMPT = """You are an architecture requirement parser. Extract structured data from the user's prompt.

Rules:
1. Always return valid JSON only, no markdown or explanation.
2. Include these core keys with appropriate types (use defaults if not mentioned):
   - plot_width (int, feet)
   - plot_length (int, feet)
   - bedrooms (int)
   - bathrooms (int)
   - floors (int, default 1)
   - style (string, e.g. modern, traditional)
   - parking (boolean)
   - budget (int, total rupees; convert "60 lakh" to 6000000, "1 crore" to 10000000)
   - furniture (array of strings, e.g. ["sofa", "table", "chair"])

3. If the user gives area only (e.g. "1200 sqft"), derive plot_width and plot_length (e.g. ~28x42 for 1200 sqft).
4. Add ANY other key-value pairs the user mentions: garden, balcony, home_office, open_kitchen, terrace, etc. Use snake_case for new keys. Use sensible types (bool, int, string, array).
5. Infer from context: "2 BHK" => bedrooms=2, "parking" => parking=true, "budget 120000" => budget=120000.
6. For numbers in words ("two bedrooms") use the numeric value."""


def parse_with_llm(prompt: str, *, api_key: str) -> dict[str, Any]:
    """
    Call OpenAI API to parse the prompt into structured JSON.
    Returns dict with core fields + any extra keys the LLM extracted.
    """
    try:
        from openai import OpenAI
    except ImportError:
        raise ValueError("openai package not installed; run: pip install openai")

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt.strip()},
        ],
        temperature=0.1,
        max_tokens=1024,
    )
    content = (response.choices[0].message.content or "").strip()
    # Strip markdown code block if present
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)
    data = json.loads(content)
    if not isinstance(data, dict):
        raise ValueError("LLM did not return a JSON object")
    return _normalize_llm_output(data)


def _normalize_llm_output(data: dict[str, Any]) -> dict[str, Any]:
    """Ensure core fields exist with correct types; merge defaults; preserve extra keys."""
    out: dict[str, Any] = {**CORE_DEFAULTS}

    for key, value in data.items():
        key_lower = key.lower().replace(" ", "_")
        if key_lower in CORE_DEFAULTS:
            out[key_lower] = _coerce_value(key_lower, value)
        else:
            out[key] = value

    # Ensure list for furniture
    if "furniture" in out and not isinstance(out["furniture"], list):
        out["furniture"] = [out["furniture"]] if out["furniture"] else []
    out["furniture"] = [str(x) for x in out["furniture"]]

    return out


def _coerce_value(key: str, value: Any) -> Any:
    """Coerce LLM output to expected types for core fields."""
    if value is None:
        return CORE_DEFAULTS[key]
    if key in ("plot_width", "plot_length", "bedrooms", "bathrooms", "floors", "budget"):
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return CORE_DEFAULTS[key]
    if key == "parking":
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("true", "yes", "1", "y")
        return bool(value)
    if key == "style":
        return str(value) if value else "unspecified"
    if key == "furniture":
        if isinstance(value, list):
            return [str(x) for x in value]
        return [str(value)] if value else []
    return value
