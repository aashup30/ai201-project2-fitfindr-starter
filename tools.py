"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Complete and test each tool before moving to agent.py.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

import os

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.

    Args:
        description: Keywords describing what the user is looking for
                     (e.g., "vintage graphic tee").
        size:        Size string to filter by, or None to skip size filtering.
                     Matching is case-insensitive (e.g., "M" matches "S/M").
        max_price:   Maximum price (inclusive), or None to skip price filtering.

    Returns:
        A list of matching listing dicts, sorted by relevance (best match first).
        Returns an empty list if nothing matches — does NOT raise an exception.

    Each listing dict has the following fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand, platform

    TODO:
        1. Load all listings with load_listings().
        2. Filter by max_price and size (if provided).
        3. Score each remaining listing by keyword overlap with `description`.
        4. Drop any listings with a score of 0 (no relevant matches).
        5. Sort by score, highest first, and return the listing dicts.

    Before writing code, fill in the Tool 1 section of planning.md.
    """
    listings = load_listings()

    # Filter by price and size
    filtered = []
    for item in listings:
        if max_price is not None and item["price"] > max_price:
            continue
        if size is not None and size.lower() not in item["size"].lower():
            continue
        filtered.append(item)

    # Score by keyword overlap with description
    keywords = set(description.lower().split())

    def score(item):
        fields = (
            item["title"].lower() + " "
            + item["description"].lower() + " "
            + item["category"].lower() + " "
            + " ".join(item["style_tags"]).lower()
        )
        return sum(1 for kw in keywords if kw in fields)

    # Drop zero-score listings and sort by score descending
    scored = [(item, score(item)) for item in filtered]
    scored = [(item, s) for item, s in scored if s > 0]
    scored.sort(key=lambda x: x[1], reverse=True)

    return [item for item, _ in scored]
    return []



# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.

    Args:
        new_item: A listing dict (the item the user is considering buying).
        wardrobe: A wardrobe dict with an 'items' key containing a list of
                  wardrobe item dicts. May be empty — handle this gracefully.

    Returns:
        A non-empty string with outfit suggestions.
        If the wardrobe is empty, offer general styling advice for the item
        rather than raising an exception or returning an empty string.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If empty: call the LLM with a prompt for general styling ideas
           (what kinds of items pair well, what vibe it suits, etc.).
        3. If not empty: format the wardrobe items into a prompt and ask
           the LLM to suggest specific outfit combinations using the new item
           and named pieces from the wardrobe.
        4. Return the LLM's response as a string.

    Before writing code, fill in the Tool 2 section of planning.md.
    """
    client = _get_groq_client()

    items = wardrobe.get("items", [])

    if not items:
        prompt = (
            f"I'm considering buying this thrifted item: {new_item['title']}. "
            f"It's a {new_item['category']} with these style tags: {', '.join(new_item['style_tags'])}. "
            f"Colors: {', '.join(new_item['colors'])}. "
            "I don't have my wardrobe handy — give me general styling advice. "
            "What kinds of pieces pair well with it? What vibe does it suit?"
        )
    else:
        wardrobe_lines = "\n".join(
            f"- {it['name']} ({it['category']}, {', '.join(it['colors'])}, {it.get('notes', '')})"
            for it in items
        )
        prompt = (
            f"I'm considering buying this thrifted item: {new_item['title']}. "
            f"It's a {new_item['category']} with style tags: {', '.join(new_item['style_tags'])}. "
            f"Colors: {', '.join(new_item['colors'])}.\n\n"
            f"Here's my current wardrobe:\n{wardrobe_lines}\n\n"
            "Suggest 1–2 complete outfit combinations using the new item and specific pieces "
            "from my wardrobe. Include brief styling notes for each."
        )

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )

    return response.choices[0].message.content or ""
    ##return ""


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.

    Args:
        outfit:   The outfit suggestion string from suggest_outfit().
        new_item: The listing dict for the thrifted item.

    Returns:
        A 2–4 sentence string usable as an Instagram/TikTok caption.
        If outfit is empty or missing, return a descriptive error message
        string — do NOT raise an exception.

    The caption should:
    - Feel casual and authentic (like a real OOTD post, not a product description)
    - Mention the item name, price, and platform naturally (once each)
    - Capture the outfit vibe in specific terms
    - Sound different each time for different inputs (use higher LLM temperature)

    TODO:
        1. Guard against an empty or whitespace-only outfit string.
        2. Build a prompt that gives the LLM the item details and the outfit,
           and asks for a caption matching the style guidelines above.
        3. Call the LLM and return the response.

    Before writing code, fill in the Tool 3 section of planning.md.
    """
    if not outfit or not outfit.strip():
        return (
            f"Couldn't generate a caption — outfit description was empty. "
            f"Here's what we found though: {new_item['title']} for ${new_item['price']} on {new_item['platform']}."
        )

    client = _get_groq_client()

    prompt = (
        f"Write a 2–4 sentence Instagram/TikTok caption for this thrifted outfit.\n\n"
        f"Thrifted item: {new_item['title']}, ${new_item['price']}, found on {new_item['platform']}.\n"
        f"Outfit: {outfit}\n\n"
        "Guidelines:\n"
        "- Sound like a real person posting an OOTD, not a product description\n"
        "- Mention the item name, price, and platform once each, naturally\n"
        "- Be specific about the vibe of the outfit\n"
        "- Keep it casual and shareable"
    )

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=1.0,
    )

    return response.choices[0].message.content
    return ""


# ── Tool 4: compare_price ─────────────────────────────────────────────────────

def compare_price(item: dict) -> dict:
    """
    Estimate whether a listing's price is fair by comparing it against
    similar items in the dataset.

    Args:
        item: A listing dict from search_listings containing title, price,
              category, style_tags, condition, and brand.

    Returns:
        A dict with keys: verdict, avg_comparable_price, comparable_count,
        and reasoning. Returns an error dict if fewer than 2 comparables exist.
    """
    listings = load_listings()

    comparables = [
        l for l in listings
        if l["id"] != item["id"]
        and l["category"] == item["category"]
        and any(tag in item["style_tags"] for tag in l["style_tags"])
    ]

    if len(comparables) < 2:
        return {
            "verdict": None,
            "avg_comparable_price": None,
            "comparable_count": len(comparables),
            "reasoning": "Not enough comparable listings to estimate price fairness.",
        }

    avg = sum(l["price"] for l in comparables) / len(comparables)
    price = item["price"]

    if price <= avg * 0.8:
        verdict = "great deal"
        reasoning = f"At ${price:.2f}, this is well below the average comparable price of ${avg:.2f}."
    elif price <= avg * 1.1:
        verdict = "fair"
        reasoning = f"At ${price:.2f}, this is in line with the average comparable price of ${avg:.2f}."
    else:
        verdict = "overpriced"
        reasoning = f"At ${price:.2f}, this is above the average comparable price of ${avg:.2f}."

    return {
        "verdict": verdict,
        "avg_comparable_price": round(avg, 2),
        "comparable_count": len(comparables),
        "reasoning": reasoning,
    }