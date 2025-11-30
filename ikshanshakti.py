# filename: newseo.py
# Shakti 1.3 — PW SEO Optimizer (Single + Batch + Chat)
# - Prompt library with L1/L2 presets (incl. PW Elite preset)
# - Dropdown selector instead of manual L1/L2 pasting
# - Single Optimize supports product URL auto-fetch (Amazon, Flipkart, Meesho, etc.)
# - API keys persisted in .shakti_keys.json (no need to paste every time)
# - Multi-engine support: OpenAI (primary) + optional OpenAI-2 / Gemini / Claude
# - Batch optimization (≤10 rows) using the same prompt presets

import io
import os
import sys
import re
import json
import zipfile
import unicodedata
from datetime import datetime
from pathlib import Path

import streamlit as st
import pandas as pd

# Optional imports for URL auto-fetch
try:
    import requests
    from bs4 import BeautifulSoup
except Exception:
    requests = None
    BeautifulSoup = None

# ----------------------- SDKs -----------------------
try:
    from openai import OpenAI
except Exception:
    OpenAI = None

try:
    import google.generativeai as genai
except Exception:
    genai = None

try:
    import anthropic
except Exception:
    anthropic = None

# ----------------------- Model Maps -----------------------
OPENAI_MODELS = {
    "GPT-5.1 Thinking": "gpt-5.1-thinking",
    "GPT-5.1": "gpt-5.1",
    "GPT-5": "gpt-5",
    "GPT-4.1": "gpt-4.1-mini",
}

GEMINI_MODELS = {
    "Gemini 2.5 Flash": "gemini-2.5-flash",
    "Gemini 1.5 Pro": "gemini-1.5-pro",
}

CLAUDE_MODELS = {
    "Claude Sonnet 3.7": "claude-3-7-sonnet-latest",
    "Claude Haiku 3.5": "claude-3-5-haiku-latest",
}

# ------------- Inline keys (fallback; normally use .shakti_keys.json) -------------
OPENAI_API_KEY_INLINE = ""
GEMINI_API_KEY_INLINE = ""
ANTHROPIC_API_KEY_INLINE = ""

# ------------- Persistent key storage -------------
KEYS_FILE = Path(".shakti_keys.json")


def load_saved_keys():
    """Load saved API keys from local JSON file."""
    if not KEYS_FILE.exists():
        return {"openai": "", "gemini": "", "anthropic": ""}
    try:
        data = json.loads(KEYS_FILE.read_text(encoding="utf-8"))
        return {
            "openai": data.get("openai", "") or "",
            "gemini": data.get("gemini", "") or "",
            "anthropic": data.get("anthropic", "") or "",
        }
    except Exception:
        return {"openai": "", "gemini": "", "anthropic": ""}


def save_keys(openai_key: str, gemini_key: str, anthropic_key: str):
    """Save API keys to local JSON file."""
    try:
        data = {
            "openai": openai_key or "",
            "gemini": gemini_key or "",
            "anthropic": anthropic_key or "",
        }
        KEYS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return True, ""
    except Exception as e:
        return False, str(e)


# ----------------------- Helper Functions -----------------------
def to_utf8_clean(x: str) -> str:
    if not isinstance(x, str):
        x = str(x or "")
    x = unicodedata.normalize("NFKC", x)
    return x.replace("\u00a0", " ").strip()


def coerce_json(txt: str):
    """Try to extract JSON from model output."""
    if not txt:
        return None
    txt = txt.strip()
    # Strip fenced code blocks if present
    fence_match = re.search(r"```(?:json)?(.*?)```", txt, flags=re.S | re.I)
    if fence_match:
        txt = fence_match.group(1).strip()
    # Remove leading commentary before first '{'
    if "{" in txt:
        txt = txt[txt.index("{}") :] if txt.startswith("{}") else txt[txt.index("{") :]
    try:
        return json.loads(txt)
    except Exception:
        try:
            # Fallback if previous slicing misbehaved
            start = txt.find("{")
            end = txt.rfind("}")
            if start != -1 and end != -1 and end > start:
                return json.loads(txt[start : end + 1])
        except Exception:
            return None
        return None


def ensure_listing_shape(obj):
    """Ensure result has the expected listing fields."""
    if not isinstance(obj, dict):
        obj = {}
    return {
        "new_title": obj.get("new_title", "") or "",
        "new_description": obj.get("new_description", "") or "",
        "keywords_short": obj.get("keywords_short", []) or [],
        "keywords_mid": obj.get("keywords_mid", []) or [],
        "keywords_long": obj.get("keywords_long", []) or [],
    }


def extract_text_from_docx(file_bytes: bytes) -> str:
    """Simple DOCX text extractor (if you ever re-use docx prompts)."""
    try:
        from xml.etree import ElementTree as ET

        with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
            xml = z.read("word/document.xml")
        root = ET.fromstring(xml)
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        texts = [t.text or "" for t in root.iterfind(".//w:t", ns)]
        return " ".join("".join(texts).split()).strip()
    except Exception as e:
        return f"[DOCX READ ERROR] {e}"


# ----------------------- URL Fetch Helper -----------------------
def fetch_listing_from_url(url: str):
    """
    Fetch a product page and try to extract approximate title + description.
    Works best for Amazon / Flipkart / Meesho. Fails gracefully if libs missing.
    """
    url = (url or "").strip()
    if not url:
        return "", ""

    if requests is None:
        return "", ""

    try:
        resp = requests.get(
            url,
            timeout=12,
            headers={
                "User-Agent": "Mozilla/5.0 (Shakti-SEO-1.3)",
                "Accept-Language": "en-IN,en;q=0.9",
            },
        )
        resp.raise_for_status()
        html = resp.text
    except Exception:
        return "", ""

    title, desc = "", ""

    if BeautifulSoup is not None:
        soup = BeautifulSoup(html, "html.parser")

        # Title extraction
        if "amazon." in url:
            t = soup.select_one("#productTitle") or soup.select_one("#title")
            if t:
                title = t.get_text(strip=True)
        if not title and soup.title and soup.title.string:
            title = soup.title.get_text(strip=True)

        # Description extraction (approx)
        if "amazon." in url:
            bullets = soup.select_one("#feature-bullets")
            if bullets:
                points = [li.get_text(" ", strip=True) for li in bullets.select("li")]
                desc = "<br>".join(points)
            if not desc:
                pd = soup.select_one("#productDescription")
                if pd:
                    desc = pd.get_text(" ", strip=True)
        # Generic fallback
        if not desc:
            meta = soup.find("meta", attrs={"name": "description"}) or soup.find(
                "meta", attrs={"property": "og:description"}
            )
            if meta and meta.get("content"):
                desc = meta["content"].strip()
    else:
        # Fallback: raw HTML regex for title
        m = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.S | re.I)
        if m:
            title = re.sub(r"\s+", " ", m.group(1)).strip()

    return to_utf8_clean(title), to_utf8_clean(desc)


# ----------------------- Shakti Knowledge Base + Prompts -----------------------

SHAKTI_KB = """
You are Shakti 1.3 — PW in-house Amazon SEO optimizer, built for Physics Wallah (PW) and
general e-commerce use cases (books, edtech products, stationery, retail, etc.).

Core non-negotiable rules:
- ALWAYS respect Amazon-style limits: Title <= 200 characters; Description HTML <= 2000 characters.
- Avoid keyword stuffing; keep language natural, student-first, and exam-context aware.
- Preserve factual accuracy. Never invent exam names, years, or features that are not in the source.
- Preserve any product links that appear in the original description. Do not drop or break them.
- Maintain JSON structure exactly when requested (new_title, new_description, keywords_short, keywords_mid, keywords_long).
- Optimize for discoverability, CTR, AND conversion — not just random keyword injection.
- Assume Indian exam-prep and Indian buyer behaviour unless clearly global/general.
""".strip()

# ----- L1: PW Amazon SEO Optimization Engine — Elite Edition -----
L1_PW_ELITE = """
You are an elite Amazon SEO strategist specializing in Physics Wallah (PW), India's most trusted education brand.
Your listings consistently rank on the first page for academic and competitive exam books.

You deeply understand:
- Amazon's A9/A10 ranking algorithm and its evolution.
- Indian exam-prep search behavior and urgency patterns (latest edition, 2025, updated syllabus, etc.).
- The balance between discoverability, CTR, and actual conversions.
- Exam terminology across JEE, NEET, UPSC, SSC, Banking, CBSE/ICSE, State Boards, and teaching exams.

Inputs given to you:
- Book Title and Book Type.
- Existing Product Description (possibly messy, repetitive, or non-SEO friendly).

Your mission:
Transform any given listing into a high-ranking, high-converting Amazon product using this 8-step framework:

STEP 1: Audience Intelligence
- Identify exact target segment (JEE, NEET, UPSC, SSC, Banking, CBSE/ICSE, State Board, Teaching Exams, etc.).
- Map their needs: theory foundation, quick revision, PYQs, formula sheets, mock tests, chapter-wise practice, etc.

STEP 2: Search Intent Mapping
- Derive 2–3 realistic Amazon search queries students would type.
- Consider Hindi-English code-mixing, exam abbreviations (PYQ, MCQ, Prelims/Mains), and urgency cues (latest, 2025, updated syllabus).

STEP 3: Strategic Keyword Architecture
- Build ~15 keywords split into short-tail, mid-tail, and long-tail.
- Use exam + subject, exam phase (Prelims/Mains), year variants (2024/2025/2026), synonyms (PYQ/previous year questions/solved papers).

STEP 4: Keyword Distribution Strategy
- Title: 1–2 short-tail + 1 high-value mid-tail keyword.
- Description: Use all keyword clusters naturally, keyword density <3%.
- Backend search terms: Remaining unused but relevant variants; avoid repeating title/description keywords.

STEP 5: Title Optimization (<= 200 characters)
Use pattern:
[Exam + Subject/Topic] | [Content Type/Value Proposition] | [Edition/Year] | PW

Principles:
- Lead with exam name.
- Include specific numbers (chapters, questions, years).
- End with “PW” for brand authority.
- Use power words like Complete, Ultimate, Comprehensive, Quick, Master.
- Avoid filler words like “best,” “for your,” “#1.”

STEP 6: Description Crafting (HTML, <= 2000 characters)
Structure:
1) Hook paragraph (40–60 words) describing student pain point + clear solution.
2) 5–7 bolded feature bullets (<b>...</b><br>) with benefits and specifics.
3) “What’s Inside” section with chapter/section breakdown and special features (QR codes, online tests, infographics).
4) PW credibility anchor (expert faculty, years of experience, number of aspirants).
5) Motivational CTA that is authentic, not salesy.

Tone:
- Confident but approachable.
- Aspirant-centric and outcome-focused.
- Clear, scannable, mobile-friendly formatting.

STEP 7: Backend Search Terms (<= 250 characters)
- Comma-separated list of unused relevant keywords.
- Include exam full forms, alternate spellings, Hindi transliterations, and generic terms like “mcq book,” “study material.”

STEP 8: Quality Assurance Checklist
- Respect character limits.
- No exaggerated or prohibited claims (“guaranteed,” “#1” etc.).
- Maintain PW’s student-first voice and factual accuracy.
- Ensure all original product links remain intact in the description.

Your deliverable for L1 (as JSON):
{
  "new_title": "...",
  "new_description": "...",  // HTML formatted
  "keywords_short": ["...", "..."],
  "keywords_mid": ["...", "..."],
  "keywords_long": ["...", "..."]
}

Return ONLY this JSON. Do not include explanations or commentary.
""".strip()

# ----- L2: Title enrichment + mandatory keyword preservation -----
L2_PW_ENRICH = """
You act as a Level-2 refinement engine for Amazon SEO listings.

You receive:
- A JSON object with: new_title, new_description, keywords_short, keywords_mid, keywords_long.
- Context of the original product so you can refine and enrich without breaking meaning.

Your L2 responsibilities:
1) Enrich the title with any essential, context-appropriate keywords that are missing but necessary for clarity and SEO.
   - Especially words like “Combo”, “Set of 2”, “Set of 3”, “Pack”, “Bundle” or similar identifiers
     whenever the product genuinely represents multiple items or a combo.
2) If the original title indicates COMBO, Combo Set, Combo Pack, or similar:
   - Ensure the optimized title clearly contains that identifier.
   - Never silently remove or downgrade such identifiers.
3) Maintain:
   - Accuracy with respect to the real product.
   - Clarity, readability, and consistency.
   - Natural language without keyword stuffing.

Mandatory link rule:
- If the original description contains any links (product links, cross-promotion URLs, external resources),
  they must be preserved exactly (same text, same URL).
- You may reflow text around them for readability, but you must not delete, alter, or break the links.

Format:
- Keep the JSON structure exactly:
  {
    "new_title": "...",
    "new_description": "...",   // HTML
    "keywords_short": [...],
    "keywords_mid": [...],
    "keywords_long": [...]
  }

- Update fields as needed but do not add or remove keys.
- Respect the constraints:
  - Title <= 200 characters.
  - Description (HTML) <= 2000 characters.
  - No keyword stuffing.

Return ONLY the final JSON. No explanations.
""".strip()

# ----- Category-Specific L1 Prompts -----

L1_ELECTRONICS = """
You are an expert Electronics SEO strategist. Create optimized product titles and descriptions following these rules:

STEP 1: Extract ONLY explicitly provided product data (category, brand, specs, compatibility, features).
STEP 2: Analyze reviews for pain points and positive themes if provided.
STEP 3: Classify into market category:
- HIGH-TECH/PERFORMANCE (20% Short | 35% Mid | 45% Long-tail)
- ACCESSORIES/COMPATIBILITY (25% Short | 50% Mid | 25% Long-tail)
- AUDIO/LIFESTYLE (30% Short | 30% Mid | 40% Long-tail)
- COMMODITY/CONSUMABLE (40% Short | 35% Mid | 25% Long-tail)
- EMERGING/NICHE (15% Short | 30% Mid | 55% Long-tail)

STEP 4-6: Build SEO title (<=180 chars) and 5 benefit-driven bullet points following keyword ratios.

Return ONLY JSON: {"new_title": "...", "new_description": "HTML...", "keywords_short": [...], "keywords_mid": [...], "keywords_long": [...]}
""".strip()

L1_HOME_KITCHEN = """
You are an expert Home & Kitchen SEO strategist. Create conversion-optimized product titles and descriptions.

STEP 1: Extract product type, use-case, material, dimensions, capacity, durability features, maintenance info.
STEP 2-3: Classify into market category:
- STORAGE & ORGANIZATION (25% Short | 45% Mid | 30% Long-tail)
- COOKWARE & BAKEWARE (35% Short | 40% Mid | 25% Long-tail)
- SMALL APPLIANCES (30% Short | 35% Mid | 35% Long-tail)
- DINING & SERVEWARE (40% Short | 35% Mid | 25% Long-tail)
- FURNITURE & LARGE ITEMS (20% Short | 50% Mid | 30% Long-tail)
- KITCHEN TOOLS & GADGETS (45% Short | 35% Mid | 20% Long-tail)
- CLEANING & MAINTENANCE (35% Short | 40% Mid | 25% Long-tail)

Return ONLY JSON: {"new_title": "...", "new_description": "HTML...", "keywords_short": [...], "keywords_mid": [...], "keywords_long": [...]}
""".strip()

L1_BEAUTY = """
You are an expert Beauty & Personal Care SEO strategist. Create compliant, conversion-optimized titles and descriptions.

MEDICAL CLAIMS PROHIBITION: Never use "treats", "cures", "heals". Use "helps reduce appearance of", "supports", "promotes".

Market Categories:
- TREATMENT/ACTIVE SKINCARE (20% Short | 40% Mid | 40% Long-tail)
- DAILY ESSENTIALS (35% Short | 45% Mid | 20% Long-tail)
- HAIR CARE/SCALP (30% Short | 40% Mid | 30% Long-tail)
- COLOR COSMETICS (40% Short | 35% Mid | 25% Long-tail)
- CLEAN/NATURAL/SENSITIVE (25% Short | 35% Mid | 40% Long-tail)
- SPECIALTY/TARGETED (25% Short | 45% Mid | 30% Long-tail)

Return ONLY JSON: {"new_title": "...", "new_description": "HTML...", "keywords_short": [...], "keywords_mid": [...], "keywords_long": [...]}
""".strip()

L1_PET_CARE = """
You are an expert Pet Care & Supplies SEO strategist. Create safety-focused, conversion-optimized titles and descriptions.

SAFETY PRIORITY: Never fabricate safety claims, vet endorsements, or breed suitability not explicitly stated.

Market Categories:
- PET FOOD & TREATS (30% Short | 40% Mid | 30% Long-tail)
- TOYS & ENRICHMENT (35% Short | 35% Mid | 30% Long-tail)
- GROOMING & HYGIENE (35% Short | 40% Mid | 25% Long-tail)
- COLLARS/LEASHES/HARNESSES (30% Short | 45% Mid | 25% Long-tail)
- BEDS/FURNITURE/COMFORT (30% Short | 40% Mid | 30% Long-tail)
- HEALTH & WELLNESS (25% Short | 40% Mid | 35% Long-tail)
- FEEDING & WATERING (35% Short | 40% Mid | 25% Long-tail)
- LITTER & WASTE (40% Short | 35% Mid | 25% Long-tail)
- TRAINING & BEHAVIOR (30% Short | 40% Mid | 30% Long-tail)

Return ONLY JSON: {"new_title": "...", "new_description": "HTML...", "keywords_short": [...], "keywords_mid": [...], "keywords_long": [...]}
""".strip()

L1_AUTOMOTIVE = """
You are an expert Automotive Accessories SEO strategist. Create fitment-focused, conversion-optimized titles and descriptions.

FITMENT PRIORITY: Never fabricate vehicle compatibility, makes, models, years, or trim levels.

Market Categories:
- INTERIOR PROTECTION (25% Short | 50% Mid | 25% Long-tail)
- SEAT ACCESSORIES (30% Short | 40% Mid | 30% Long-tail)
- STEERING WHEEL & PEDAL (35% Short | 40% Mid | 25% Long-tail)
- EXTERIOR PROTECTION (30% Short | 45% Mid | 25% Long-tail)
- TECH & PHONE MOUNTS (35% Short | 40% Mid | 25% Long-tail)
- STORAGE & ORGANIZATION (35% Short | 40% Mid | 25% Long-tail)
- LIGHTING & VISIBILITY (30% Short | 45% Mid | 25% Long-tail)
- PERFORMANCE & MAINTENANCE (35% Short | 45% Mid | 20% Long-tail)
- EXTERIOR STYLING (30% Short | 45% Mid | 25% Long-tail)

Return ONLY JSON: {"new_title": "...", "new_description": "HTML...", "keywords_short": [...], "keywords_mid": [...], "keywords_long": [...]}
""".strip()

L1_BABY_KIDS = """
You are an expert Baby & Kids SEO strategist. Create safety-focused, conversion-optimized titles and descriptions.

SAFETY PRIORITY: Never fabricate safety certifications, age recommendations, or material compositions.

Market Categories:
- INFANT ESSENTIALS 0-12M (20% Short | 45% Mid | 35% Long-tail)
- DEVELOPMENTAL TOYS (25% Short | 40% Mid | 35% Long-tail)
- FEEDING & MEALTIME (30% Short | 45% Mid | 25% Long-tail)
- CLOTHING & FOOTWEAR (35% Short | 40% Mid | 25% Long-tail)
- SLEEP & COMFORT (25% Short | 40% Mid | 35% Long-tail)
- OUTDOOR & ACTIVE PLAY (25% Short | 45% Mid | 30% Long-tail)
- LEARNING & EDUCATIONAL (30% Short | 40% Mid | 30% Long-tail)
- NURSERY & FURNITURE (20% Short | 50% Mid | 30% Long-tail)

Return ONLY JSON: {"new_title": "...", "new_description": "HTML...", "keywords_short": [...], "keywords_mid": [...], "keywords_long": [...]}
""".strip()

L1_BOOKS_OFFICE = """
You are an expert Books & Office Supplies SEO strategist. Create learning-focused, conversion-optimized titles and descriptions.

ACCURACY PRIORITY: Never fabricate edition numbers, publication years, or curriculum alignment.

Market Categories:
- TEXTBOOKS & STUDY GUIDES (25% Short | 45% Mid | 30% Long-tail)
- WORKBOOKS & PRACTICE (30% Short | 40% Mid | 30% Long-tail)
- PLANNERS & ORGANIZERS (35% Short | 40% Mid | 25% Long-tail)
- NOTEBOOKS & JOURNALS (40% Short | 35% Mid | 25% Long-tail)
- PROFESSIONAL/BUSINESS BOOKS (30% Short | 40% Mid | 30% Long-tail)
- CHILDREN'S EDUCATIONAL (30% Short | 45% Mid | 25% Long-tail)
- WRITING INSTRUMENTS (45% Short | 35% Mid | 20% Long-tail)
- DESK ACCESSORIES (40% Short | 40% Mid | 20% Long-tail)
- ART & CREATIVE SUPPLIES (35% Short | 40% Mid | 25% Long-tail)

Return ONLY JSON: {"new_title": "...", "new_description": "HTML...", "keywords_short": [...], "keywords_mid": [...], "keywords_long": [...]}
""".strip()

L1_FASHION = """
You are an expert Fashion SEO strategist. Create conversion-optimized product titles and descriptions.

Market Categories:
- TREND/STATEMENT PIECES (25% Short | 30% Mid | 45% Long-tail)
- WARDROBE BASICS (45% Short | 40% Mid | 15% Long-tail)
- OCCASION/FORMAL WEAR (20% Short | 50% Mid | 30% Long-tail)
- ACTIVEWEAR/FUNCTIONAL (30% Short | 35% Mid | 35% Long-tail)
- SPECIALTY/INCLUSIVE SIZING (20% Short | 45% Mid | 35% Long-tail)
- SUSTAINABLE/ETHICAL (25% Short | 30% Mid | 45% Long-tail)

Return ONLY JSON: {"new_title": "...", "new_description": "HTML...", "keywords_short": [...], "keywords_mid": [...], "keywords_long": [...]}
""".strip()

L1_FOOD_GROCERY = """
You are an expert Food & Grocery SEO strategist. Create regulatory-compliant, conversion-optimized titles and descriptions.

FDA COMPLIANCE: Never make disease prevention/treatment claims. Use "contains", "source of", "made with".

Market Categories:
- SPICES & SEASONINGS (30% Short | 40% Mid | 30% Long-tail)
- COOKING OILS & FATS (35% Short | 40% Mid | 25% Long-tail)
- GRAINS & PULSES (35% Short | 45% Mid | 20% Long-tail)
- SNACKS & TREATS (40% Short | 35% Mid | 25% Long-tail)
- BEVERAGES (35% Short | 40% Mid | 25% Long-tail)
- CONDIMENTS & SAUCES (35% Short | 40% Mid | 25% Long-tail)
- SPECIALTY/ARTISAN FOODS (25% Short | 40% Mid | 35% Long-tail)
- HEALTH/FUNCTIONAL FOODS (30% Short | 35% Mid | 35% Long-tail)
- READY-TO-EAT/CONVENIENCE (40% Short | 40% Mid | 20% Long-tail)

Return ONLY JSON: {"new_title": "...", "new_description": "HTML...", "keywords_short": [...], "keywords_mid": [...], "keywords_long": [...]}
""".strip()

L1_HEALTH_FITNESS = """
You are an expert Health & Fitness SEO strategist. Create compliant, conversion-optimized titles and descriptions.

REGULATORY COMPLIANCE: Never make disease claims. Use "supports", "helps promote", "may contribute to".

Market Categories:
- PROTEIN SUPPLEMENTS (30% Short | 40% Mid | 30% Long-tail)
- PRE-WORKOUT/ENERGY (25% Short | 35% Mid | 40% Long-tail)
- RECOVERY/POST-WORKOUT (30% Short | 40% Mid | 30% Long-tail)
- WEIGHT MANAGEMENT (25% Short | 35% Mid | 40% Long-tail)
- VITAMINS/GENERAL WELLNESS (35% Short | 40% Mid | 25% Long-tail)
- SPECIALTY/ATHLETIC PERFORMANCE (20% Short | 45% Mid | 35% Long-tail)
- PLANT-BASED/CLEAN LABEL (25% Short | 40% Mid | 35% Long-tail)

Return ONLY JSON: {"new_title": "...", "new_description": "HTML...", "keywords_short": [...], "keywords_mid": [...], "keywords_long": [...]}
""".strip()

L2_GENERIC_ENRICH = """
You act as a Level-2 refinement engine for Amazon SEO listings.

Your L2 responsibilities:
1) Enrich the title with essential, context-appropriate keywords missing for clarity and SEO.
2) If original title indicates COMBO/Pack/Set, ensure the optimized title contains that identifier.
3) Maintain accuracy, clarity, readability, and natural language without keyword stuffing.
4) Preserve any links in the original description exactly.

Constraints: Title <= 200 chars, Description HTML <= 2000 chars, No keyword stuffing.

Return ONLY the final JSON: {"new_title": "...", "new_description": "...", "keywords_short": [...], "keywords_mid": [...], "keywords_long": [...]}
""".strip()

# ----- Category List for UI -----
PRODUCT_CATEGORIES = [
    "Books & EdTech",
    "Electronics",
    "Home & Kitchen",
    "Beauty & Personal Care",
    "Pet Care & Supplies",
    "Automotive Accessories",
    "Baby & Kids",
    "Books & Office Supplies",
    "Fashion",
    "Food & Grocery",
    "Health & Fitness",
]

# ----- Prompt Library -----
PROMPT_LIBRARY = [
    {
        "id": "pw_elite_01",
        "label": "PW Amazon SEO – Elite Edition (Books + EdTech)",
        "category": "Books & EdTech",
        "use_case": "Physics Wallah books, exam-prep, academic stationery, and related education products.",
        "level1": f"{SHAKTI_KB}\n\n{L1_PW_ELITE}",
        "level2": f"{SHAKTI_KB}\n\n{L2_PW_ENRICH}",
    },
    {
        "id": "electronics_01",
        "label": "Electronics",
        "category": "Electronics",
        "use_case": "Smartphones, laptops, chargers, cables, earbuds, speakers, smart home devices, and all electronic products.",
        "level1": f"{SHAKTI_KB}\n\n{L1_ELECTRONICS}",
        "level2": f"{SHAKTI_KB}\n\n{L2_GENERIC_ENRICH}",
    },
    {
        "id": "home_kitchen_01",
        "label": "Home & Kitchen",
        "category": "Home & Kitchen",
        "use_case": "Kitchen organizers, cookware, storage solutions, dining sets, kitchen tools, and home furniture.",
        "level1": f"{SHAKTI_KB}\n\n{L1_HOME_KITCHEN}",
        "level2": f"{SHAKTI_KB}\n\n{L2_GENERIC_ENRICH}",
    },
    {
        "id": "beauty_01",
        "label": "Beauty & Personal Care",
        "category": "Beauty & Personal Care",
        "use_case": "Skincare serums, moisturizers, shampoos, makeup, hair care products, and personal care items.",
        "level1": f"{SHAKTI_KB}\n\n{L1_BEAUTY}",
        "level2": f"{SHAKTI_KB}\n\n{L2_GENERIC_ENRICH}",
    },
    {
        "id": "pet_care_01",
        "label": "Pet Care & Supplies",
        "category": "Pet Care & Supplies",
        "use_case": "Pet food, toys, grooming supplies, beds, collars, leashes, and all pet-related products.",
        "level1": f"{SHAKTI_KB}\n\n{L1_PET_CARE}",
        "level2": f"{SHAKTI_KB}\n\n{L2_GENERIC_ENRICH}",
    },
    {
        "id": "automotive_01",
        "label": "Automotive Accessories",
        "category": "Automotive Accessories",
        "use_case": "Floor mats, seat covers, car phone mounts, steering covers, and vehicle accessories.",
        "level1": f"{SHAKTI_KB}\n\n{L1_AUTOMOTIVE}",
        "level2": f"{SHAKTI_KB}\n\n{L2_GENERIC_ENRICH}",
    },
    {
        "id": "baby_kids_01",
        "label": "Baby & Kids",
        "category": "Baby & Kids",
        "use_case": "Baby monitors, toys, clothing, feeding supplies, nursery furniture, and kids' products.",
        "level1": f"{SHAKTI_KB}\n\n{L1_BABY_KIDS}",
        "level2": f"{SHAKTI_KB}\n\n{L2_GENERIC_ENRICH}",
    },
    {
        "id": "books_office_01",
        "label": "Books & Office Supplies",
        "category": "Books & Office Supplies",
        "use_case": "Textbooks, workbooks, notebooks, planners, pens, desk organizers, and office supplies.",
        "level1": f"{SHAKTI_KB}\n\n{L1_BOOKS_OFFICE}",
        "level2": f"{SHAKTI_KB}\n\n{L2_GENERIC_ENRICH}",
    },
    {
        "id": "fashion_01",
        "label": "Fashion",
        "category": "Fashion",
        "use_case": "Dresses, jeans, jackets, activewear, formal wear, and all clothing/apparel products.",
        "level1": f"{SHAKTI_KB}\n\n{L1_FASHION}",
        "level2": f"{SHAKTI_KB}\n\n{L2_GENERIC_ENRICH}",
    },
    {
        "id": "food_grocery_01",
        "label": "Food & Grocery",
        "category": "Food & Grocery",
        "use_case": "Spices, cooking oils, grains, snacks, beverages, condiments, and grocery items.",
        "level1": f"{SHAKTI_KB}\n\n{L1_FOOD_GROCERY}",
        "level2": f"{SHAKTI_KB}\n\n{L2_GENERIC_ENRICH}",
    },
    {
        "id": "health_fitness_01",
        "label": "Health & Fitness",
        "category": "Health & Fitness",
        "use_case": "Protein powders, supplements, vitamins, pre-workout, fitness accessories, and wellness products.",
        "level1": f"{SHAKTI_KB}\n\n{L1_HEALTH_FITNESS}",
        "level2": f"{SHAKTI_KB}\n\n{L2_GENERIC_ENRICH}",
    },
]

DEFAULT_PRESET_ID = PROMPT_LIBRARY[0]["id"]


def get_preset_by_label(label: str):
    for p in PROMPT_LIBRARY:
        if p["label"] == label:
            return p
    return PROMPT_LIBRARY[0]


def get_preset_by_category(category: str):
    """Get preset by category name."""
    for p in PROMPT_LIBRARY:
        if p.get("category") == category:
            return p
    return PROMPT_LIBRARY[0]


# ----------------------- L1+L2 Runner -----------------------
def single_contract():
    """Contract for L1 outputs."""
    return """
Return ONLY a JSON object with this exact structure:
{
  "new_title": "string (<= 200 chars)",
  "new_description": "HTML string (<= 2000 chars, using <b>, <br>, <ul>, <li> if useful)",
  "keywords_short": ["short-tail keyword 1", "..."],
  "keywords_mid": ["mid-tail keyword 1", "..."],
  "keywords_long": ["long-tail keyword 1", "..."]
}
No extra keys. No comments. No explanations.
""".strip()


def run_l1_l2(
    prev_title,
    prev_desc,
    product_link,
    system_prompt_l1,
    system_prompt_l2,
    openai_key,
    openai_model,
    second_engine,
    openai2_key,
    openai2_model,
    gemini_key,
    gemini_model,
    anthropic_key,
    claude_model,
):
    """Run Level-1 (OpenAI) + Level-2 (optional second engine)."""

    # --------- L1 with OpenAI (primary engine) ---------
    u1 = f"""
You are given an existing Amazon/e-commerce listing fragment.

Inputs:
- Previous Title: {prev_title or '(empty)'}
- Previous Description: {prev_desc or '(empty)'}
- Product Link: {product_link or '(none)'}

TASK:
Using the Level-1 system prompt’s framework, produce a fully optimized listing for this product.

{single_contract()}
""".strip()

    if OpenAI is None:
        raise RuntimeError("openai SDK not installed. pip install openai")

    c1 = OpenAI(api_key=openai_key)
    r1 = c1.chat.completions.create(
        model=openai_model,
        temperature=0.15,
        messages=[
            {"role": "system", "content": to_utf8_clean(system_prompt_l1)},
            {"role": "user", "content": to_utf8_clean(u1)},
        ],
    )
    raw1 = to_utf8_clean((r1.choices[0].message.content or "").strip())
    p1 = coerce_json(raw1)
    if not p1:
        raise RuntimeError("L1 returned non-JSON.")
    draft = ensure_listing_shape(p1)

    # If no second engine selected, L2 = L1
    if second_engine == "None":
        return draft, draft

    # --------- L2 (refinement) ---------
    u2 = f"""
Refine the JSON listing below using the Level-2 system prompt rules.

Constraints:
- Preserve JSON structure (new_title, new_description, keywords_short, keywords_mid, keywords_long).
- Title <= 200 characters.
- Description is HTML <= 2000 characters.
- Avoid keyword stuffing; maintain clarity, compliance, and factual accuracy.
- Preserve combo/pack identifiers and all original links.

Context:
Previous Title: {prev_title or '(empty)'}
Previous Description: {prev_desc or '(empty)'}
Product Link: {product_link or '(none)'}

Here is the draft JSON to refine:
{json.dumps(draft, ensure_ascii=False)}
""".strip()

    # --- OpenAI second pass ---
    if second_engine == "OpenAI (second pass)":
        c2 = OpenAI(api_key=openai2_key or openai_key)
        r2 = c2.chat.completions.create(
            model=openai2_model or openai_model,
            temperature=0.15,
            messages=[
                {"role": "system", "content": to_utf8_clean(system_prompt_l2)},
                {"role": "user", "content": to_utf8_clean(u2)},
            ],
        )
        raw2 = to_utf8_clean((r2.choices[0].message.content or "").strip())
        p2 = coerce_json(raw2)
        return draft, ensure_listing_shape(p2) if p2 else draft

    # --- Gemini ---
    if second_engine == "Gemini (Google)":
        if genai is None:
            raise RuntimeError(
                "google-generativeai not installed. pip install google-generativeai"
            )
        genai.configure(api_key=gemini_key)
        model = genai.GenerativeModel(gemini_model)
        prompt = to_utf8_clean(system_prompt_l2) + "\n\n" + to_utf8_clean(u2)
        resp = model.generate_content(prompt)
        text = to_utf8_clean(getattr(resp, "text", "") or "")
        p2 = coerce_json(text)
        return draft, ensure_listing_shape(p2) if p2 else draft

    # --- Claude ---
    if second_engine == "Claude (Anthropic)":
        if anthropic is None:
            raise RuntimeError("anthropic SDK not installed. pip install anthropic")
        aclient = anthropic.Anthropic(api_key=anthropic_key)
        msg = aclient.messages.create(
            model=claude_model,
            max_tokens=2000,
            temperature=0.15,
            system=to_utf8_clean(system_prompt_l2),
            messages=[
                {
                    "role": "user",
                    "content": to_utf8_clean(u2),
                }
            ],
        )
        blocks = getattr(msg, "content", []) or []
        parts = []
        for b in blocks:
            t = getattr(b, "text", None)
            if t:
                parts.append(t)
            elif isinstance(b, dict) and b.get("type") == "text":
                parts.append(b.get("text") or "")
        raw2 = to_utf8_clean("\n".join(parts))
        p2 = coerce_json(raw2)
        return draft, ensure_listing_shape(p2) if p2 else draft

    # Fallback: no recognized engine; return draft as final
    return draft, draft


# ----------------------- Basic Styling -----------------------
def theme_css(theme: str) -> str:
    base_bg = "#0f172a" if theme == "Gradient" else "#0b1120"
    accent = {
        "Blue": "#3b82f6",
        "Red": "#ef4444",
        "Green": "#22c55e",
        "Gradient": "#6366f1",
    }.get(theme, "#6366f1")
    return f"""
    <style>
    body {{
        background: radial-gradient(circle at top, #1e293b, {base_bg});
    }}
    .stApp {{
        background: transparent;
    }}
    .main-block {{
        background: rgba(15,23,42,0.94);
        border-radius: 20px;
        padding: 18px 22px;
        border: 1px solid rgba(148,163,184,0.35);
        box-shadow: 0 18px 60px rgba(15,23,42,0.9);
    }}
    .title {{
        font-size: 1.35rem;
        font-weight: 700;
        color: #e5e7eb;
    }}
    .subtitle {{
        font-size: .9rem;
        color: #9ca3af;
        margin-bottom: .6rem;
    }}
    .badge {{
        display:inline-block;
        padding:4px 10px;
        border-radius:999px;
        border:1px solid rgba(148,163,184,0.6);
        font-size:.75rem;
        color:#e5e7eb;
        margin-right:6px;
        margin-bottom:4px;
        background:rgba(15,23,42,0.8);
    }}
    .badge-accent {{
        border-color:{accent};
        color:{accent};
    }}
    .stTabs [data-baseweb="tab-list"] {{
        gap: .25rem;
    }}
    .stTabs [data-baseweb="tab"] {{
        padding: .4rem .8rem;
        border-radius:999px;
    }}
    .stTextInput>div>div>input,
    textarea {{
        background:#020617 !important;
        color:#e5e7eb !important;
        border-radius:10px !important;
        border:1px solid rgba(148,163,184,0.5) !important;
    }}
    </style>
    """


# ----------------------- App Layout -----------------------
def main():
    # Initialize saved keys in session
    if "saved_keys" not in st.session_state:
        st.session_state["saved_keys"] = load_saved_keys()
    if "engine_cfg" not in st.session_state:
        st.session_state["engine_cfg"] = {}

    st.set_page_config(
        page_title="Shakti 1.3 — PW SEO Optimizer",
        layout="wide",
        page_icon="⚡",
    )

    st.sidebar.header("Shakti 1.3")
    theme = st.sidebar.selectbox(
        "Theme", ["Blue", "Red", "Green", "Gradient"], index=3
    )
    st.markdown(theme_css(theme), unsafe_allow_html=True)

    # Header
    st.markdown(
        """
    <div class="main-block">
      <div class="title">Shakti 1.3 — PW SEO Optimizer</div>
      <div class="subtitle">
        PW in-house SEO optimization engine for Amazon & e-commerce listings.
        Built for Physics Wallah books, edtech products, and more.
      </div>
      <div>
        <span class="badge badge-accent">Shakti OS • Internal Tool</span>
        <span class="badge">SEO Engine: L1 + L2</span>
        <span class="badge">Author: Vishal Tiwari (PW17633)</span>
        <span class="badge">Project Head: Kumar Sanskar</span>
      </div>
    </div>
    """,
        unsafe_allow_html=True,
    )
    st.markdown("")

    tabs = st.tabs(
        ["① Optimize (Single)", "② AI Engines", "③ Batch", "④ GPT-5 Chat"]
    )

    # ======================= ① Optimize (Single) =======================
    with tabs[0]:
        st.subheader("Listing Inputs")

        col_url, col_blank = st.columns([2, 1])
        with col_url:
            product_url = st.text_input(
                "Product Page URL (Amazon / Flipkart / Meesho etc.)",
                value="",
                help="If provided and title/description are empty, Shakti will auto-read this page.",
            )
        with col_blank:
            st.caption(
                "Tip: You can either paste the raw title/description below OR just provide the product URL."
            )

        prev_title = st.text_input(
            "Previous Title (optional; leave blank to rely on URL)",
            "",
        )
        prev_desc = st.text_area(
            "Previous Description (optional; leave blank to rely on URL)",
            height=140,
            value="",
        )
        product_link = st.text_input(
            "Product Link (will default to Product Page URL if empty)",
            "",
        )

        st.markdown("---")
        st.subheader("📦 Product Category")
        st.caption("Select the category that best matches your product for optimized SEO prompts.")
        
        # Category selection with visual badges
        selected_category = st.selectbox(
            "Product Category",
            options=PRODUCT_CATEGORIES,
            index=0,
            help="Choose the category that best describes your product. Each category has specialized SEO strategies."
        )
        
        # Get the preset for the selected category
        preset = get_preset_by_category(selected_category)
        
        # Show category info
        col_info1, col_info2 = st.columns([1, 2])
        with col_info1:
            st.info(f"**Selected:** {preset['label']}")
        with col_info2:
            st.caption(f"*{preset['use_case']}*")

        st.markdown("---")
        st.subheader("Prompt Preset (L1 + L2)")

        with st.expander("Preview L1 prompt (read-only)", expanded=False):
            st.write(preset["level1"])

        with st.expander("Preview L2 prompt (read-only)", expanded=False):
            st.write(preset["level2"])

        use_custom_prompts = st.checkbox(
            "Override preset with custom L1/L2 prompts (advanced)",
            value=False,
        )

        system_prompt_l1_single = preset["level1"]
        system_prompt_l2_single = preset["level2"]

        if use_custom_prompts:
            system_prompt_l1_single = st.text_area(
                "Custom L1 System Prompt",
                height=200,
                value=preset["level1"],
            )
            system_prompt_l2_single = st.text_area(
                "Custom L2 System Prompt",
                height=200,
                value=preset["level2"],
            )

        st.markdown("---")
        st.subheader("Run & Result (Single)")

        if st.button("🚀 Run L1 + L2 Optimization", use_container_width=True):
            # 1) Figure out actual inputs (URL vs manual)
            used_prev_title = prev_title
            used_prev_desc = prev_desc

            # Try to auto-fetch from URL only if something is missing
            if product_url and (not used_prev_title or not used_prev_desc):
                t, d = fetch_listing_from_url(product_url)
                # Only overwrite if we actually got something
                if t:
                    used_prev_title = used_prev_title or t
                if d:
                    used_prev_desc = used_prev_desc or d

            # If no explicit product_link, fall back to the URL
            final_product_link = product_link or product_url

            # 2) Read engine configuration from tab ②
            cfg = st.session_state.get("engine_cfg", {})
            openai_key = cfg.get("openai_key") or st.session_state["saved_keys"].get(
                "openai"
            )
            openai_model = cfg.get("openai_model") or list(OPENAI_MODELS.values())[0]
            second_engine = cfg.get("second_engine", "OpenAI (second pass)")
            openai2_key = cfg.get("openai2_key") or openai_key
            openai2_model = cfg.get("openai2_model") or openai_model
            gemini_key = cfg.get("gemini_key") or st.session_state["saved_keys"].get(
                "gemini"
            )
            gemini_model = cfg.get("gemini_model") or list(GEMINI_MODELS.values())[0]
            anthropic_key = cfg.get("anthropic_key") or st.session_state["saved_keys"].get(
                "anthropic"
            )
            claude_model = cfg.get("claude_model") or list(CLAUDE_MODELS.values())[0]

            # Validations
            if not openai_key:
                st.error("OpenAI API key required (configure in tab ②).")
                st.stop()
            if second_engine == "Gemini (Google)" and not gemini_key:
                st.error("Gemini API key required (tab ②).")
                st.stop()
            if second_engine == "Claude (Anthropic)" and not anthropic_key:
                st.error("Anthropic API key required (tab ②).")
                st.stop()

            # IMPORTANT FIX: accept URL as valid input even if extraction failed
            if not (used_prev_title or used_prev_desc or product_url):
                st.error(
                    "Please provide at least a Product Page URL or a previous title/description."
                )
                st.stop()

            try:
                draft_res, final_res = run_l1_l2(
                    used_prev_title,
                    used_prev_desc,
                    final_product_link,
                    system_prompt_l1_single,
                    system_prompt_l2_single,
                    openai_key,
                    openai_model,
                    second_engine,
                    openai2_key,
                    openai2_model,
                    gemini_key,
                    gemini_model,
                    anthropic_key,
                    claude_model,
                )
            except Exception as e:
                st.error(f"Error while running optimization: {e}")
                st.stop()

            st.success("Done ✅")

            st.markdown("**Extracted / Used Source Inputs**")
            st.write(f"**Used Title:** {used_prev_title or '—'}")
            st.write(
                f"**Used Description (first 400 chars):** "
                f"{(used_prev_desc[:400] + '...') if used_prev_desc else '—'}"
            )
            st.write(f"**Product Link Used:** {final_product_link or '—'}")

            st.markdown("---")
            st.markdown("### Final Output (L2)")

            st.markdown("**New Title**")
            st.write(final_res["new_title"] or "—")

            st.markdown("**New Description (HTML)**")
            st.code(final_res["new_description"] or "—", language="html")

            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown("**Short-tail Keywords**")
                st.write(
                    "\n".join("• " + k for k in final_res["keywords_short"]) or "—"
                )
            with c2:
                st.markdown("**Mid-tail Keywords**")
                st.write(
                    "\n".join("• " + k for k in final_res["keywords_mid"]) or "—"
                )
            with c3:
                st.markdown("**Long-tail Keywords**")
                st.write(
                    "\n".join("• " + k for k in final_res["keywords_long"]) or "—"
                )

            # Table + downloads
            df_single = pd.DataFrame(
                [
                    {
                        "Stage": "L1 Draft",
                        "New Title": draft_res["new_title"],
                        "New Description (HTML)": draft_res["new_description"],
                        "Short-tail": ", ".join(draft_res["keywords_short"]),
                        "Mid-tail": ", ".join(draft_res["keywords_mid"]),
                        "Long-tail": ", ".join(draft_res["keywords_long"]),
                    },
                    {
                        "Stage": "L2 Final",
                        "New Title": final_res["new_title"],
                        "New Description (HTML)": final_res["new_description"],
                        "Short-tail": ", ".join(final_res["keywords_short"]),
                        "Mid-tail": ", ".join(final_res["keywords_mid"]),
                        "Long-tail": ", ".join(final_res["keywords_long"]),
                    },
                ]
            )
            st.markdown("#### Table View")
            st.dataframe(df_single, use_container_width=True, height=420)

            csv_bytes = df_single.to_csv(index=False).encode("utf-8")
            st.download_button(
                "⬇️ Download Table (CSV)",
                data=csv_bytes,
                file_name=f"shakti_single_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
            )

    # ======================= ② AI Engines (Keys + Models) =======================
    with tabs[1]:
        st.subheader("Primary Engine — OpenAI (required)")

        saved = st.session_state["saved_keys"]

        openai_key = st.text_input(
            "OpenAI API Key",
            type="password",
            value=saved.get("openai", "") or OPENAI_API_KEY_INLINE,
        )
        openai_choice = st.selectbox(
            "OpenAI Model",
            list(OPENAI_MODELS.keys()),
            index=0,
        )
        openai_model = OPENAI_MODELS[openai_choice]

        st.markdown("---")
        st.subheader("Secondary Engine (optional L2 pass)")

        second_engine = st.selectbox(
            "Engine",
            ["OpenAI (second pass)", "Gemini (Google)", "Claude (Anthropic)", "None"],
            index=0,
        )

        # Defaults
        openai2_key = openai_key
        openai2_model = openai_model
        gemini_key = saved.get("gemini", "") or GEMINI_API_KEY_INLINE
        gemini_model = list(GEMINI_MODELS.values())[0]
        anthropic_key = saved.get("anthropic", "") or ANTHROPIC_API_KEY_INLINE
        claude_model = list(CLAUDE_MODELS.values())[0]

        if second_engine == "OpenAI (second pass)":
            st.caption("L2 will use OpenAI again with possibly a different model/key.")
            ok2_mode = st.radio(
                "OpenAI-2 key",
                ["Reuse primary key", "Use another key"],
                horizontal=True,
            )
            if ok2_mode == "Use another key":
                openai2_key = st.text_input(
                    "OpenAI API Key (second pass)", type="password"
                )
            openai2_choice = st.selectbox(
                "OpenAI Model (second pass)",
                list(OPENAI_MODELS.keys()),
                index=0,
            )
            openai2_model = OPENAI_MODELS[openai2_choice]

        elif second_engine == "Gemini (Google)":
            gemini_key = st.text_input(
                "Gemini API Key", type="password", value=gemini_key
            )
            gem_choice = st.selectbox(
                "Gemini Model",
                list(GEMINI_MODELS.keys()),
                index=0,
            )
            gemini_model = GEMINI_MODELS[gem_choice]

        elif second_engine == "Claude (Anthropic)":
            anthropic_key = st.text_input(
                "Anthropic API Key", type="password", value=anthropic_key
            )
            cl_choice = st.selectbox(
                "Claude Model",
                list(CLAUDE_MODELS.keys()),
                index=0,
            )
            claude_model = CLAUDE_MODELS[cl_choice]

        # Save engine config into session
        if st.button("💾 Save Engine Configuration", use_container_width=True):
            st.session_state["engine_cfg"] = {
                "openai_key": openai_key,
                "openai_model": openai_model,
                "second_engine": second_engine,
                "openai2_key": openai2_key,
                "openai2_model": openai2_model,
                "gemini_key": gemini_key,
                "gemini_model": gemini_model,
                "anthropic_key": anthropic_key,
                "claude_model": claude_model,
            }
            st.success("Engine configuration saved for other tabs.")

        st.markdown("---")
        st.subheader("Persist Keys on This Machine")

        if st.button("🔐 Save API Keys to .shakti_keys.json", use_container_width=True):
            ok, err = save_keys(openai_key, gemini_key, anthropic_key)
            if ok:
                st.session_state["saved_keys"] = load_saved_keys()
                st.success("Keys saved locally. They will auto-load on restart.")
            else:
                st.error(f"Failed to save keys: {err}")

        st.caption(
            "Note: Keys are stored in plain text in .shakti_keys.json in this folder. "
            "Use only on your secure local machine."
        )

    # ======================= ③ Batch (Sequential, ≤10) =======================
    with tabs[2]:
        st.subheader("Batch (sequential, up to 10 rows)")
        st.caption(
            "Upload a CSV with columns: Previous Title, Previous Description, Product Link (optional). "
            "Each row will run through L1 + L2 using the same prompt preset and engines as configured."
        )

        st.markdown("---")
        st.subheader("📦 Product Category for Batch")
        st.caption("Select the category for all products in this batch.")
        
        # Category selection for batch
        batch_selected_category = st.selectbox(
            "Batch Product Category",
            options=PRODUCT_CATEGORIES,
            index=0,
            key="batch_category",
            help="All products in this batch will use this category's SEO strategy."
        )
        
        # Get the preset for the selected category
        batch_preset = get_preset_by_category(batch_selected_category)
        
        # Show category info
        st.info(f"**Using:** {batch_preset['label']} - *{batch_preset['use_case']}*")
        
        st.markdown("---")
        
        batch_file = st.file_uploader("Upload CSV", type=["csv"])

        use_custom_batch_prompts = st.checkbox(
            "Override this preset with custom L1/L2 prompts for batch (advanced)",
            value=False,
        )

        batch_l1 = batch_preset["level1"]
        batch_l2 = batch_preset["level2"]

        if use_custom_batch_prompts:
            batch_l1 = st.text_area(
                "Batch L1 System Prompt",
                height=180,
                value=batch_preset["level1"],
            )
            batch_l2 = st.text_area(
                "Batch L2 System Prompt",
                height=180,
                value=batch_preset["level2"],
            )

        if batch_file is not None:
            try:
                df_in = pd.read_csv(batch_file)
            except Exception as e:
                st.error(f"Could not read CSV: {e}")
                df_in = None

            if df_in is not None:
                st.write("Preview of uploaded data:")
                st.dataframe(df_in.head(), use_container_width=True)

                if len(df_in) > 10:
                    st.warning(
                        f"Batch is limited to 10 rows; your file has {len(df_in)}. Only first 10 will be processed."
                    )
                    df_in = df_in.head(10)

                if st.button("🚀 Run Batch Optimization (L1 + L2)", use_container_width=True):
                    cfg = st.session_state.get("engine_cfg", {})
                    openai_key = cfg.get("openai_key") or st.session_state[
                        "saved_keys"
                    ].get("openai")
                    openai_model = cfg.get("openai_model") or list(
                        OPENAI_MODELS.values()
                    )[0]
                    second_engine = cfg.get("second_engine", "OpenAI (second pass)")
                    openai2_key = cfg.get("openai2_key") or openai_key
                    openai2_model = cfg.get("openai2_model") or openai_model
                    gemini_key = cfg.get("gemini_key") or st.session_state[
                        "saved_keys"
                    ].get("gemini")
                    gemini_model = cfg.get("gemini_model") or list(
                        GEMINI_MODELS.values()
                    )[0]
                    anthropic_key = cfg.get("anthropic_key") or st.session_state[
                        "saved_keys"
                    ].get("anthropic")
                    claude_model = cfg.get("claude_model") or list(
                        CLAUDE_MODELS.values()
                    )[0]

                    if not openai_key:
                        st.error("OpenAI API key required (tab ②).")
                        st.stop()
                    if second_engine == "Gemini (Google)" and not gemini_key:
                        st.error("Gemini API key required (tab ②).")
                        st.stop()
                    if second_engine == "Claude (Anthropic)" and not anthropic_key:
                        st.error("Anthropic API key required (tab ②).")
                        st.stop()

                    out_rows = []
                    progress = st.progress(0.0)
                    for idx, row in df_in.iterrows():
                        prev_title_row = str(row.get("Previous Title", "") or "")
                        prev_desc_row = str(row.get("Previous Description", "") or "")
                        link = str(row.get("Product Link", "") or "")

                        try:
                            draft_res, final_res = run_l1_l2(
                                prev_title_row,
                                prev_desc_row,
                                link,
                                batch_l1,
                                batch_l2,
                                openai_key,
                                openai_model,
                                second_engine,
                                openai2_key,
                                openai2_model,
                                gemini_key,
                                gemini_model,
                                anthropic_key,
                                claude_model,
                            )
                        except Exception as e:
                            final_res = {
                                "new_title": f"[ERROR] {e}",
                                "new_description": "",
                                "keywords_short": [],
                                "keywords_mid": [],
                                "keywords_long": [],
                            }

                        out_rows.append(
                            {
                                "Row": idx + 1,
                                "Previous Title": prev_title_row,
                                "Previous Description": prev_desc_row,
                                "Product Link": link,
                                "New Title": final_res["new_title"],
                                "New Description (HTML)": final_res[
                                    "new_description"
                                ],
                                "Short-tail": ", ".join(final_res["keywords_short"]),
                                "Mid-tail": ", ".join(final_res["keywords_mid"]),
                                "Long-tail": ", ".join(final_res["keywords_long"]),
                            }
                        )
                        progress.progress((idx + 1) / len(df_in))

                    df_out = pd.DataFrame(out_rows)
                    st.success("Batch optimization complete ✅")
                    st.dataframe(df_out, use_container_width=True, height=420)

                    csv_bytes = df_out.to_csv(index=False).encode("utf-8")
                    st.download_button(
                        "⬇️ Download Batch Results (CSV)",
                        data=csv_bytes,
                        file_name=f"shakti_batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                    )

    # ======================= ④ GPT-5 Chat (Knowledge-aware) =======================
    with tabs[3]:
        st.subheader("GPT-5 Chat — Shakti Knowledge Mode")
        st.caption(
            "Free-form chat using the same OpenAI primary engine, grounded in the Shakti KB. "
            "Use this to discuss SEO strategy, ideas, or custom experiments."
        )

        chat_prompt = st.text_area(
            "Ask anything related to Amazon SEO, PW books, keyword strategy, etc.",
            height=180,
        )

        if st.button("💬 Ask Shakti (Chat)", use_container_width=True):
            cfg = st.session_state.get("engine_cfg", {})
            openai_key = cfg.get("openai_key") or st.session_state["saved_keys"].get(
                "openai"
            )
            openai_model = cfg.get("openai_model") or list(OPENAI_MODELS.values())[0]

            if not openai_key:
                st.error("OpenAI API key required (tab ②).")
                st.stop()
            if not chat_prompt.strip():
                st.error("Please type a question or message.")
                st.stop()
            if OpenAI is None:
                st.error("openai SDK not installed. pip install openai")
                st.stop()

            try:
                client = OpenAI(api_key=openai_key)
                resp = client.chat.completions.create(
                    model=openai_model,
                    temperature=0.2,
                    messages=[
                        {"role": "system", "content": SHAKTI_KB},
                        {"role": "user", "content": chat_prompt},
                    ],
                )
                answer = to_utf8_clean(
                    (resp.choices[0].message.content or "").strip()
                )
                st.markdown("**Shakti:**")
                st.write(answer)
            except Exception as e:
                st.error(f"Chat error: {e}")


if __name__ == "__main__":
    main()