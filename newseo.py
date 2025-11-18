# filename: app.py
# Shakti 1.2 — PW SEO Optimizer
# - Single Optimize panel (no duplicates)
# - Batch with its own L1/L2 prompts (entered once)
# - Theme switcher fixed (Blue/Red/Green/Gradient)
# - Strict dropdown model lists (incl. GPT-5), no free text
# - Sequential batch (≤10), HTML-only reports, GPT-5 chat

import io, os, sys, re, json, zipfile, unicodedata
from xml.etree import ElementTree as ET

import streamlit as st
import pandas as pd

# =====================================================
#                SDK IMPORT & WRAPPERS
# =====================================================

OPENAI_CLIENT_MODE = None  # "new" or "old"

try:
    # New OpenAI SDK (>= 1.0.0)
    from openai import OpenAI
    OPENAI_CLIENT_MODE = "new"
except Exception:
    try:
        # Legacy SDK
        import openai
        OpenAI = None
        OPENAI_CLIENT_MODE = "old"
    except Exception:
        OpenAI = None
        openai = None
        OPENAI_CLIENT_MODE = None

try:
    import google.generativeai as genai
except Exception:
    genai = None

try:
    import anthropic
except Exception:
    anthropic = None


def openai_chat_completion(api_key, model, messages, temperature: float = 0.2) -> str:
    """
    Wrapper that works with both:
    - new OpenAI SDK (OpenAI class)
    - old openai.ChatCompletion API

    Returns the response text (str).
    """
    if OPENAI_CLIENT_MODE == "new":
        client = OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model=model,
            temperature=temperature,
            messages=messages,
        )
        return resp.choices[0].message.content or ""
    elif OPENAI_CLIENT_MODE == "old":
        openai.api_key = api_key
        resp = openai.ChatCompletion.create(
            model=model,
            temperature=temperature,
            messages=messages,
        )
        return resp["choices"][0]["message"]["content"] or ""
    else:
        raise RuntimeError(
            "OpenAI SDK not available. Make sure `openai` is in requirements.txt."
        )

# =====================================================
#           APP / UTF-8 / GLOBAL CONSTANTS
# =====================================================

st.set_page_config(page_title="Shakti 1.2 — PW SEO Optimizer", layout="wide")
os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["PYTHONUTF8"] = "1"
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

SMART_MAP = {
    "\u2018": "'",
    "\u2019": "'",
    "\u201c": '"',
    "\u201d": '"',
    "\u2013": "-",
    "\u2014": "-",
    "\u00A0": " ",
}


def to_utf8_clean(s: str) -> str:
    if s is None:
        return ""
    s = unicodedata.normalize("NFC", str(s))
    for k, v in SMART_MAP.items():
        s = s.replace(k, v)
    return s.encode("utf-8", "ignore").decode("utf-8")


# ---------------- Model lists (dropdown only) ----------------
OPENAI_MODELS = {
    "GPT-4.1 Mini (fast/cost-effective)": "gpt-4.1-mini",
    "GPT-4.1": "gpt-4.1",
    "GPT-4o": "gpt-4o",
    "GPT-5 (if enabled)": "gpt-5",
}
GEMINI_MODELS = {
    "Gemini 1.5 Pro": "gemini-1.5-pro",
    "Gemini 1.5 Flash": "gemini-1.5-flash",
}
CLAUDE_MODELS = {
    "Claude 3.5 Sonnet (2024-10-22)": "claude-3.5-sonnet-20241022",
    "Claude 3.5 Haiku (2024-10-22)": "claude-3.5-haiku-20241022",
    "Claude 3 Opus (2024-02-29)": "claude-3-opus-20240229",
}

# ------------- Optional inline keys (or enter in UI) -------------
OPENAI_API_KEY_INLINE = ""
GEMINI_API_KEY_INLINE = ""
ANTHROPIC_API_KEY_INLINE = ""

# =====================================================
#                    HELPERS
# =====================================================

def extract_text_from_docx(file_bytes: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
            xml = z.read("word/document.xml")
        root = ET.fromstring(xml)
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        texts = [t.text or "" for t in root.iterfind(".//w:t", ns)]
        return " ".join("".join(texts).split()).strip()
    except Exception as e:
        return f"[DOCX READ ERROR] {e}"


def coerce_json(s: str):
    try:
        return json.loads(s)
    except Exception:
        pass
    try:
        m = re.search(r"\{.*\}", s, flags=re.DOTALL)
        if m:
            return json.loads(m.group(0))
    except Exception:
        pass
    return None


def ensure_listing_shape(obj: dict):
    return {
        "new_title": (obj.get("new_title") or "").strip(),
        "new_description": (obj.get("new_description") or "").strip(),
        "keywords_short": obj.get("keywords_short")
        or obj.get("short_tail_keywords")
        or [],
        "keywords_mid": obj.get("keywords_mid")
        or obj.get("mid_tail_keywords")
        or [],
        "keywords_long": obj.get("keywords_long")
        or obj.get("long_tail_keywords")
        or [],
    }


def html_report_bytes(title_text: str, inputs: dict, draft: dict, final_: dict):
    style = """
    <style>
      body { font-family: Arial, sans-serif; line-height: 1.45; padding: 24px; color: #1f2937; }
      .title { font-size: 24px; font-weight: 800; color: var(--c1,#4f46e5); margin: 0 0 4px; }
      .sub { color:#6b7280; margin: 0 0 16px; }
      .card { border: 1px solid #e5e7eb; border-radius: 12px; padding: 16px; margin: 16px 0; }
      h3 { margin: 16px 0 8px; color:#111827; }
      table { border-collapse: collapse; width: 100%; }
      td, th { border: 1px solid #e5e7eb; padding: 8px; vertical-align: top; text-align: left; }
      .mono { white-space: pre-wrap; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; background:#f9fafb; padding:8px; border-radius:8px;}
      .badge { display:inline-block; padding:4px 10px; border-radius:999px; background:#eef2ff; border:1px solid #c7d2fe; color:#3730a3; font-weight:600; margin-right:6px;}
    </style>
    """

    def kv(label, value):
        return f"<tr><td><b>{label}</b></td><td>{value}</td></tr>"

    def jo(lst):
        return ", ".join(lst or [])

    html = f"""<!doctype html><html><head><meta charset="utf-8"><title>{title_text}</title>{style}</head>
<body>
  <div class="title">{title_text}</div>
  <div class="sub">PW in-house SEO optimization app made by Vishal Tiwari (pw17633), Project Head: Kumar Sanskar</div>
  <div class="card">
    <span class="badge">Shakti 1.2</span>
    <span class="badge">PW In-house</span>
    <span class="badge">Author: Vishal Tiwari</span>
    <span class="badge">Project Head: Kumar Sanskar</span>
  </div>

  <div class="card">
    <h3>Inputs</h3>
    <table>
      {kv("Previous Title", inputs.get('prev_title') or '—')}
      {kv("Previous Description", f"<div class='mono'>{(inputs.get('prev_desc') or '—')}</div>")}
      {kv("Product Link", inputs.get('product_link') or '—')}
    </table>
  </div>

  <div class="card">
    <h3>Draft (L1 — OpenAI)</h3>
    <table>
      {kv("Title", draft.get('new_title') or '—')}
      {kv("Description (HTML)", f"<div class='mono'>{(draft.get('new_description') or '—').replace('<','&lt;').replace('>','&gt;')}</div>")}
      {kv("Short-tail", jo(draft.get('keywords_short')) or '—')}
      {kv("Mid-tail", jo(draft.get('keywords_mid')) or '—')}
      {kv("Long-tail", jo(draft.get('keywords_long')) or '—')}
    </table>
  </div>

  <div class="card">
    <h3>Final (L2 — Refined)</h3>
    <table>
      {kv("Title", final_.get('new_title') or '—')}
      {kv("Description (HTML)", f"<div class='mono'>{(final_.get('new_description') or '—').replace('<','&lt;').replace('>','&gt;')}</div>")}
      {kv("Short-tail", jo(final_.get('keywords_short')) or '—')}
      {kv("Mid-tail", jo(final_.get('keywords_mid')) or '—')}
      {kv("Long-tail", jo(final_.get('keywords_long')) or '—')}
    </table>
  </div>
</body></html>"""
    return html.encode("utf-8"), "text/html", "shakti_report.html"


def theme_css(theme: str) -> str:
    # Make all themes effective (buttons + highlights)
    if theme == "Red":
        return """
        :root { --c1: #dc2626; }
        .stButton > button { background:#dc2626 !important; color:#fff !important; border:0 !important; }
        .stDownloadButton > button { background:#dc2626 !important; color:#fff !important; border:0 !important; }
        """
    if theme == "Green":
        return """
        :root { --c1: #16a34a; }
        .stButton > button { background:#16a34a !important; color:#fff !important; border:0 !important; }
        .stDownloadButton > button { background:#16a34a !important; color:#fff !important; border:0 !important; }
        """
    if theme == "Gradient":
        return """
        :root { --c1: #111827; }
        .stApp header { background: linear-gradient(135deg,#6366f1,#22c55e); }
        .stButton > button, .stDownloadButton > button { background:#111827 !important; color:#fff !important; border:0 !important; }
        """
    # Default Blue
    return """
    :root { --c1: #4f46e5; }
    .stButton > button { background:#4f46e5 !important; color:#fff !important; border:0 !important; }
    .stDownloadButton > button { background:#4f46e5 !important; color:#fff !important; border:0 !important; }
    """

# =====================================================
#                   HEADER / LAYOUT
# =====================================================

st.sidebar.header("Shakti 1.2")
theme = st.sidebar.selectbox("Theme", ["Blue", "Red", "Green", "Gradient"], index=0)
st.markdown(f"<style>{theme_css(theme)}</style>", unsafe_allow_html=True)

st.markdown(
    """
## Shakti 1.2 — PW SEO Optimizer
<div style='color:#6b7280'>PW in-house SEO optimization app made by <b>Vishal Tiwari (pw17633)</b>, Project Head: <b>Kumar Sanskar</b></div>
<div style='display:flex;gap:.5rem;flex-wrap:wrap;margin:.6rem 0 1rem;'>
  <span style='background:#eef2ff;border:1px solid #c7d2fe;color:#3730a3;padding:.35rem .65rem;border-radius:999px;font-weight:600;font-size:.85rem;'>Shakti 1.2</span>
  <span style='background:#eef2ff;border:1px solid #c7d2fe;color:#3730a3;padding:.35rem .65rem;border-radius:999px;font-weight:600;font-size:.85rem;'>PW In-house</span>
  <span style='background:#eef2ff;border:1px solid #c7d2fe;color:#3730a3;padding:.35rem .65rem;border-radius:999px;font-weight:600;font-size:.85rem;'>Author: Vishal Tiwari</span>
  <span style='background:#eef2ff;border:1px solid #c7d2fe;color:#3730a3;padding:.35rem .65rem;border-radius:999px;font-weight:600;font-size:.85rem;'>Project Head: Kumar Sanskar</span>
</div>
""",
    unsafe_allow_html=True,
)

tabs = st.tabs(["① Optimize (Single)", "② AI Engines", "③ Batch", "④ GPT-5 Chat"])

# =====================================================
#           TAB ① — SINGLE OPTIMIZE
# =====================================================

with tabs[0]:
    st.subheader("Listing Inputs")
    prev_title = st.text_input("Previous Title", "")
    prev_desc = st.text_area("Previous Description", height=160, value="")
    product_link = st.text_input("Amazon Product Link (optional)", "")

    st.markdown("---")
    st.subheader("System Prompts (Single)")

    # L1 prompt (paste or DOCX)
    st.caption("Level 1 (OpenAI)")
    use_docx_l1 = st.toggle("Load L1 from .docx", key="docx_l1_single")
    system_prompt_l1_single = ""
    if use_docx_l1:
        docx_file_l1 = st.file_uploader(
            "Upload L1 prompt (.docx)", type=["docx"], key="docx_file_l1_single"
        )
        if docx_file_l1:
            system_prompt_l1_single = extract_text_from_docx(docx_file_l1.read())
            if system_prompt_l1_single.startswith("[DOCX READ ERROR]"):
                st.warning(system_prompt_l1_single)
            else:
                with st.expander("Preview L1 prompt"):
                    st.write(system_prompt_l1_single)
    else:
        system_prompt_l1_single = st.text_area(
            "Paste L1 system prompt", height=180, key="l1_prompt_text_single"
        )

    # L2 prompt (paste or DOCX)
    st.caption("Level 2 (Refinement Engine)")
    use_docx_l2 = st.toggle("Load L2 from .docx", key="docx_l2_single")
    system_prompt_l2_single = ""
    if use_docx_l2:
        docx_file_l2 = st.file_uploader(
            "Upload L2 prompt (.docx)", type=["docx"], key="docx_file_l2_single"
        )
        if docx_file_l2:
            system_prompt_l2_single = extract_text_from_docx(docx_file_l2.read())
            if system_prompt_l2_single.startswith("[DOCX READ ERROR]"):
                st.warning(system_prompt_l2_single)
            else:
                with st.expander("Preview L2 prompt"):
                    st.write(system_prompt_l2_single)
    else:
        system_prompt_l2_single = st.text_area(
            "Paste L2 system prompt", height=160, key="l2_prompt_text_single"
        )

    st.markdown("---")
    st.subheader("Run & Result (Single)")

    def single_contract():
        return """
Return ONLY a JSON object with keys:
- new_title (string, <=200 chars)
- new_description (string, HTML, <=2000 chars)
- keywords_short (array of strings)
- keywords_mid (array of strings)
- keywords_long (array of strings)
No extra text or markdown.
"""

    def run_l1_l2_single(
        prev_title,
        prev_desc,
        product_link,
        sp_l1,
        sp_l2,
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
        # ---------- L1 ----------
        u1 = f"""
You are given an existing Amazon listing fragment.

Inputs:
- Previous Title: {prev_title or '(empty)'}
- Previous Description: {prev_desc or '(empty)'}
- Product Link: {product_link or '(none)'}

TASK: Using the Level-1 system prompt’s framework, produce an improved listing.
{single_contract()}
""".strip()

        raw1 = to_utf8_clean(
            openai_chat_completion(
                api_key=openai_key,
                model=openai_model,
                temperature=0.2,
                messages=[
                    {"role": "system", "content": to_utf8_clean(sp_l1)},
                    {"role": "user", "content": to_utf8_clean(u1)},
                ],
            ).strip()
        )
        p1 = coerce_json(raw1)
        if not p1:
            raise RuntimeError("L1 returned non-JSON.")
        draft = ensure_listing_shape(p1)

        if second_engine == "None":
            return draft, draft

        # ---------- L2 ----------
        u2 = f"""
Refine a JSON listing produced by another model using the Level-2 system prompt rules.
- Keep the exact JSON structure (new_title, new_description, keywords_short, keywords_mid, keywords_long).
- Title <= 200 chars; Description is HTML <= 2000 chars; avoid keyword stuffing; ensure clarity & compliance.
Return ONLY the JSON.

Context:
Previous Title: {prev_title or '(empty)'}
Previous Description: {prev_desc or '(empty)'}
Product Link: {product_link or '(none)'}
""".strip()

        if second_engine == "OpenAI (second pass)":
            raw2 = to_utf8_clean(
                openai_chat_completion(
                    api_key=openai2_key or openai_key,
                    model=openai2_model or openai_model,
                    temperature=0.2,
                    messages=[
                        {"role": "system", "content": to_utf8_clean(sp_l2)},
                        {
                            "role": "user",
                            "content": to_utf8_clean(u2)
                            + "\n\nDraft JSON:\n"
                            + json.dumps(draft, ensure_ascii=False),
                        },
                    ],
                ).strip()
            )
            p2 = coerce_json(raw2)
            return draft, ensure_listing_shape(p2) if p2 else draft

        if second_engine == "Gemini (Google)":
            if genai is None:
                raise RuntimeError(
                    "google-generativeai not installed. pip install google-generativeai"
                )
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel(gemini_model)
            prompt = (
                to_utf8_clean(sp_l2)
                + "\n\n"
                + to_utf8_clean(u2)
                + "\n\nDraft JSON:\n"
                + json.dumps(draft, ensure_ascii=False)
            )
            resp = model.generate_content(prompt)
            text = to_utf8_clean((resp.text or "").strip())
            p2 = coerce_json(text)
            return draft, ensure_listing_shape(p2) if p2 else draft

        if second_engine == "Claude (Anthropic)":
            if anthropic is None:
                raise RuntimeError("anthropic SDK not installed. pip install anthropic")
            aclient = anthropic.Anthropic(api_key=anthropic_key)
            msg = aclient.messages.create(
                model=claude_model,
                max_tokens=2000,
                temperature=0.2,
                system=to_utf8_clean(sp_l2),
                messages=[
                    {
                        "role": "user",
                        "content": to_utf8_clean(u2)
                        + "\n\nDraft JSON:\n"
                        + json.dumps(draft, ensure_ascii=False),
                    }
                ],
            )
            blocks = getattr(msg, "content", []) or []
            parts = []
            for b in blocks:
                if getattr(b, "type", None) == "text":
                    parts.append(getattr(b, "text", "") or "")
            text = to_utf8_clean("".join(parts))
            p2 = coerce_json(text)
            return draft, ensure_listing_shape(p2) if p2 else draft

        return draft, draft

    # Run (single)
    if st.button("Run L1 → L2 (Single) 🚀", type="primary"):
        cfg = st.session_state.get("engine_cfg", {})
        openai_key = cfg.get("openai_key")
        openai_model = cfg.get("openai_model")
        second_engine = cfg.get("second_engine", "OpenAI (second pass)")
        openai2_key = cfg.get("openai2_key")
        openai2_model = cfg.get("openai2_model")
        gemini_key = cfg.get("gemini_key")
        gemini_model = cfg.get("gemini_model")
        anthropic_key = cfg.get("anthropic_key")
        claude_model = cfg.get("claude_model")

        # validations
        if not openai_key:
            st.error("OpenAI API key required (tab ②).")
            st.stop()
        if not (system_prompt_l1_single or "").strip():
            st.error("Provide Level-1 prompt.")
            st.stop()
        if second_engine != "None" and not (system_prompt_l2_single or "").strip():
            st.error("Provide Level-2 prompt.")
            st.stop()
        if second_engine == "Gemini (Google)" and not gemini_key:
            st.error("Gemini API key required.")
            st.stop()
        if second_engine == "Claude (Anthropic)" and not anthropic_key:
            st.error("Anthropic API key required.")
            st.stop()

        try:
            draft_result, final_result = run_l1_l2_single(
                prev_title,
                prev_desc,
                product_link,
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

            st.success("Done.")
            st.markdown("**New Title**")
            st.write(final_result["new_title"] or "—")
            st.markdown("**New Description (HTML)**")
            st.code(final_result["new_description"] or "—", language="html")

            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown("**Short-tail**")
                st.write(
                    "\n".join("• " + k for k in final_result["keywords_short"]) or "—"
                )
            with c2:
                st.markdown("**Mid-tail**")
                st.write(
                    "\n".join("• " + k for k in final_result["keywords_mid"]) or "—"
                )
            with c3:
                st.markdown("**Long-tail**")
                st.write(
                    "\n".join("• " + k for k in final_result["keywords_long"]) or "—"
                )

            df_single = pd.DataFrame(
                [
                    {
                        "Stage": "L1 Draft",
                        "New Title": draft_result["new_title"],
                        "New Description (HTML)": draft_result["new_description"],
                        "Short-tail": ", ".join(draft_result["keywords_short"]),
                        "Mid-tail": ", ".join(draft_result["keywords_mid"]),
                        "Long-tail": ", ".join(draft_result["keywords_long"]),
                    },
                    {
                        "Stage": "L2 Final",
                        "New Title": final_result["new_title"],
                        "New Description (HTML)": final_result["new_description"],
                        "Short-tail": ", ".join(final_result["keywords_short"]),
                        "Mid-tail": ", ".join(final_result["keywords_mid"]),
                        "Long-tail": ", ".join(final_result["keywords_long"]),
                    },
                ]
            )
            st.markdown("#### Table View")
            st.dataframe(df_single, use_container_width=True, height=560)
            st.download_button(
                "⬇️ Download Table (CSV)",
                data=df_single.to_csv(index=False).encode("utf-8"),
                file_name="shakti_single_table.csv",
                mime="text/csv",
            )

            data_bytes, mime, fname = html_report_bytes(
                title_text="Shakti 1.2 — Single Report",
                inputs={
                    "prev_title": prev_title,
                    "prev_desc": prev_desc,
                    "product_link": product_link,
                },
                draft=draft_result,
                final_=final_result,
            )
            st.download_button(
                "⬇️ Download Report (HTML)",
                data=data_bytes,
                file_name=fname,
                mime=mime,
            )
        except Exception as e:
            st.error(f"Run failed: {e}")

# =====================================================
#           TAB ② — ENGINE CONFIG
# =====================================================

with tabs[1]:
    st.subheader("Primary Engine — OpenAI (required)")
    openai_key_mode = st.radio(
        "OpenAI Key Source", ["Inline", "Enter now"], horizontal=True, key="okm"
    )
    openai_key = (
        (OPENAI_API_KEY_INLINE or "").strip()
        if openai_key_mode == "Inline"
        else st.text_input("OpenAI API Key", type="password", key="okey")
    )
    openai_choice = st.selectbox(
        "OpenAI Model", list(OPENAI_MODELS.keys()), index=0
    )
    openai_model = OPENAI_MODELS[openai_choice]

    st.markdown("---")
    st.subheader("Secondary Engine — choose one")
    second_engine = st.selectbox(
        "Engine",
        ["None", "OpenAI (second pass)", "Gemini (Google)", "Claude (Anthropic)"],
        index=1,
    )

    # OpenAI second pass
    openai2_key = openai_key
    openai2_model = openai_model
    if second_engine == "OpenAI (second pass)":
        ok2_mode = st.radio(
            "OpenAI-2 Key Source",
            ["Reuse primary key", "Enter another key"],
            horizontal=True,
            key="ok2m",
        )
        if ok2_mode == "Enter another key":
            openai2_key = st.text_input(
                "OpenAI API Key (second pass)", type="password", key="okey2"
            )
        openai2_choice = st.selectbox(
            "OpenAI Model (second pass)",
            list(OPENAI_MODELS.keys()),
            index=0,
            key="openai2_choice",
        )
        openai2_model = OPENAI_MODELS[openai2_choice]

    # Gemini
    gemini_key = ""
    gemini_model = ""
    if second_engine == "Gemini (Google)":
        gkm = st.radio(
            "Gemini Key Source",
            ["Inline", "Enter now"],
            horizontal=True,
            key="gkm",
        )
        gemini_key = (
            (GEMINI_API_KEY_INLINE or "").strip()
            if gkm == "Inline"
            else st.text_input("Gemini API Key", type="password", key="gkey")
        )
        gem_choice = st.selectbox(
            "Gemini Model", list(GEMINI_MODELS.keys()), index=0
        )
        gemini_model = GEMINI_MODELS[gem_choice]

    # Claude
    anthropic_key = ""
    claude_model = ""
    if second_engine == "Claude (Anthropic)":
        akm = st.radio(
            "Claude Key Source",
            ["Inline", "Enter now"],
            horizontal=True,
            key="akm",
        )
        anthropic_key = (
            (ANTHROPIC_API_KEY_INLINE or "").strip()
            if akm == "Inline"
            else st.text_input("Anthropic API Key", type="password", key="akey")
        )
        cl_choice = st.selectbox(
            "Claude Model", list(CLAUDE_MODELS.keys()), index=0
        )
        claude_model = CLAUDE_MODELS[cl_choice]

    # Save config to session for other tabs
    st.session_state.engine_cfg = {
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
    st.success("Engine configuration saved.")

# =====================================================
#           TAB ③ — BATCH (≤10 ROWS)
# =====================================================

with tabs[2]:
    st.subheader("Batch (sequential, up to 10 rows)")
    st.caption(
        "Upload a CSV with columns: Previous Title, Previous Description, Product Link (optional). Each row is processed one-by-one for top consistency."
    )

    st.markdown("**Batch System Prompts**")
    batch_l1_prompt = st.text_area(
        "Level 1 (OpenAI) — Batch Prompt", height=160, key="batch_l1_prompt"
    )
    batch_l2_prompt = st.text_area(
        "Level 2 (Refinement Engine) — Batch Prompt (optional if secondary engine is None)",
        height=140,
        key="batch_l2_prompt",
    )

    batch_file = st.file_uploader("Upload CSV", type=["csv"], key="batch_csv")

    def batch_contract():
        return """
Return ONLY a JSON object with keys:
- new_title (string, <=200 chars)
- new_description (string, HTML, <=2000 chars)
- keywords_short (array of strings)
- keywords_mid (array of strings)
- keywords_long (array of strings)
No extra text or markdown.
"""

    def run_l1_l2_batch(
        prev_title,
        prev_desc,
        product_link,
        sp_l1,
        sp_l2,
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
        # ---------- L1 ----------
        u1 = f"""
You are given an existing Amazon listing fragment.

Inputs:
- Previous Title: {prev_title or '(empty)'}
- Previous Description: {prev_desc or '(empty)'}
- Product Link: {product_link or '(none)'}

TASK: Using the Level-1 system prompt’s framework, produce an improved listing.
{batch_contract()}
""".strip()
        raw1 = to_utf8_clean(
            openai_chat_completion(
                api_key=openai_key,
                model=openai_model,
                temperature=0.2,
                messages=[
                    {"role": "system", "content": to_utf8_clean(sp_l1)},
                    {"role": "user", "content": to_utf8_clean(u1)},
                ],
            ).strip()
        )
        p1 = coerce_json(raw1)
        if not p1:
            raise RuntimeError("L1 returned non-JSON.")
        draft = ensure_listing_shape(p1)

        if second_engine == "None":
            return draft, draft

        # ---------- L2 ----------
        u2 = f"""
Refine a JSON listing produced by another model using the Level-2 system prompt rules.
- Keep the exact JSON structure (new_title, new_description, keywords_short, keywords_mid, keywords_long).
- Title <= 200 chars; Description is HTML <= 2000 chars; avoid keyword stuffing; ensure clarity & compliance.
Return ONLY the JSON.

Context:
Previous Title: {prev_title or '(empty)'}
Previous Description: {prev_desc or '(empty)'}
Product Link: {product_link or '(none)'}
""".strip()

        if second_engine == "OpenAI (second pass)":
            raw2 = to_utf8_clean(
                openai_chat_completion(
                    api_key=openai2_key or openai_key,
                    model=openai2_model or openai_model,
                    temperature=0.2,
                    messages=[
                        {"role": "system", "content": to_utf8_clean(sp_l2)},
                        {
                            "role": "user",
                            "content": to_utf8_clean(u2)
                            + "\n\nDraft JSON:\n"
                            + json.dumps(draft, ensure_ascii=False),
                        },
                    ],
                ).strip()
            )
            p2 = coerce_json(raw2)
            return draft, ensure_listing_shape(p2) if p2 else draft

        if second_engine == "Gemini (Google)":
            if genai is None:
                raise RuntimeError(
                    "google-generativeai not installed. pip install google-generativeai"
                )
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel(gemini_model)
            prompt = (
                to_utf8_clean(sp_l2)
                + "\n\n"
                + to_utf8_clean(u2)
                + "\n\nDraft JSON:\n"
                + json.dumps(draft, ensure_ascii=False)
            )
            resp = model.generate_content(prompt)
            text = to_utf8_clean((resp.text or "").strip())
            p2 = coerce_json(text)
            return draft, ensure_listing_shape(p2) if p2 else draft

        if second_engine == "Claude (Anthropic)":
            if anthropic is None:
                raise RuntimeError("anthropic SDK not installed. pip install anthropic")
            aclient = anthropic.Anthropic(api_key=anthropic_key)
            msg = aclient.messages.create(
                model=claude_model,
                max_tokens=2000,
                temperature=0.2,
                system=to_utf8_clean(sp_l2),
                messages=[
                    {
                        "role": "user",
                        "content": to_utf8_clean(u2)
                        + "\n\nDraft JSON:\n"
                        + json.dumps(draft, ensure_ascii=False),
                    }
                ],
            )
            blocks = getattr(msg, "content", []) or []
            parts = []
            for b in blocks:
                if getattr(b, "type", None) == "text":
                    parts.append(getattr(b, "text", "") or "")
            text = to_utf8_clean("".join(parts))
            p2 = coerce_json(text)
            return draft, ensure_listing_shape(p2) if p2 else draft

        return draft, draft

    if batch_file:
        try:
            df_in = pd.read_csv(batch_file)
            cols = {c.lower().strip(): c for c in df_in.columns}

            def pick(*names):
                for n in names:
                    if n in cols:
                        return cols[n]
                return None

            col_t = pick("previous title", "title", "old title")
            col_d = pick("previous description", "description", "old description")
            col_l = pick("product link", "amazon product link", "link", "url")

            if not col_t or not col_d:
                st.error(
                    "CSV must include 'Previous Title' and 'Previous Description' columns."
                )
                st.stop()

            if len(df_in) > 10:
                st.warning("Only first 10 rows will be processed (sequential).")
                df_in = df_in.head(10)

            cfg = st.session_state.get("engine_cfg", {})
            openai_key = cfg.get("openai_key")
            openai_model = cfg.get("openai_model")
            second_engine = cfg.get("second_engine", "OpenAI (second pass)")
            openai2_key = cfg.get("openai2_key")
            openai2_model = cfg.get("openai2_model")
            gemini_key = cfg.get("gemini_key")
            gemini_model = cfg.get("gemini_model")
            anthropic_key = cfg.get("anthropic_key")
            claude_model = cfg.get("claude_model")

            if st.button("Run Batch (Sequential) 🚀", type="primary"):
                if not openai_key:
                    st.error("OpenAI API key required (tab ②).")
                    st.stop()
                if not (batch_l1_prompt or "").strip():
                    st.error("Provide Batch Level-1 prompt above.")
                    st.stop()
                if second_engine != "None" and not (batch_l2_prompt or "").strip():
                    st.error("Provide Batch Level-2 prompt.")
                    st.stop()
                if second_engine == "Gemini (Google)" and not gemini_key:
                    st.error("Gemini API key required.")
                    st.stop()
                if second_engine == "Claude (Anthropic)" and not anthropic_key:
                    st.error("Anthropic API key required.")
                    st.stop()

                rows_out = []
                html_files = []
                prog = st.progress(0, text="Processing…")
                n = len(df_in)

                for i, (_, row) in enumerate(df_in.iterrows(), start=1):
                    pt = str(row[col_t]) if pd.notna(row[col_t]) else ""
                    pdsc = str(row[col_d]) if pd.notna(row[col_d]) else ""
                    plink = (
                        str(row[col_l]) if col_l and pd.notna(row[col_l]) else ""
                    )

                    try:
                        draft_res, final_res = run_l1_l2_batch(
                            pt,
                            pdsc,
                            plink,
                            batch_l1_prompt,
                            batch_l2_prompt,
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
                        rows_out.append(
                            {
                                "Row": i,
                                "Prev Title": pt,
                                "New Title": final_res["new_title"],
                                "New Description (HTML)": final_res[
                                    "new_description"
                                ],
                                "Short-tail": ", ".join(
                                    final_res["keywords_short"]
                                ),
                                "Mid-tail": ", ".join(
                                    final_res["keywords_mid"]
                                ),
                                "Long-tail": ", ".join(
                                    final_res["keywords_long"]
                                ),
                            }
                        )
                        html_bytes, _, fname = html_report_bytes(
                            title_text=f"Shakti 1.2 — Batch Report #{i}",
                            inputs={
                                "prev_title": pt,
                                "prev_desc": pdsc,
                                "product_link": plink,
                            },
                            draft=draft_res,
                            final_=final_res,
                        )
                        html_files.append((f"report_{i:02d}.html", html_bytes))
                    except Exception as e:
                        rows_out.append(
                            {
                                "Row": i,
                                "Prev Title": pt,
                                "New Title": f"[ERROR] {e}",
                                "New Description (HTML)": "",
                                "Short-tail": "",
                                "Mid-tail": "",
                                "Long-tail": "",
                            }
                        )
                    prog.progress(i / n, text=f"Processed {i}/{n}")

                st.success("Batch complete.")
                df_out = pd.DataFrame(rows_out)
                st.dataframe(df_out, use_container_width=True, height=600)
                st.download_button(
                    "⬇️ Download Batch CSV",
                    data=df_out.to_csv(index=False).encode("utf-8"),
                    file_name="shakti_batch_results.csv",
                    mime="text/csv",
                )

                memzip = io.BytesIO()
                with zipfile.ZipFile(memzip, "w", zipfile.ZIP_DEFLATED) as zf:
                    for name, data in html_files:
                        zf.writestr(name, data)
                memzip.seek(0)
                st.download_button(
                    "⬇️ Download All HTML Reports (ZIP)",
                    data=memzip.getvalue(),
                    file_name="shakti_batch_reports.zip",
                    mime="application/zip",
                )
        except Exception as e:
            st.error(f"Unable to read CSV: {e}")

# =====================================================
#           TAB ④ — GPT-5 CHAT
# =====================================================

with tabs[3]:
    st.subheader("GPT-5 Chat Panel (OpenAI key)")
    st.caption("Pick any model (e.g., GPT-5) if your access allows.")
    chat_model_choice = st.selectbox(
        "Model",
        list(OPENAI_MODELS.keys()),
        index=3 if "GPT-5 (if enabled)" in OPENAI_MODELS else 0,
    )
    chat_model = OPENAI_MODELS[chat_model_choice]

    cfg = st.session_state.get("engine_cfg", {})
    base_key = cfg.get("openai_key")
    chat_key_mode = st.radio(
        "OpenAI Key Source",
        ["Reuse engine key", "Enter another key"],
        horizontal=True,
        key="chat_km",
    )
    chat_key = (
        base_key
        if chat_key_mode == "Reuse engine key"
        else st.text_input(
            "OpenAI API Key (chat)", type="password", key="chat_key"
        )
    )

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    with st.form("chat_form", clear_on_submit=True):
        chat_input = st.text_area(
            "Message", height=120, placeholder="Ask anything…"
        )
        submitted = st.form_submit_button("Send")

    if submitted:
        if not chat_key:
            st.error("OpenAI API key required for chat.")
            st.stop()
        try:
            st.session_state.chat_history.append(("user", chat_input))
            msgs = [
                {
                    "role": "system",
                    "content": "You are ChatGPT inside Shakti 1.2 chat panel.",
                }
            ]
            for role, content in st.session_state.chat_history:
                msgs.append(
                    {"role": role, "content": to_utf8_clean(content)}
                )
            reply = openai_chat_completion(
                api_key=chat_key,
                model=chat_model,
                temperature=0.2,
                messages=msgs,
            ).strip()
            st.session_state.chat_history.append(("assistant", reply))
        except Exception as e:
            st.error(f"Chat error: {e}")

    for role, content in st.session_state.chat_history:
        if role == "user":
            st.markdown(f"**You:** {content}")
        else:
            st.markdown(
                f"**Assistant ({chat_model_choice}):** {content}"
            )
