import streamlit as st
import cloudscraper
from bs4 import BeautifulSoup
import json
import base64
import re
import time
import random
import requests
from io import BytesIO
from PIL import Image
from openai import OpenAI
from urllib.parse import urljoin, urlparse, unquote

# -------------------------------------------------
# PAGE CONFIG
# -------------------------------------------------
st.set_page_config(
    page_title="Ecom Image SEO | AI-Powered Product Image Intelligence",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# -------------------------------------------------
# CUSTOM CSS FOR PROFESSIONAL UI
# -------------------------------------------------
st.markdown("""
<style>
    /* Main app styling */
    .main {
        background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%);
    }
    
    /* Header styling */
    .app-header {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 50%, #1e3c72 100%);
        padding: 2rem 2rem 1.5rem 2rem;
        border-radius: 0 0 20px 20px;
        margin: -1rem -1rem 2rem -1rem;
        box-shadow: 0 4px 20px rgba(0,0,0,0.15);
    }
    
    .app-title {
        color: #ffffff;
        font-size: 2.5rem;
        font-weight: 700;
        margin: 0;
        text-align: center;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
    }
    
    .app-subtitle {
        color: #a8d0ff;
        font-size: 1.1rem;
        text-align: center;
        margin-top: 0.5rem;
        font-weight: 400;
    }
    
    .app-credits {
        display: flex;
        justify-content: center;
        gap: 3rem;
        margin-top: 1.5rem;
        flex-wrap: wrap;
    }
    
    .credit-item {
        text-align: center;
        color: #ffffff;
    }
    
    .credit-label {
        font-size: 0.75rem;
        color: #a8d0ff;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 0.2rem;
    }
    
    .credit-value {
        font-size: 0.95rem;
        font-weight: 600;
        color: #ffffff;
    }
    
    /* Card styling */
    .stExpander {
        background-color: #ffffff;
        border: 1px solid #e0e5ec;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }
    
    /* Button styling */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 0.6rem 1.5rem;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.5);
    }
    
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        box-shadow: 0 4px 15px rgba(17, 153, 142, 0.4);
    }
    
    .stButton > button[kind="primary"]:hover {
        box-shadow: 0 6px 20px rgba(17, 153, 142, 0.5);
    }
    
    /* Input styling */
    .stTextInput > div > div > input {
        border-radius: 10px;
        border: 2px solid #e0e5ec;
        padding: 0.6rem 1rem;
        transition: border-color 0.3s ease;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
    }
    
    .stTextArea > div > div > textarea {
        border-radius: 10px;
        border: 2px solid #e0e5ec;
    }
    
    .stTextArea > div > div > textarea:focus {
        border-color: #667eea;
    }
    
    /* Section headers */
    .section-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-size: 1.5rem;
        font-weight: 700;
        margin: 1.5rem 0 1rem 0;
    }
    
    /* Info boxes */
    .stAlert {
        border-radius: 12px;
        border: none;
    }
    
    /* Metric cards */
    .metric-card {
        background: #ffffff;
        padding: 1rem 1.5rem;
        border-radius: 12px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.08);
        border-left: 4px solid #667eea;
    }
    
    .metric-label {
        color: #6c757d;
        font-size: 0.85rem;
        margin-bottom: 0.3rem;
    }
    
    .metric-value {
        color: #1e3c72;
        font-size: 1.1rem;
        font-weight: 600;
    }
    
    /* Divider */
    hr {
        border: none;
        height: 2px;
        background: linear-gradient(90deg, transparent, #667eea, transparent);
        margin: 2rem 0;
    }
    
    /* Radio buttons */
    .stRadio > div {
        background: #ffffff;
        padding: 1rem;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }
    
    /* Multiselect */
    .stMultiSelect > div > div {
        border-radius: 10px;
    }
    
    /* Image Scorecard Styles */
    .scorecard-container {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
        gap: 1.5rem;
        padding: 1rem 0;
    }
    
    .image-scorecard {
        background: linear-gradient(145deg, #ffffff 0%, #f8f9fa 100%);
        border-radius: 16px;
        overflow: hidden;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        border: 1px solid #e9ecef;
    }
    
    .image-scorecard:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 30px rgba(0,0,0,0.12);
    }
    
    .scorecard-image-wrap {
        position: relative;
        width: 100%;
        height: 200px;
        overflow: hidden;
        background: #f0f0f0;
    }
    
    .scorecard-image-wrap img {
        width: 100%;
        height: 100%;
        object-fit: cover;
    }
    
    .scorecard-badge {
        position: absolute;
        top: 12px;
        left: 12px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    
    .scorecard-score {
        position: absolute;
        top: 12px;
        right: 12px;
        width: 50px;
        height: 50px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.2rem;
        font-weight: 700;
        color: white;
        box-shadow: 0 2px 10px rgba(0,0,0,0.2);
    }
    
    .score-high { background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); }
    .score-medium { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }
    .score-low { background: linear-gradient(135deg, #eb3349 0%, #f45c43 100%); }
    
    .scorecard-body {
        padding: 1.25rem;
    }
    
    .scorecard-title {
        font-size: 0.85rem;
        font-weight: 600;
        color: #1e3c72;
        margin-bottom: 0.75rem;
        line-height: 1.4;
    }
    
    .scorecard-summary {
        font-size: 0.8rem;
        color: #495057;
        line-height: 1.5;
        margin-bottom: 1rem;
    }
    
    .scorecard-tags {
        display: flex;
        flex-wrap: wrap;
        gap: 0.4rem;
        margin-bottom: 1rem;
    }
    
    .scorecard-tag {
        background: #e7f1ff;
        color: #0066cc;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 0.7rem;
        font-weight: 500;
    }
    
    .scorecard-tag.missing {
        background: #ffe6e6;
        color: #cc0000;
    }
    
    .scorecard-tag.found {
        background: #e6ffe6;
        color: #008000;
    }
    
    .scorecard-metrics {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 0.5rem;
        border-top: 1px solid #e9ecef;
        padding-top: 1rem;
    }
    
    .scorecard-metric {
        text-align: center;
    }
    
    .scorecard-metric-value {
        font-size: 1rem;
        font-weight: 700;
        color: #1e3c72;
    }
    
    .scorecard-metric-label {
        font-size: 0.65rem;
        color: #6c757d;
        text-transform: uppercase;
    }
    
    .quality-indicator {
        display: inline-flex;
        align-items: center;
        gap: 0.3rem;
        padding: 4px 10px;
        border-radius: 8px;
        font-size: 0.75rem;
        font-weight: 500;
    }
    
    .quality-high {
        background: #d4edda;
        color: #155724;
    }
    
    .quality-medium {
        background: #fff3cd;
        color: #856404;
    }
    
    .quality-low {
        background: #f8d7da;
        color: #721c24;
    }
    
    /* Success/Error messages */
    .stSuccess {
        background-color: #d4edda;
        border-radius: 10px;
    }
    
    .stError {
        background-color: #f8d7da;
        border-radius: 10px;
    }
    
    /* Download button */
    .stDownloadButton > button {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        border: none;
        border-radius: 10px;
        color: white;
        font-weight: 600;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Spinner */
    .stSpinner > div {
        border-color: #667eea;
    }
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 10px 10px 0 0;
        padding: 10px 20px;
        background-color: #f0f2f6;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #667eea;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------
# APP HEADER
# -------------------------------------------------
st.markdown("""
<div class="app-header">
    <h1 class="app-title">🛒 Ecom Image SEO</h1>
    <p class="app-subtitle">AI-Powered Product Image Intelligence for Amazon & Flipkart</p>
    <div class="app-credits">
        <div class="credit-item">
            <div class="credit-label">App Author</div>
            <div class="credit-value">Vishal Tiwari (PW17633)</div>
        </div>
        <div class="credit-item">
            <div class="credit-label">Project Head</div>
            <div class="credit-value">Kumar Sanskar</div>
        </div>
        <div class="credit-item">
            <div class="credit-label">Version</div>
            <div class="credit-value">1.0.0</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# -------------------------------------------------
# SESSION STATE INITIALIZATION
# -------------------------------------------------
if 'product' not in st.session_state:
    st.session_state.product = None
if 'ai_response' not in st.session_state:
    st.session_state.ai_response = None
if 'image_brief' not in st.session_state:
    st.session_state.image_brief = None
if 'generated_images' not in st.session_state:
    st.session_state.generated_images = {}
if 'analysis_done' not in st.session_state:
    st.session_state.analysis_done = False
if 'image_scorecards' not in st.session_state:
    st.session_state.image_scorecards = []
if 'quick_summary' not in st.session_state:
    st.session_state.quick_summary = None

# -------------------------------------------------
# API KEY INPUT
# -------------------------------------------------
st.markdown("### 🔐 Configuration")
api_col1, api_col2 = st.columns([2, 1])
with api_col1:
    user_api_key = st.text_input(
        "🔑 OpenAI API Key",
        type="password",
        placeholder="sk-...",
        help="Enter your OpenAI API key to enable AI analysis and image generation"
    )
client = OpenAI(api_key=user_api_key) if user_api_key else None

with api_col2:
    if user_api_key:
        st.success("✅ API Key Provided")
    else:
        st.warning("⚠️ API Key Required")

st.markdown("---")

# -------------------------------------------------
# INPUT MODE SELECTION
# -------------------------------------------------
st.markdown("### 📥 Data Input")
input_mode = st.radio(
    "Choose your preferred input method:",
    ["🔗 URL Scraping (Auto)", "✍️ Manual Input (Recommended for Amazon)"],
    horizontal=True,
    key="input_mode_radio",
    help="URL Scraping auto-extracts product data. Manual Input gives you full control and bypasses anti-bot protection."
)

if input_mode == "🔗 URL Scraping (Auto)":
    product_url = st.text_input("🔗 Paste Amazon / Flipkart Product URL", key="product_url_input")
    manual_mode = False
else:
    manual_mode = True
    product_url = None
    
    st.info("💡 **Tip:** Copy product details from Amazon/Flipkart page and paste below. This bypasses anti-bot protection.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        manual_platform = st.selectbox("Platform", ["Amazon", "Flipkart", "Both"], key="manual_platform")
        manual_title = st.text_area("📌 Product Title", height=80, placeholder="Paste the product title here...", key="manual_title")
        manual_brand = st.text_input("🏷️ Brand Name", placeholder="e.g., Physics Wallah, Arihant, MTG...", key="manual_brand")
        manual_price = st.text_input("💰 Price", placeholder="e.g., ₹499", key="manual_price")
        manual_rating = st.text_input("⭐ Rating", placeholder="e.g., 4.2 out of 5", key="manual_rating")
        
    with col2:
        manual_category = st.text_input("📂 Category", placeholder="e.g., Books > Education > JEE", key="manual_category")
        manual_whats_in_box = st.text_area("📦 What's in the Box", height=80, placeholder="List all items included...", key="manual_whats_in_box")
        
    manual_bullets = st.text_area(
        "📝 Bullet Points / Highlights (one per line)", 
        height=150,
        placeholder="• Chapter-wise questions\n• Previous year papers included\n• Detailed solutions\n• Covers all topics...",
        key="manual_bullets"
    )
    
    manual_description = st.text_area(
        "📄 Full Description", 
        height=150,
        placeholder="Paste the product description here...",
        key="manual_description"
    )
    
    manual_reviews = st.text_area(
        "💬 Customer Reviews (paste 3-5 reviews)", 
        height=150,
        placeholder="Review 1: Great book for JEE preparation...\n\nReview 2: Quality is excellent...",
        key="manual_reviews"
    )
    
    manual_image_urls = st.text_area(
        "🖼️ Image URLs (one per line, optional)",
        height=100,
        placeholder="https://m.media-amazon.com/images/I/...\nhttps://m.media-amazon.com/images/I/...",
        key="manual_image_urls"
    )

analyze_btn = st.button("🎯 Generate Image Strategy", key="analyze_btn")

# -------------------------------------------------
# ROBUST SCRAPER WITH MULTIPLE FALLBACKS
# -------------------------------------------------

def create_scraper_with_headers():
    """Create scraper with rotating user agents and realistic headers"""
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    ]
    
    scraper = cloudscraper.create_scraper(
        browser={
            "browser": "chrome",
            "platform": "windows",
            "desktop": True,
            "mobile": False
        },
        delay=5,
        interpreter='nodejs'  # Use nodejs for better JS challenge solving
    )
    
    selected_ua = random.choice(user_agents)
    
    scraper.headers.update({
        "User-Agent": selected_ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7,hi;q=0.6",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Sec-CH-UA": '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
        "Sec-CH-UA-Mobile": "?0",
        "Sec-CH-UA-Platform": '"Windows"',
        "Cache-Control": "max-age=0",
        "Pragma": "no-cache",
    })
    
    return scraper

def create_simple_session():
    """Create a simple requests session as fallback"""
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-IN,en;q=0.9",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
    })
    return session

def extract_with_fallbacks(soup, selectors, extract_type="text"):
    """Try multiple selectors and return first successful match"""
    for selector in selectors:
        try:
            element = soup.select_one(selector)
            if element:
                if extract_type == "text":
                    return element.get_text(strip=True)
                elif extract_type == "html":
                    return str(element)
                elif extract_type == "src":
                    return element.get("src") or element.get("data-src") or element.get("data-old-hires")
        except:
            continue
    return None

def extract_all_with_fallbacks(soup, selectors, extract_type="text", limit=None):
    """Try multiple selectors and return all matches from first successful selector"""
    for selector in selectors:
        try:
            elements = soup.select(selector)
            if elements:
                results = []
                for el in elements[:limit] if limit else elements:
                    if extract_type == "text":
                        text = el.get_text(strip=True)
                        if text:
                            results.append(text)
                    elif extract_type == "src":
                        src = el.get("src") or el.get("data-src") or el.get("data-old-hires") or el.get("data-a-dynamic-image")
                        if src:
                            results.append(src)
                if results:
                    return results
        except:
            continue
    return []

def clean_text(text):
    """Clean and normalize extracted text"""
    if not text:
        return ""
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    # Remove special characters that break JSON
    text = text.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
    return text.strip()

def get_image_dimensions(url, timeout=10):
    """Fetch image and get its dimensions to check quality"""
    try:
        response = requests.get(url, timeout=timeout, stream=True)
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content))
            return img.size  # (width, height)
    except:
        pass
    return None

def validate_image_quality(url, min_width=500, min_height=500):
    """Validate if an image meets minimum quality requirements"""
    dimensions = get_image_dimensions(url)
    if dimensions:
        width, height = dimensions
        return {
            "valid": width >= min_width and height >= min_height,
            "width": width,
            "height": height,
            "quality": "high" if width >= 1000 and height >= 1000 else "medium" if width >= 500 else "low"
        }
    return {"valid": False, "width": 0, "height": 0, "quality": "unknown"}

def analyze_single_image_with_vision(client, image_url, product_context, image_number):
    """Use GPT-4o Vision to analyze a single product image in detail"""
    
    analysis_prompt = f"""Analyze this e-commerce product image (Image #{image_number}) in extreme detail.

PRODUCT CONTEXT:
{product_context}

YOUR TASK - Extract EVERYTHING visible in this image:

1. **VISIBLE TEXT** (read ALL text exactly as shown):
   - Product titles, subtitles
   - Feature callouts, bullet points
   - Numbers, specifications, measurements
   - Brand names, logos
   - Certifications, badges
   - Price tags, offers
   - Any fine print

2. **VISIBLE ELEMENTS**:
   - Physical products shown (books, boxes, components)
   - Count of each item visible
   - Colors, sizes, materials
   - Packaging details
   - USB ports, cables, accessories
   - Buttons, interfaces, ports
   - Any included materials

3. **USPs VISIBLE** (claims/features shown):
   - What benefits are highlighted?
   - What features are demonstrated?
   - What makes this product special (as shown)?

4. **QUALITY ASSESSMENT**:
   - Is the image sharp or blurry?
   - Is lighting good?
   - Is background professional?
   - Are all items clearly visible?

5. **COMPLIANCE CHECK**:
   - For Image 1: Is background pure white?
   - Any text overlays?
   - Any watermarks?
   - Is product filling ~85% frame?

Respond in this EXACT JSON format only (no markdown):
{{
    "image_number": {image_number},
    "visible_text": ["exact text 1", "exact text 2"],
    "visible_products": [
        {{"item": "item name", "count": 1, "description": "brief desc"}}
    ],
    "visible_usps": ["usp 1", "usp 2"],
    "ports_connectors": ["usb-c", "hdmi", etc or empty],
    "certifications_badges": ["CE", "ISI", etc or empty],
    "quality_score": 8,
    "quality_issues": ["issue 1 if any"],
    "is_sharp": true,
    "is_professional": true,
    "background_type": "white/colored/lifestyle/transparent",
    "compliance_score": 9,
    "compliance_issues": ["issue if any"],
    "summary": "2-3 sentence summary of what this image communicates"
}}"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": analysis_prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": image_url, "detail": "high"}
                        }
                    ]
                }
            ],
            max_tokens=1500,
            temperature=0.1,
            timeout=45
        )
        
        result = response.choices[0].message.content.strip()
        # Clean JSON if wrapped in markdown
        if result.startswith("```"):
            result = re.sub(r'^```json?\n?', '', result)
            result = re.sub(r'\n?```$', '', result)
        
        return json.loads(result)
    except json.JSONDecodeError:
        return {
            "image_number": image_number,
            "error": "Failed to parse AI response",
            "visible_text": [],
            "visible_products": [],
            "visible_usps": [],
            "quality_score": 5,
            "compliance_score": 5,
            "summary": "AI response could not be parsed"
        }
    except Exception as e:
        return {
            "image_number": image_number,
            "error": str(e),
            "visible_text": [],
            "visible_products": [],
            "visible_usps": [],
            "quality_score": 0,
            "compliance_score": 0,
            "summary": f"Failed to analyze: {str(e)[:50]}"
        }

def generate_image_scorecards(client, images, product):
    """Generate detailed scorecards for all product images using Vision API"""
    
    # Create product context for the AI
    product_context = f"""
Title: {product.get('title', 'Unknown')}
Brand: {product.get('brand', 'Unknown')}
Category: {product.get('category', 'Unknown')}
Bullets: {' | '.join(product.get('bullets', [])[:5])}
What's in Box: {product.get('whats_in_box', 'Unknown')}
"""
    
    scorecards = []
    
    for idx, img_url in enumerate(images[:7], 1):  # Analyze up to 7 images
        # First validate image quality
        quality_info = validate_image_quality(img_url)
        
        # Then do vision analysis
        analysis = analyze_single_image_with_vision(client, img_url, product_context, idx)
        
        # Combine quality info with analysis
        scorecard = {
            "image_number": idx,
            "image_url": img_url,
            "dimensions": f"{quality_info.get('width', 0)}x{quality_info.get('height', 0)}",
            "resolution_quality": quality_info.get('quality', 'unknown'),
            "is_valid_resolution": quality_info.get('valid', False),
            **analysis
        }
        
        scorecards.append(scorecard)
    
    return scorecards

def render_scorecard_html(scorecard):
    """Render a single scorecard as HTML"""
    
    img_num = scorecard.get('image_number', 1)
    quality_score = scorecard.get('quality_score', 0)
    compliance_score = scorecard.get('compliance_score', 0)
    overall_score = round((quality_score + compliance_score) / 2, 1)
    
    # Score class
    score_class = "score-high" if overall_score >= 7 else "score-medium" if overall_score >= 5 else "score-low"
    
    # Quality badge
    res_quality = scorecard.get('resolution_quality', 'unknown')
    quality_class = "quality-high" if res_quality == "high" else "quality-medium" if res_quality == "medium" else "quality-low"
    quality_emoji = "🟢" if res_quality == "high" else "🟡" if res_quality == "medium" else "🔴"
    
    # Build tags
    found_tags = []
    missing_tags = []
    
    for usp in scorecard.get('visible_usps', [])[:3]:
        found_tags.append(f'<span class="scorecard-tag found">✓ {usp[:25]}{"..." if len(usp) > 25 else ""}</span>')
    
    for issue in scorecard.get('quality_issues', [])[:2]:
        missing_tags.append(f'<span class="scorecard-tag missing">✗ {issue[:25]}{"..." if len(issue) > 25 else ""}</span>')
    
    for issue in scorecard.get('compliance_issues', [])[:2]:
        missing_tags.append(f'<span class="scorecard-tag missing">⚠ {issue[:25]}{"..." if len(issue) > 25 else ""}</span>')
    
    tags_html = ''.join(found_tags + missing_tags) if (found_tags or missing_tags) else '<span class="scorecard-tag">No tags</span>'
    
    # Summary
    summary = scorecard.get('summary', 'No analysis available')[:150]
    if len(scorecard.get('summary', '')) > 150:
        summary += "..."
    
    # Visible text preview
    visible_text = scorecard.get('visible_text', [])
    text_preview = ', '.join(visible_text[:3])[:60] + "..." if visible_text else "No text detected"
    
    return f'''
    <div class="image-scorecard">
        <div class="scorecard-image-wrap">
            <img src="{scorecard.get('image_url', '')}" alt="Image {img_num}" onerror="this.src='https://via.placeholder.com/300x200?text=Image+{img_num}'">
            <div class="scorecard-badge">Image {img_num}</div>
            <div class="scorecard-score {score_class}">{overall_score}</div>
        </div>
        <div class="scorecard-body">
            <div class="scorecard-title">
                <span class="quality-indicator {quality_class}">{quality_emoji} {scorecard.get('dimensions', 'N/A')}</span>
                &nbsp;|&nbsp;
                <span style="color: #6c757d;">{scorecard.get('background_type', 'Unknown')} bg</span>
            </div>
            <div class="scorecard-summary">{summary}</div>
            <div class="scorecard-tags">{tags_html}</div>
            <div class="scorecard-metrics">
                <div class="scorecard-metric">
                    <div class="scorecard-metric-value">{quality_score}/10</div>
                    <div class="scorecard-metric-label">Quality</div>
                </div>
                <div class="scorecard-metric">
                    <div class="scorecard-metric-value">{compliance_score}/10</div>
                    <div class="scorecard-metric-label">Compliance</div>
                </div>
                <div class="scorecard-metric">
                    <div class="scorecard-metric-value">{len(scorecard.get('visible_usps', []))}</div>
                    <div class="scorecard-metric-label">USPs Found</div>
                </div>
            </div>
        </div>
    </div>
    '''

def extract_amazon_images(soup, url):
    """Extract all product images from Amazon with multiple strategies"""
    images = []
    
    # Strategy 1: Main image container
    main_img_selectors = [
        "#landingImage",
        "#imgBlkFront",
        "#ebooksImgBlkFront",
        "img.a-dynamic-image",
        "#main-image-container img",
        "#imageBlock img",
    ]
    
    for selector in main_img_selectors:
        img = soup.select_one(selector)
        if img:
            # Priority: data-old-hires (highest res) > data-a-dynamic-image > src
            src = img.get("data-old-hires") or img.get("data-a-dynamic-image") or img.get("src")
            if src and src not in images:
                # Handle data-a-dynamic-image which contains JSON with multiple resolutions
                if src.startswith("{"):
                    try:
                        img_dict = json.loads(src)
                        # Get the highest resolution (largest dimensions)
                        if img_dict:
                            best_url = max(img_dict.keys(), key=lambda u: img_dict[u][0] * img_dict[u][1] if isinstance(img_dict[u], list) and len(img_dict[u]) >= 2 else 0)
                            src = best_url
                    except:
                        pass
                if src and "data:image" not in src:
                    # Convert to maximum resolution
                    high_res = convert_amazon_to_hires(src)
                    if high_res not in images:
                        images.append(high_res)
    
    # Strategy 2: Thumbnail strip images
    thumb_selectors = [
        "#altImages img",
        ".imageThumbnail img",
        "#imageBlock_feature_div img",
        "li.image img",
        "li.a-spacing-small img",
        ".imgTagWrapper img",
    ]
    
    for selector in thumb_selectors:
        thumbs = soup.select(selector)
        for thumb in thumbs:
            src = thumb.get("data-old-hires") or thumb.get("src") or thumb.get("data-src")
            if src and "data:image" not in src and "sprite" not in src.lower() and "icon" not in src.lower():
                # Convert thumbnail to high-res
                high_res = convert_amazon_to_hires(src)
                if high_res not in images:
                    images.append(high_res)
    
    # Strategy 3: Extract from JavaScript data - look for hiRes images
    scripts = soup.find_all("script", string=re.compile(r"colorImages|ImageBlockATF|'initial'|hiRes|large"))
    for script in scripts:
        try:
            script_text = script.string or ""
            
            # Look for hiRes URLs specifically (highest quality)
            hires_matches = re.findall(r'"hiRes"\s*:\s*"(https://[^"]+)"', script_text)
            for match in hires_matches:
                if match not in images and "sprite" not in match.lower():
                    images.append(match)
            
            # Look for large image URLs
            large_matches = re.findall(r'"large"\s*:\s*"(https://[^"]+)"', script_text)
            for match in large_matches:
                high_res = convert_amazon_to_hires(match)
                if high_res not in images and "sprite" not in high_res.lower():
                    images.append(high_res)
            
            # Fallback: Find any image URLs and convert to high-res
            all_matches = re.findall(r'https://m\.media-amazon\.com/images/I/[^"\']+\.(?:jpg|jpeg|png|webp)', script_text)
            for match in all_matches:
                high_res = convert_amazon_to_hires(match)
                if high_res not in images and "sprite" not in high_res.lower():
                    images.append(high_res)
        except:
            continue
    
    # Remove duplicates while preserving order
    seen = set()
    unique_images = []
    for img in images:
        if img not in seen:
            seen.add(img)
            unique_images.append(img)
    
    return unique_images[:10]  # Limit to 10 images

def convert_amazon_to_hires(url):
    """Convert Amazon image URL to highest resolution version"""
    if not url:
        return url
    
    # Remove ALL size constraints to get original/highest resolution
    # Common patterns: ._SX300_., ._SL1500_., ._AC_SX679_., ._SS40_., etc.
    high_res = url
    
    # Remove underscore patterns that limit size
    patterns_to_remove = [
        r'\._[A-Z]{2}_[A-Z0-9_,]+_\.',
        r'\._[A-Z0-9_,]+_\.',
        r'_SX\d+_',
        r'_SY\d+_',
        r'_SL\d+_',
        r'_SS\d+_',
        r'_AC_',
        r'_SR\d+,\d+_',
        r'_CR\d+,\d+,\d+,\d+_',
        r'_QL\d+_',
        r'_UX\d+_',
        r'_UY\d+_',
        r'_PIbundle[^_]*_',
    ]
    
    for pattern in patterns_to_remove:
        high_res = re.sub(pattern, '.', high_res)
    
    # Clean up any double dots or trailing dots before extension
    high_res = re.sub(r'\.+', '.', high_res)
    high_res = re.sub(r'\.(\.(jpg|jpeg|png|webp|gif))', r'\1', high_res, flags=re.IGNORECASE)
    
    return high_res

def convert_flipkart_to_hires(url):
    """Convert Flipkart image URL to highest resolution version"""
    if not url:
        return url
    
    # Flipkart uses patterns like /128/128/ or /416/416/ for dimensions
    # Convert to maximum size (1664 is typically the max available)
    high_res = re.sub(r'/\d+/\d+/', '/1664/1664/', url)
    
    # Also handle _XXX. patterns
    high_res = re.sub(r'_\d+\.', '_1664.', high_res)
    
    # Handle q=XX quality parameter - set to max (100)
    high_res = re.sub(r'q=\d+', 'q=100', high_res)
    
    # Handle width/height query params
    high_res = re.sub(r'w=\d+', 'w=1664', high_res)
    high_res = re.sub(r'h=\d+', 'h=1664', high_res)
    
    return high_res

def extract_flipkart_images(soup, url):
    """Extract all product images from Flipkart with multiple strategies"""
    images = []
    
    # Strategy 1: Main product images
    img_selectors = [
        "img._396cs4",
        "img._2r_T1I",
        "div._3kidJX img",
        "div._1BweB8 img",
        "img.q6DClP",
        "img._2amPTt",
        "img.DByuf4",
        "img._0DkuPH",
    ]
    
    for selector in img_selectors:
        imgs = soup.select(selector)
        for img in imgs:
            src = img.get("src") or img.get("data-src")
            if src and "data:image" not in src:
                # Convert to high resolution
                high_res = convert_flipkart_to_hires(src)
                if high_res not in images:
                    images.append(high_res)
    
    # Strategy 2: Thumbnail images
    thumb_selectors = [
        "div._3GnUWp img",
        "div._1Nyybr img",
        "ul._3GnUWp img",
        "div._2mLllQ img",
        "li._20Gt85 img",
    ]
    
    for selector in thumb_selectors:
        thumbs = soup.select(selector)
        for thumb in thumbs:
            src = thumb.get("src") or thumb.get("data-src")
            if src and "data:image" not in src:
                high_res = convert_flipkart_to_hires(src)
                if high_res not in images:
                    images.append(high_res)
    
    # Strategy 3: Extract from page scripts/data
    scripts = soup.find_all("script", string=re.compile(r'imageUrl|originalUrl|url.*image'))
    for script in scripts:
        try:
            script_text = script.string or ""
            # Find Flipkart CDN URLs
            matches = re.findall(r'https://rukminim[12]\.flixcart\.com/image/[^"\']+', script_text)
            for match in matches:
                high_res = convert_flipkart_to_hires(match)
                if high_res not in images:
                    images.append(high_res)
        except:
            continue
    
    # Remove duplicates while preserving order
    seen = set()
    unique_images = []
    for img in images:
        if img not in seen:
            seen.add(img)
            unique_images.append(img)
    
    return unique_images[:10]

def scrape_amazon(soup, url):
    """Comprehensive Amazon scraper with multiple fallback selectors"""
    data = {
        "platform": "Amazon",
        "url": url,
        "title": "NOT_FOUND",
        "brand": "NOT_FOUND",
        "price": "NOT_FOUND",
        "rating": "NOT_FOUND",
        "review_count": "NOT_FOUND",
        "bullets": [],
        "description": "NOT_FOUND",
        "whats_in_box": "NOT_FOUND",
        "product_details": {},
        "reviews": [],
        "images": [],
        "category": "NOT_FOUND",
    }
    
    # Title - multiple selectors
    title_selectors = [
        "#productTitle",
        "#title span",
        "h1.a-size-large",
        "span#productTitle",
        "#ebooksProductTitle",
    ]
    data["title"] = extract_with_fallbacks(soup, title_selectors) or "NOT_FOUND"
    
    # Brand
    brand_selectors = [
        "#bylineInfo",
        "a#bylineInfo",
        ".po-brand .po-break-word",
        "tr.po-brand td.a-span9 span",
        "#brand",
    ]
    data["brand"] = extract_with_fallbacks(soup, brand_selectors) or "NOT_FOUND"
    
    # Price
    price_selectors = [
        "span.a-price-whole",
        "#priceblock_ourprice",
        "#priceblock_dealprice",
        "span.a-offscreen",
        "#corePrice_feature_div span.a-offscreen",
        "#corePriceDisplay_desktop_feature_div span.a-offscreen",
        ".a-price .a-offscreen",
    ]
    data["price"] = extract_with_fallbacks(soup, price_selectors) or "NOT_FOUND"
    
    # Rating
    rating_selectors = [
        "span.a-icon-alt",
        "#acrPopover span.a-icon-alt",
        "i.a-icon-star span.a-icon-alt",
    ]
    rating_text = extract_with_fallbacks(soup, rating_selectors)
    if rating_text:
        match = re.search(r'([\d.]+)', rating_text)
        data["rating"] = match.group(1) if match else rating_text
    
    # Review count
    review_count_selectors = [
        "#acrCustomerReviewText",
        "#acrCustomerReviewLink span",
        "span[data-hook='total-review-count']",
    ]
    data["review_count"] = extract_with_fallbacks(soup, review_count_selectors) or "NOT_FOUND"
    
    # Bullet points / Feature bullets
    bullet_selectors = [
        "#feature-bullets li:not(.aok-hidden) span.a-list-item",
        "#feature-bullets li span",
        "#feature-bullets ul li span",
        ".a-unordered-list.a-vertical li span.a-list-item",
    ]
    bullets = extract_all_with_fallbacks(soup, bullet_selectors, limit=10)
    data["bullets"] = [clean_text(b) for b in bullets if len(b) > 5]
    
    # Product description
    desc_selectors = [
        "#productDescription p",
        "#productDescription",
        "#aplus_feature_div",
        "#aplus p",
        "#bookDescription_feature_div noscript",
        "#bookDescription_feature_div span",
        "div[data-a-expander-name='book_description_expander'] span",
    ]
    desc = extract_with_fallbacks(soup, desc_selectors)
    data["description"] = clean_text(desc) if desc else " | ".join(data["bullets"])
    
    # What's in the box
    box_selectors = [
        "#whats-in-the-box ul",
        "#whats-in-the-box",
        "div[data-feature-name='whatsInTheBox']",
        "#witb_feature_div",
    ]
    box_content = extract_with_fallbacks(soup, box_selectors)
    if box_content:
        data["whats_in_box"] = clean_text(box_content)
    
    # Product details table
    detail_tables = soup.select("#productDetails_techSpec_section_1 tr, #productDetails_detailBullets_sections1 tr, .prodDetTable tr")
    for row in detail_tables:
        try:
            key = row.select_one("th, td:first-child")
            val = row.select_one("td:last-child, td:nth-child(2)")
            if key and val:
                k = clean_text(key.get_text())
                v = clean_text(val.get_text())
                if k and v:
                    data["product_details"][k] = v
        except:
            continue
    
    # Also try detail bullets format
    detail_bullets = soup.select("#detailBullets_feature_div li, #detailBulletsWrapper_feature_div li")
    for bullet in detail_bullets:
        try:
            text = bullet.get_text(strip=True)
            if ":" in text:
                parts = text.split(":", 1)
                if len(parts) == 2:
                    data["product_details"][clean_text(parts[0])] = clean_text(parts[1])
        except:
            continue
    
    # Customer reviews
    review_selectors = [
        "span[data-hook='review-body'] span",
        "div.review-text-content span",
        "#cm-cr-dp-review-list div.review span.review-text",
    ]
    reviews = extract_all_with_fallbacks(soup, review_selectors, limit=8)
    data["reviews"] = [clean_text(r)[:500] for r in reviews if len(r) > 20]
    
    # Review titles
    review_title_selectors = [
        "a[data-hook='review-title'] span:not(.a-icon-alt)",
        "span[data-hook='review-title'] span",
    ]
    review_titles = extract_all_with_fallbacks(soup, review_title_selectors, limit=8)
    if review_titles:
        data["review_titles"] = [clean_text(t) for t in review_titles]
    
    # Images
    data["images"] = extract_amazon_images(soup, url)
    
    # Category / Breadcrumb
    breadcrumb_selectors = [
        "#wayfinding-breadcrumbs_feature_div a",
        ".a-breadcrumb a",
        "#nav-subnav a.nav-a",
    ]
    breadcrumbs = extract_all_with_fallbacks(soup, breadcrumb_selectors, limit=5)
    if breadcrumbs:
        data["category"] = " > ".join(breadcrumbs)
    
    return data

def scrape_flipkart(soup, url):
    """Comprehensive Flipkart scraper with multiple fallback selectors"""
    data = {
        "platform": "Flipkart",
        "url": url,
        "title": "NOT_FOUND",
        "brand": "NOT_FOUND",
        "price": "NOT_FOUND",
        "rating": "NOT_FOUND",
        "review_count": "NOT_FOUND",
        "bullets": [],
        "description": "NOT_FOUND",
        "highlights": [],
        "specifications": {},
        "reviews": [],
        "images": [],
        "category": "NOT_FOUND",
        "seller": "NOT_FOUND",
    }
    
    # Title - multiple selectors (Flipkart changes classes frequently)
    title_selectors = [
        "span.B_NuCI",
        "span.VU-ZEz",
        "h1.yhB1nd span",
        "h1._6EBuvT span",
        ".C7fEHH h1 span",
        "h1 span.B_NuCI",
        "._35KyD6",
    ]
    data["title"] = extract_with_fallbacks(soup, title_selectors) or "NOT_FOUND"
    
    # Brand
    brand_selectors = [
        "span._2WkVRV",
        "a._2whKao",
        ".G6XhRU",
    ]
    data["brand"] = extract_with_fallbacks(soup, brand_selectors) or "NOT_FOUND"
    
    # Price
    price_selectors = [
        "div._30jeq3",
        "div._16Jk6d",
        "._25b18c ._30jeq3",
        "div.Nx9bqj",
        ".CEmiEU div",
    ]
    data["price"] = extract_with_fallbacks(soup, price_selectors) or "NOT_FOUND"
    
    # Rating
    rating_selectors = [
        "div._3LWZlK",
        "div._2d4LTz",
        "span._1lRcqv div._3LWZlK",
    ]
    data["rating"] = extract_with_fallbacks(soup, rating_selectors) or "NOT_FOUND"
    
    # Review count
    review_selectors = [
        "span._2_R_DZ span",
        "span._13vcmD",
        "._1fQZEK span",
    ]
    review_count_text = extract_with_fallbacks(soup, review_selectors)
    if review_count_text:
        data["review_count"] = clean_text(review_count_text)
    
    # Highlights
    highlight_selectors = [
        "li._21Ahn-",
        "ul._1xgFaf li",
        "div._1mXcCf li",
        ".X3BRps li",
        "._2418kt li",
    ]
    highlights = extract_all_with_fallbacks(soup, highlight_selectors, limit=10)
    data["highlights"] = [clean_text(h) for h in highlights if len(h) > 3]
    data["bullets"] = data["highlights"]  # Alias for consistency
    
    # Description
    desc_selectors = [
        "div._1mXcCf p",
        "div._1mXcCf",
        "div.RmoJUa",
        "div._1AN87F",
        "p._2RngUh",
    ]
    desc = extract_with_fallbacks(soup, desc_selectors)
    data["description"] = clean_text(desc) if desc else " | ".join(data["highlights"])
    
    # Specifications - try multiple table formats
    spec_tables = soup.select("table._14cfVK tr, div._3k-BhJ div._1UhVsV, .X3BRps table tr, ._2RngUh table tr")
    for row in spec_tables:
        try:
            cols = row.select("td")
            if len(cols) >= 2:
                key = clean_text(cols[0].get_text())
                val = clean_text(cols[1].get_text())
                if key and val:
                    data["specifications"][key] = val
        except:
            continue
    
    # Also try key-value div format
    spec_rows = soup.select("div._3_6Uyw row, ._14cfVK ._1hKmbr")
    for row in spec_rows:
        try:
            label = row.select_one("._2H87wv, ._2k4JXJ")
            value = row.select_one("._3YhLQA, ._2cKhwK")
            if label and value:
                data["specifications"][clean_text(label.get_text())] = clean_text(value.get_text())
        except:
            continue
    
    # Customer reviews
    review_body_selectors = [
        "div.t-ZTKy",
        "div._6K-7Co",
        "p._2-N8zT",
        "div.ZmyHeo div",
    ]
    reviews = extract_all_with_fallbacks(soup, review_body_selectors, limit=8)
    data["reviews"] = [clean_text(r)[:500] for r in reviews if len(r) > 20]
    
    # Review titles
    review_title_selectors = [
        "p._2-N8zT",
        "p._2sc7ZR",
    ]
    review_titles = extract_all_with_fallbacks(soup, review_title_selectors, limit=8)
    if review_titles:
        data["review_titles"] = [clean_text(t) for t in review_titles]
    
    # Images
    data["images"] = extract_flipkart_images(soup, url)
    
    # Category breadcrumb
    breadcrumb_selectors = [
        "div._1MR4o5 a",
        "a._2whKao",
        "div._3GIHBu a",
    ]
    breadcrumbs = extract_all_with_fallbacks(soup, breadcrumb_selectors, limit=5)
    if breadcrumbs:
        data["category"] = " > ".join(breadcrumbs)
    
    # Seller info
    seller_selectors = [
        "div._1RLviY span",
        "#sellerName span",
        "div._3enH42 span",
    ]
    data["seller"] = extract_with_fallbacks(soup, seller_selectors) or "NOT_FOUND"
    
    return data

def scrape_product(url: str, max_retries: int = 3) -> dict:
    """Main scraping function with retry logic and comprehensive extraction"""
    
    last_error = None
    methods_tried = []
    
    # Clean URL - remove tracking parameters
    clean_url = url.split('?')[0] if '?' in url else url
    if '/ref=' in clean_url:
        clean_url = clean_url.split('/ref=')[0]
    
    # Method 1: CloudScraper with enhanced headers
    for attempt in range(max_retries):
        try:
            methods_tried.append(f"CloudScraper attempt {attempt + 1}")
            scraper = create_scraper_with_headers()
            
            # Add delay between retries
            if attempt > 0:
                time.sleep(random.uniform(3, 7))
            
            # First visit homepage to get cookies
            if "amazon" in url.lower():
                try:
                    scraper.get("https://www.amazon.in/", timeout=10)
                    time.sleep(random.uniform(1, 2))
                except:
                    pass
            
            res = scraper.get(url, timeout=35)
            
            # Check for anti-bot pages
            if res.status_code != 200:
                raise Exception(f"HTTP {res.status_code}")
            
            # More lenient anti-bot check
            page_lower = res.text.lower()
            if "captcha" in page_lower and "enter the characters" in page_lower:
                raise Exception("CAPTCHA detected")
            if "automated access" in page_lower:
                raise Exception("Automated access blocked")
            if "api-services-support@amazon.com" in page_lower:
                raise Exception("Amazon bot detection")
            
            soup = BeautifulSoup(res.text, "lxml")
            
            # Detect platform and scrape accordingly
            if "amazon" in url.lower():
                data = scrape_amazon(soup, url)
            elif "flipkart" in url.lower():
                data = scrape_flipkart(soup, url)
            else:
                # Generic fallback
                data = {
                    "platform": "Unknown",
                    "url": url,
                    "title": extract_with_fallbacks(soup, ["h1", "title"]) or "NOT_FOUND",
                    "description": extract_with_fallbacks(soup, ["meta[name='description']"]) or "NOT_FOUND",
                    "images": [],
                    "reviews": [],
                }
            
            # Validate we got meaningful data
            if data["title"] not in ["NOT_FOUND", "", None]:
                return data
            
            if data.get("bullets") and len(data["bullets"]) > 0:
                return data
                
            raise Exception("Failed to extract product data - page structure may have changed")
            
        except Exception as e:
            last_error = str(e)
            continue
    
    # Method 2: Simple requests session (sometimes works better)
    try:
        methods_tried.append("Simple requests session")
        session = create_simple_session()
        time.sleep(random.uniform(2, 4))
        
        res = session.get(url, timeout=30)
        
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "lxml")
            
            if "amazon" in url.lower():
                data = scrape_amazon(soup, url)
            elif "flipkart" in url.lower():
                data = scrape_flipkart(soup, url)
            else:
                data = {
                    "platform": "Unknown",
                    "url": url,
                    "title": extract_with_fallbacks(soup, ["h1", "title"]) or "NOT_FOUND",
                    "description": "NOT_FOUND",
                    "images": [],
                    "reviews": [],
                }
            
            if data["title"] not in ["NOT_FOUND", "", None]:
                return data
                
    except Exception as e:
        last_error = str(e)
    
    # Return error data if all methods failed
    return {
        "platform": "Amazon" if "amazon" in url.lower() else "Flipkart" if "flipkart" in url.lower() else "Unknown",
        "url": url,
        "title": "SCRAPING_FAILED",
        "description": f"Failed after multiple attempts. Error: {last_error}",
        "images": [],
        "reviews": [],
        "bullets": [],
        "error": last_error,
        "methods_tried": methods_tried,
        "suggestion": "Please use Manual Input mode - copy product details from the Amazon/Flipkart page and paste them directly."
    }

def create_manual_product_data(platform, title, brand, price, rating, category, bullets_text, description, whats_in_box, reviews_text, image_urls_text):
    """Create product data structure from manual input"""
    
    # Parse bullets
    bullets = []
    if bullets_text:
        for line in bullets_text.strip().split('\n'):
            line = line.strip()
            if line:
                # Remove bullet characters
                line = re.sub(r'^[•\-\*]\s*', '', line)
                if line:
                    bullets.append(line)
    
    # Parse reviews
    reviews = []
    if reviews_text:
        # Split by double newline or "Review X:" pattern
        review_parts = re.split(r'\n\n+|Review \d+:', reviews_text)
        for part in review_parts:
            part = part.strip()
            if part and len(part) > 10:
                reviews.append(part[:500])
    
    # Parse image URLs
    images = []
    if image_urls_text:
        for line in image_urls_text.strip().split('\n'):
            line = line.strip()
            if line and (line.startswith('http://') or line.startswith('https://')):
                images.append(line)
    
    return {
        "platform": platform,
        "url": "Manual Input",
        "title": title or "NOT_PROVIDED",
        "brand": brand or "NOT_PROVIDED",
        "price": price or "NOT_PROVIDED",
        "rating": rating or "NOT_PROVIDED",
        "review_count": "N/A",
        "category": category or "NOT_PROVIDED",
        "bullets": bullets,
        "description": description or " | ".join(bullets) if bullets else "NOT_PROVIDED",
        "whats_in_box": whats_in_box or "NOT_PROVIDED",
        "product_details": {},
        "specifications": {},
        "reviews": reviews,
        "images": images,
        "input_method": "manual"
    }

# -------------------------------------------------
# IMAGE-FOCUSED SEO PROMPT (CONCISE OUTPUT)
# -------------------------------------------------
def image_seo_prompt(product: dict) -> str:
    # Format bullets/highlights
    bullets_text = "\n".join([f"  • {b}" for b in product.get('bullets', [])]) or "NOT_FOUND"
    
    # Format product details/specifications
    details = product.get('product_details', {}) or product.get('specifications', {})
    details_text = "\n".join([f"  • {k}: {v}" for k, v in details.items()]) if details else "NOT_FOUND"
    
    # Format reviews
    reviews_text = "\n".join([f"  [{i+1}] {r}" for i, r in enumerate(product.get('reviews', []))]) or "No reviews found"
    
    # Format images
    images_list = product.get('images', [])
    images_text = "\n".join([f"  Image {i+1}: {url}" for i, url in enumerate(images_list)]) if images_list else "No images extracted"
    
    # Get what's in box
    whats_in_box = product.get('whats_in_box', 'NOT_FOUND')
    
    return f"""
You are a senior eCommerce SEO Image Strategist for Amazon India and Flipkart India.
Analyze the product listing and provide a CONCISE, ACTION-ORIENTED report.

================================================================================
PRODUCT DATA
================================================================================
PLATFORM: {product.get('platform', 'Unknown')}
TITLE: {product.get('title', 'NOT_FOUND')}
BRAND: {product.get('brand', 'NOT_FOUND')}
PRICE: {product.get('price', 'NOT_FOUND')}
RATING: {product.get('rating', 'NOT_FOUND')}
CATEGORY: {product.get('category', 'NOT_FOUND')}

BULLETS:
{bullets_text}

DESCRIPTION:
{product.get('description', 'NOT_FOUND')}

WHAT'S IN BOX:
{whats_in_box}

PRODUCT DETAILS:
{details_text}

CURRENT IMAGES:
{images_text}

REVIEWS:
{reviews_text}

================================================================================
OUTPUT FORMAT (Keep each section SHORT and ACTIONABLE)
================================================================================

## 🎯 QUICK SUMMARY (3 sentences max)
[Product type, target audience, key value proposition]

## 📋 USP MAP (Table format, max 6 rows)
| USP | Source | Must Show? |
|-----|--------|------------|

## 🖼️ IMAGE 1 SCORE: X/10
**Quick verdict:** [One sentence]
**Top 3 issues:**
1. [Issue + Fix]
2. [Issue + Fix]  
3. [Issue + Fix]

## ⚠️ TOP 5 GAPS (Priority order)
1. **[Gap]** → [One-line fix]
2. **[Gap]** → [One-line fix]
3. **[Gap]** → [One-line fix]
4. **[Gap]** → [One-line fix]
5. **[Gap]** → [One-line fix]

## 🛒 AMAZON IMAGE PROMPTS (Concise)

### Image 1 - Hero
**Goal:** [One line]
**Composition:** [One line]
**Must show:** [Comma-separated list]
**Avoid:** [Comma-separated list]

### Image 2 - Contents
**Goal:** [One line]
**Must show:** [Comma-separated list]

### Image 3 - Benefits
**Goal:** [One line]
**Must show:** [Comma-separated list]

### Image 4-7
[Brief 2-line description for each]

## 🛍️ FLIPKART IMAGE PROMPTS (Concise)
[Same format as Amazon, highlight QC differences only]

---
Keep EVERYTHING concise. No verbose explanations. Bullet points preferred.
"""

# -------------------------------------------------
# IMAGE BRIEF PACK PROMPT (FOR STRUCTURED JSON OUTPUT)
# -------------------------------------------------
def image_brief_prompt(product: dict) -> str:
    """Generate the prompt for creating IMAGE_BRIEF_PACK JSON"""
    
    # Format bullets/highlights
    bullets_text = "\n".join([f"  • {b}" for b in product.get('bullets', [])]) or "NOT_FOUND"
    
    # Format product details/specifications
    details = product.get('product_details', {}) or product.get('specifications', {})
    details_text = "\n".join([f"  • {k}: {v}" for k, v in details.items()]) if details else "NOT_FOUND"
    
    # Format reviews
    reviews_text = "\n".join([f"  [{i+1}] {r}" for i, r in enumerate(product.get('reviews', []))]) or "No reviews found"
    
    # Get what's in box
    whats_in_box = product.get('whats_in_box', 'NOT_FOUND')
    
    return f"""You are an eCommerce Image CRO Analyst for Amazon India + Flipkart India.
You will NOT rewrite listing title/description. Your only output is a structured "Image Brief Pack" for image creation.

INPUTS PROVIDED:
- Platform: {product.get('platform', 'Both')}
- Product type: (infer from title/category - Book / Experiment Kit / Combo / Other)
- Listing copy (as-is):
  - Title: {product.get('title', 'NOT_FOUND')}
  - Brand: {product.get('brand', 'NOT_FOUND')}
  - Price: {product.get('price', 'NOT_FOUND')}
  - Category: {product.get('category', 'NOT_FOUND')}
  - Bullets/Highlights:
{bullets_text}
  - Description: {product.get('description', 'NOT_FOUND')}
  - What's in the box: {whats_in_box}
  - Product Details:
{details_text}
- Target audience/exam context: (infer from title - JEE/NEET/Class 9-12/etc.)
- Customer Reviews:
{reviews_text}

TASK:
1) Extract a USP/Claim Map from listing copy (no invention).
2) For each USP, decide the best VISUAL EVIDENCE type:
   - show product physically, show contents layout, show close-up detail, show usage steps, show outcome/benefit iconography, show trust proof (only if verifiable).
3) Identify "Must show" items for compliance + buyer clarity:
   - Exact included items, counts, dimensions if present, compatibility (class/exam), language/edition if present.
4) Decide per-image objectives (Image 1..7) for Amazon and Flipkart separately.
5) Output a single JSON called IMAGE_BRIEF_PACK.

COMPLIANCE RULES:
- Amazon Image 1: white background, no text/graphics/watermarks, product ~85% frame, accurate contents depiction.
- Flipkart: QC-safe first; if text overlays might be restricted, mark them "optional" and provide a no-text plan.

OUTPUT FORMAT (ONLY JSON, nothing else):
{{
  "product_summary": {{
    "title": "...",
    "type": "Book/Combo/Kit/Other",
    "target_audience": "...",
    "exam_context": "JEE/NEET/Board/etc",
    "key_differentiator": "..."
  }},
  "usp_map": [
    {{"usp_id":"USP1","claim":"...","source_in_copy":"...","buyer_intent":"trust/learning/value/contents/quality","visual_evidence_type":"product_physical|contents_layout|close_up|usage_steps|benefit_icon|trust_proof","risk_flag":"none|vague|unverifiable|qc-risk"}}
  ],
  "included_items": [
    {{"item":"...","count":"...","must_show":true,"source_in_copy":"..."}}
  ],
  "image_strategy": {{
    "amazon": [
      {{"image_no":1,"objective":"Hero - show complete product/combo on white","composition":"45-degree angle, all items visible, proportional sizing","must_include":["item1","item2"],"avoid":["text","badges","props"],"text_overlay":"none","background":"pure white RGB(255,255,255)","lighting":"soft studio, even shadows"}},
      {{"image_no":2,"objective":"Contents spread - what's inside","composition":"flat lay or organized grid","must_include":["all included items with counts"],"avoid":["cluttered arrangement"],"text_overlay":"allowed_secondary_only","background":"light neutral"}},
      {{"image_no":3,"objective":"Benefits/Learning outcomes","composition":"infographic style","must_include":["key USPs visualized"],"avoid":["unverifiable claims"],"text_overlay":"allowed_secondary_only","background":"light gradient"}},
      {{"image_no":4,"objective":"How to use / Study approach","composition":"step-by-step visual","must_include":["usage demonstration"],"avoid":["complex text"],"text_overlay":"allowed_secondary_only","background":"contextual"}},
      {{"image_no":5,"objective":"Close-up quality/pages/components","composition":"macro detail shot","must_include":["quality indicators"],"avoid":["blurry details"],"text_overlay":"minimal","background":"white or neutral"}},
      {{"image_no":6,"objective":"Lifestyle/Context - student using","composition":"student at study desk","must_include":["realistic study environment"],"avoid":["stock photo feel"],"text_overlay":"none","background":"real environment"}},
      {{"image_no":7,"objective":"Trust/Social proof","composition":"ratings, reviews highlight","must_include":["verifiable claims only"],"avoid":["fake testimonials"],"text_overlay":"allowed","background":"branded"}}
    ],
    "flipkart": [
      {{"image_no":1,"objective":"Hero - QC-safe product shot","composition":"similar to Amazon hero","must_include":["complete product"],"avoid":["text","watermarks"],"text_overlay":"prefer_none","background":"white/light","qc_safe_alternate":"same as primary"}},
      {{"image_no":2,"objective":"Contents layout","composition":"organized display","must_include":["all items"],"avoid":["text if QC restricted"],"text_overlay":"optional_with_alt","background":"light","qc_safe_alternate":"no text version"}},
      {{"image_no":3,"objective":"Key benefits","composition":"visual hierarchy","must_include":["top 3 USPs"],"avoid":["crowded layout"],"text_overlay":"optional_with_alt","background":"light gradient","qc_safe_alternate":"icon-only version"}},
      {{"image_no":4,"objective":"Usage guide","composition":"step visual","must_include":["clear steps"],"avoid":["tiny text"],"text_overlay":"optional_with_alt","background":"neutral","qc_safe_alternate":"visual-only"}},
      {{"image_no":5,"objective":"Detail shots","composition":"close-up","must_include":["quality features"],"avoid":["blur"],"text_overlay":"prefer_none","background":"white"}},
      {{"image_no":6,"objective":"Context/Lifestyle","composition":"study scene","must_include":["aspirational context"],"avoid":["unrealistic"],"text_overlay":"none","background":"real"}},
      {{"image_no":7,"objective":"Value proposition","composition":"comparison or bundle value","must_include":["clear value"],"avoid":["competitor mentions"],"text_overlay":"optional_with_alt","background":"branded","qc_safe_alternate":"visual comparison"}}
    ]
  }},
  "creative_constraints": {{
    "style":"clean, modern, high-trust, education-focused",
    "color_palette":"professional blues, greens for education; avoid flashy colors",
    "typography":"if text allowed - clean sans-serif, high contrast, readable at thumbnail",
    "background_rules": {{"amazon_hero":"pure white RGB(255,255,255)","amazon_secondary":"light neutral or gradient","flipkart":"white/light, QC-safe"}},
    "accuracy_rules":["Do not invent contents","Do not add fake badges/certifications","No misleading props","Show actual item count","Match edition/language from listing"],
    "thumbnail_test":"All key info must be visible at 150x150px"
  }},
  "image_generation_prompts": {{
    "hero_prompt": "detailed prompt for generating hero image...",
    "contents_prompt": "detailed prompt for contents spread image...",
    "benefits_prompt": "detailed prompt for benefits infographic...",
    "usage_prompt": "detailed prompt for usage/how-to image...",
    "detail_prompt": "detailed prompt for close-up detail image...",
    "lifestyle_prompt": "detailed prompt for lifestyle/context image...",
    "trust_prompt": "detailed prompt for trust/social proof image..."
  }},
  "open_questions_if_any":[]
}}

IMPORTANT:
- Return ONLY the JSON object, no markdown formatting, no code blocks, no explanation.
- Make sure the JSON is valid and parseable.
- Be specific in the image_generation_prompts - they will be used directly for AI image generation.
"""

# -------------------------------------------------
# IMAGE GENERATION PROMPT BUILDER
# -------------------------------------------------
def build_image_gen_prompt(brief: dict, image_type: str, platform: str = "amazon") -> str:
    """Build a detailed image generation prompt from the brief"""
    
    product_summary = brief.get("product_summary", {})
    included_items = brief.get("included_items", [])
    creative_constraints = brief.get("creative_constraints", {})
    image_strategy = brief.get("image_strategy", {}).get(platform.lower(), [])
    gen_prompts = brief.get("image_generation_prompts", {})
    
    # Get items list
    items_list = ", ".join([f"{item['count']} {item['item']}" for item in included_items if item.get('must_show')])
    
    # Base prompt components
    product_type = product_summary.get("type", "educational product")
    target = product_summary.get("target_audience", "students")
    exam = product_summary.get("exam_context", "competitive exams")
    
    # Find the specific image config
    image_config = None
    image_no_map = {
        "hero": 1, "contents": 2, "benefits": 3, 
        "usage": 4, "detail": 5, "lifestyle": 6, "trust": 7
    }
    target_no = image_no_map.get(image_type, 1)
    
    for img in image_strategy:
        if img.get("image_no") == target_no:
            image_config = img
            break
    
    if not image_config:
        image_config = {"objective": "Product shot", "must_include": [], "avoid": [], "background": "white"}
    
    # Check if we have a pre-built prompt
    prompt_key = f"{image_type}_prompt"
    if prompt_key in gen_prompts and gen_prompts[prompt_key]:
        base_prompt = gen_prompts[prompt_key]
    else:
        base_prompt = image_config.get("objective", "Professional product photo")
    
    # Build the full prompt
    prompts = {
        "hero": f"""Professional eCommerce product photography for {platform.upper()}.

Product: {product_summary.get('title', 'Educational Book/Kit')}
Type: {product_type}
Target: {target} preparing for {exam}

REQUIREMENTS:
- Pure white background (RGB 255, 255, 255)
- Product fills approximately 85% of the frame
- 45-degree angle shot showing depth and dimension
- All included items visible: {items_list}
- Items arranged proportionally by actual size
- Sharp focus throughout
- Soft, even studio lighting with subtle shadows
- High resolution, photorealistic quality

MUST INCLUDE: {', '.join(image_config.get('must_include', ['complete product']))}

MUST AVOID:
- Any text, labels, or graphics on the image
- Watermarks or logos
- Props not included with product
- Cropped or cut-off products
- Harsh shadows or reflections

STYLE: Clean, professional, trustworthy, premium educational product
OUTPUT: Square format (1024x1024), Amazon/Flipkart marketplace ready""",

        "contents": f"""Flat-lay product contents photography for eCommerce.

Product: {product_summary.get('title', 'Educational Product')}
Show: Complete contents spread / What's inside the box

COMPOSITION:
- Bird's eye view (top-down angle)
- Organized grid or artistic flat-lay arrangement
- Each item clearly visible and identifiable
- Items: {items_list}
- Show actual quantities (e.g., if 3 books, show all 3)
- Include any bonus materials, booklets, accessories

BACKGROUND: Light neutral (off-white or very light gray)
LIGHTING: Even, shadow-free overhead lighting

STYLE: Clean, organized, informative, reveals full value
{"Text overlay allowed for labels" if platform == "amazon" else "Prefer no text for Flipkart QC safety"}

OUTPUT: Square format (1024x1024), high resolution""",

        "benefits": f"""Educational product benefits infographic for eCommerce.

Product: {product_summary.get('title', 'Educational Product')}
Target: {target} for {exam}

COMPOSITION:
- Product centered or on one side
- Visual icons/graphics showing key benefits
- Clean visual hierarchy
- 3-4 key benefits highlighted

KEY BENEFITS TO SHOW:
{chr(10).join(['- ' + usp.get('claim', '') for usp in brief.get('usp_map', [])[:4]])}

BACKGROUND: Light gradient (white to light blue/green)
STYLE: Modern infographic, education-focused, trustworthy
TYPOGRAPHY: If text needed - clean sans-serif, high contrast

{"Secondary image - text overlays allowed" if platform == "amazon" else "Flipkart: Prefer visual icons over text for QC safety"}

OUTPUT: Square format (1024x1024)""",

        "usage": f"""Step-by-step usage guide image for educational product.

Product: {product_summary.get('title', 'Educational Product')}
Audience: {target}

SHOW:
- How to effectively use this product
- Study approach or learning methodology
- 3-4 clear steps visualized
- Student-friendly demonstration

COMPOSITION:
- Sequential visual flow (left to right or numbered)
- Each step clearly distinct
- Realistic study context

BACKGROUND: Neutral, contextual study environment elements
STYLE: Instructional, clear, approachable

OUTPUT: Square format (1024x1024)""",

        "detail": f"""Close-up detail shot for educational product quality.

Product: {product_summary.get('title', 'Educational Product')}

FOCUS ON:
- Paper/print quality (if book)
- Page layout and typography
- Binding quality
- Component quality (if kit)
- Any unique features mentioned in listing

COMPOSITION:
- Macro/close-up angle
- Sharp focus on quality details
- Show texture and craftsmanship
- Multiple detail callouts if needed

BACKGROUND: White or very light, non-distracting
LIGHTING: Detailed lighting showing textures

STYLE: Quality-focused, builds trust, shows premium feel

OUTPUT: Square format (1024x1024)""",

        "lifestyle": f"""Lifestyle/contextual image for educational product.

Product: {product_summary.get('title', 'Educational Product')}
Target: {target} preparing for {exam}

SCENE:
- Indian student (age-appropriate for target) at study desk
- Clean, organized, aspirational study environment
- Natural lighting from window
- Product being actively used (reading/writing)
- Focused, determined expression

MUST INCLUDE:
- The actual product visible and identifiable
- Realistic Indian home/room study setup
- Appropriate age student ({target})

AVOID:
- Stock photo feel
- Western environments
- Unrealistic setups
- Celebrity or model-like appearance

STYLE: Aspirational but relatable, authentic Indian context

OUTPUT: Square format (1024x1024)""",

        "trust": f"""Trust and credibility image for educational product.

Product: {product_summary.get('title', 'Educational Product')}

CAN INCLUDE (only if verifiable from listing):
- Rating/review highlights (actual numbers from listing)
- Awards or recognition (only if mentioned)
- Expert endorsements (only if real)
- User testimonials (summarized)
- "Trusted by X students" (only if actual claim)

COMPOSITION:
- Professional, credibility-focused layout
- Clean data visualization if showing stats
- Trust badges or indicators

BACKGROUND: Branded or professional gradient
STYLE: Corporate trust, social proof, credibility

NOTE: Do not invent any claims, certifications, or numbers not in the listing.

OUTPUT: Square format (1024x1024)"""
    }
    
    return prompts.get(image_type, prompts["hero"])

# -------------------------------------------------
# IMAGE PROMPT BUILDER (LEGACY - kept for compatibility)
# -------------------------------------------------
def image_prompt_from_strategy(strategy: dict) -> str:
    hero = strategy["image_strategy"]["hero_image"]
    return f"""
Professional e-commerce product image.

Hero Image Requirements:
Background: {hero['background']}
Angle: {hero['angle']}
Must show: {', '.join(hero['must_show'])}

Style:
White background, studio lighting, sharp focus,
high realism, Amazon-ready, no text overlays.
"""

# -------------------------------------------------
# SELF-HEALING JSON PARSER
# -------------------------------------------------
def safe_json_from_ai(raw_text: str, client: OpenAI) -> dict:
    if not raw_text or not raw_text.strip():
        raise ValueError("Empty AI response")

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        repair_prompt = f"""
Fix the following into VALID JSON ONLY.
No text. No markdown.

CONTENT:
{raw_text}
"""
        repair_resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": repair_prompt}],
            temperature=0
        )
        return json.loads(repair_resp.choices[0].message.content.strip())

# -------------------------------------------------
# MAIN FLOW WITH SESSION STATE
# -------------------------------------------------

# Handle the analyze button click - store results in session state
if analyze_btn:
    if not user_api_key:
        st.error("API key is required.")
        st.stop()

    # Handle Manual Input Mode
    if manual_mode:
        if not manual_title or not manual_title.strip():
            st.error("Please provide at least the Product Title.")
            st.stop()
        
        with st.spinner("📝 Processing manual input..."):
            product = create_manual_product_data(
                platform=manual_platform,
                title=manual_title,
                brand=manual_brand,
                price=manual_price,
                rating=manual_rating,
                category=manual_category,
                bullets_text=manual_bullets,
                description=manual_description,
                whats_in_box=manual_whats_in_box,
                reviews_text=manual_reviews,
                image_urls_text=manual_image_urls
            )
        # Store in session state
        st.session_state.product = product
        st.success("✅ Manual data processed successfully!")
    
    # Handle URL Scraping Mode
    else:
        if not product_url:
            st.error("Please provide a product URL.")
            st.stop()
        
        with st.spinner("🔍 Scraping product data (this may take a moment)..."):
            product = scrape_product(product_url)

        # Check for scraping errors
        if product.get("title") == "SCRAPING_FAILED":
            st.error(f"❌ Failed to scrape product: {product.get('error', 'Unknown error')}")
            if product.get('suggestion'):
                st.warning(f"💡 **Suggestion:** {product['suggestion']}")
            if product.get('methods_tried'):
                with st.expander("🔧 Debug Info"):
                    st.write("Methods attempted:", product['methods_tried'])
            st.info("👆 **Try using 'Manual Input' mode** - it works 100% of the time! Just copy the product details from the Amazon/Flipkart page.")
            st.stop()
        
        # Store in session state
        st.session_state.product = product

    # Generate AI Analysis
    try:
        with st.spinner("🧠 Generating Image Strategy Analysis..."):
            resp = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": image_seo_prompt(st.session_state.product)}],
                temperature=0.2,
                max_tokens=4000,
                timeout=60
            )
            st.session_state.ai_response = resp.choices[0].message.content
    except Exception as e:
        st.error(f"❌ Failed to connect to OpenAI API: {str(e)}")
        st.warning("🔧 **Troubleshooting tips:**\n- Check your internet connection\n- Verify your API key is correct\n- Try again in a few moments")
        st.session_state.ai_response = None

    # Generate Image Scorecards (Vision Analysis)
    if st.session_state.product.get('images'):
        with st.spinner("🔍 Analyzing each image with AI Vision (this provides detailed insights)..."):
            try:
                st.session_state.image_scorecards = generate_image_scorecards(
                    client, 
                    st.session_state.product['images'], 
                    st.session_state.product
                )
            except Exception as e:
                st.warning(f"Could not generate image scorecards: {str(e)}")
                st.session_state.image_scorecards = []
    
    # Generate Quick Summary
    try:
        with st.spinner("📝 Generating quick summary..."):
            quick_summary_prompt = f"""Based on this product, give me a 3-bullet executive summary:

Title: {st.session_state.product.get('title', 'Unknown')}
Platform: {st.session_state.product.get('platform', 'Unknown')}
Category: {st.session_state.product.get('category', 'Unknown')}
Price: {st.session_state.product.get('price', 'Unknown')}
Rating: {st.session_state.product.get('rating', 'Unknown')}
Images found: {len(st.session_state.product.get('images', []))}
Bullets: {st.session_state.product.get('bullets', [])[:3]}

Format:
• **Product:** [Type + target in 10 words]
• **Key Issue:** [Biggest image/listing gap in 15 words]
• **Quick Win:** [Most impactful improvement in 15 words]

Keep it SHORT."""

            summary_resp = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": quick_summary_prompt}],
                temperature=0.2,
                max_tokens=300,
                timeout=30
            )
            st.session_state.quick_summary = summary_resp.choices[0].message.content
    except Exception as e:
        st.warning(f"Could not generate quick summary: {str(e)}")
        st.session_state.quick_summary = None

    # Generate Image Brief Pack
    try:
        with st.spinner("📋 Generating Image Brief Pack..."):
            brief_resp = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": image_brief_prompt(st.session_state.product)}],
                temperature=0.1,
                max_tokens=6000,
                timeout=90
            )
            brief_raw = brief_resp.choices[0].message.content
            
            # Parse the JSON response
            try:
                cleaned_brief = brief_raw.strip()
                if cleaned_brief.startswith("```"):
                    cleaned_brief = re.sub(r'^```json?\n?', '', cleaned_brief)
                    cleaned_brief = re.sub(r'\n?```$', '', cleaned_brief)
                st.session_state.image_brief = json.loads(cleaned_brief)
            except json.JSONDecodeError:
                try:
                    st.session_state.image_brief = safe_json_from_ai(brief_raw, client)
                except:
                    st.session_state.image_brief = None
    except Exception as e:
        st.warning(f"Could not generate image brief: {str(e)}")
        st.session_state.image_brief = None
    
    st.session_state.analysis_done = True
    st.rerun()

# -------------------------------------------------
# DISPLAY RESULTS (if analysis is done)
# -------------------------------------------------
if st.session_state.analysis_done and st.session_state.product:
    product = st.session_state.product
    
    st.markdown("---")
    
    # =========================================================
    # QUICK SUMMARY SECTION (NEW - Concise Overview)
    # =========================================================
    if st.session_state.quick_summary:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    padding: 1.5rem; border-radius: 12px; margin-bottom: 1.5rem;">
            <h3 style="color: white; margin: 0 0 1rem 0;">⚡ Quick Summary</h3>
            <div style="color: #e8e8e8; font-size: 1rem; line-height: 1.6;">
        """, unsafe_allow_html=True)
        st.markdown(st.session_state.quick_summary)
        st.markdown("</div></div>", unsafe_allow_html=True)
    
    # Display scraped/input data in organized sections
    st.markdown('<p class="section-header">📦 Product Data Extracted</p>', unsafe_allow_html=True)
    
    # Product metrics in card layout
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Platform</div>
            <div class="metric-value">{product.get('platform', 'Unknown')}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Price</div>
            <div class="metric-value">{product.get('price', 'N/A')}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Rating</div>
            <div class="metric-value">{product.get('rating', 'N/A')}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        input_method = "✍️ Manual" if product.get('input_method') == 'manual' else "🔗 Scraped"
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Input Method</div>
            <div class="metric-value">{input_method}</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Product title and brand
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown(f"**📌 Title:** {product.get('title', 'N/A')}")
        st.markdown(f"**🏷️ Brand:** {product.get('brand', 'N/A')}")
        st.markdown(f"**📂 Category:** {product.get('category', 'N/A')}")
    
    with col2:
        if product.get('images'):
            st.info(f"🖼️ **{len(product['images'])}** Images Found")
        if product.get('bullets'):
            st.info(f"📝 **{len(product['bullets'])}** Bullet Points")
        if product.get('reviews'):
            st.info(f"💬 **{len(product['reviews'])}** Reviews")
    
    # Display bullets/highlights
    if product.get('bullets'):
        with st.expander("📝 Bullets / Highlights", expanded=False):
            for bullet in product['bullets']:
                st.markdown(f"• {bullet}")
    
    # Display what's in the box
    if product.get('whats_in_box') and product['whats_in_box'] not in ["NOT_FOUND", "NOT_PROVIDED"]:
        with st.expander("📦 What's in the Box"):
            st.write(product['whats_in_box'])
    
    # Display description
    if product.get('description') and product['description'] not in ["NOT_FOUND", "NOT_PROVIDED"]:
        with st.expander("📄 Description"):
            st.write(product['description'])
    
    st.markdown("---")
    
    # =========================================================
    # IMAGE SCORECARDS SECTION (NEW - Beautiful Cards)
    # =========================================================
    if st.session_state.image_scorecards:
        st.markdown('<p class="section-header">🎴 Image Analysis Scorecards</p>', unsafe_allow_html=True)
        
        # Calculate aggregate stats
        total_images = len(st.session_state.image_scorecards)
        avg_quality = sum(s.get('quality_score', 0) for s in st.session_state.image_scorecards) / total_images if total_images else 0
        avg_compliance = sum(s.get('compliance_score', 0) for s in st.session_state.image_scorecards) / total_images if total_images else 0
        total_usps = sum(len(s.get('visible_usps', [])) for s in st.session_state.image_scorecards)
        high_res_count = sum(1 for s in st.session_state.image_scorecards if s.get('resolution_quality') == 'high')
        
        # Aggregate stats row
        stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)
        with stat_col1:
            st.metric("📊 Avg Quality", f"{avg_quality:.1f}/10", delta=None)
        with stat_col2:
            st.metric("✅ Avg Compliance", f"{avg_compliance:.1f}/10", delta=None)
        with stat_col3:
            st.metric("✨ USPs Found", total_usps, delta=None)
        with stat_col4:
            st.metric("🖼️ High-Res", f"{high_res_count}/{total_images}", delta=None)
        
        st.markdown("""
        <p style="color: #6c757d; margin: 1rem 0;">
            Each image analyzed with AI Vision. Scores based on quality, compliance & USP coverage.
        </p>
        """, unsafe_allow_html=True)
        
        # Render scorecards in a grid
        scorecards_html = '<div class="scorecard-container">'
        for scorecard in st.session_state.image_scorecards:
            scorecards_html += render_scorecard_html(scorecard)
        scorecards_html += '</div>'
        
        st.markdown(scorecards_html, unsafe_allow_html=True)
        
        # Detailed view for each scorecard
        st.markdown("<br>", unsafe_allow_html=True)
        with st.expander("📊 Detailed Image Analysis", expanded=False):
            for scorecard in st.session_state.image_scorecards:
                st.markdown(f"### Image {scorecard.get('image_number', '?')}")
                
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    try:
                        st.image(scorecard.get('image_url', ''), use_container_width=True)
                    except:
                        st.markdown(f"[View Image]({scorecard.get('image_url', '')})")
                
                with col2:
                    st.markdown(f"**📐 Resolution:** {scorecard.get('dimensions', 'N/A')}")
                    st.markdown(f"**🎯 Quality Score:** {scorecard.get('quality_score', 0)}/10")
                    st.markdown(f"**✅ Compliance Score:** {scorecard.get('compliance_score', 0)}/10")
                    st.markdown(f"**🖼️ Background:** {scorecard.get('background_type', 'Unknown')}")
                    
                    if scorecard.get('visible_text'):
                        st.markdown("**📝 Visible Text:**")
                        for text in scorecard.get('visible_text', [])[:5]:
                            st.markdown(f"• {text}")
                    
                    if scorecard.get('visible_usps'):
                        st.markdown("**✨ USPs Shown:**")
                        for usp in scorecard.get('visible_usps', []):
                            st.markdown(f"• {usp}")
                    
                    if scorecard.get('ports_connectors'):
                        st.markdown(f"**🔌 Ports/Connectors:** {', '.join(scorecard.get('ports_connectors', []))}")
                    
                    if scorecard.get('quality_issues'):
                        st.markdown("**⚠️ Issues:**")
                        for issue in scorecard.get('quality_issues', []):
                            st.markdown(f"• {issue}")
                
                st.markdown("---")
    
    # Display product images (HIGH RESOLUTION) - simplified view
    if product.get('images'):
        with st.expander("🖼️ Original Product Images (Full Resolution)", expanded=False):
            st.caption("💡 Click on image URLs below to view full resolution")
            num_images = len(product['images'])
            
            # Show images in grid
            cols = st.columns(min(num_images, 4))
            for idx, img_url in enumerate(product['images'][:8]):
                with cols[idx % 4]:
                    try:
                        st.image(img_url, caption=f"Image {idx+1}", use_container_width=True)
                    except:
                        st.markdown(f"[Image {idx+1}]({img_url})")
            
            # Show image URLs for reference
            st.markdown("**🔗 Full Resolution Image URLs:**")
            for idx, img_url in enumerate(product['images']):
                st.markdown(f"[Image {idx+1}: Click to open full resolution]({img_url})")
    
    # Display reviews
    if product.get('reviews'):
        with st.expander("💬 Customer Reviews"):
            for idx, review in enumerate(product['reviews']):
                st.markdown(f"**Review {idx+1}:** {review[:300]}{'...' if len(review) > 300 else ''}")
                st.divider()
    
    # Display full JSON
    with st.expander("🔧 Full Product Data (JSON)"):
        st.json(product)

    st.markdown("---")
    
    # =========================================================
    # DISPLAY AI ANALYSIS (Collapsible for concise view)
    # =========================================================
    if st.session_state.ai_response:
        st.markdown('<p class="section-header">📐 AI Image Strategy Analysis</p>', unsafe_allow_html=True)
        
        # Display in an expander since it's longer - users can expand if they want details
        with st.expander("📋 Full Strategy Report", expanded=True):
            st.markdown(st.session_state.ai_response)
        
        # Download option for the analysis
        col1, col2 = st.columns([1, 3])
        with col1:
            st.download_button(
                label="📥 Download Analysis",
                data=st.session_state.ai_response,
                file_name="image_strategy_analysis.md",
                mime="text/markdown",
                key="download_analysis"
            )

    st.markdown("---")
    
    # =========================================================
    # IMAGE GENERATION SECTION
    # =========================================================
    st.markdown('<p class="section-header">🎨 AI Image Generation Studio</p>', unsafe_allow_html=True)
    
    image_brief = st.session_state.image_brief
    
    if image_brief:
        # Display the brief summary
        with st.expander("📋 Image Brief Pack (JSON)", expanded=False):
            st.json(image_brief)
        
        # Display USP Map
        if image_brief.get("usp_map"):
            with st.expander("🎯 USP Map", expanded=False):
                for usp in image_brief["usp_map"]:
                    risk_emoji = "✅" if usp.get("risk_flag") == "none" else "⚠️" if usp.get("risk_flag") in ["vague", "qc-risk"] else "❌"
                    st.markdown(f"**{usp.get('usp_id', 'USP')}** {risk_emoji}: {usp.get('claim', 'N/A')}")
                    st.caption(f"Visual evidence: {usp.get('visual_evidence_type', 'N/A')} | Buyer intent: {usp.get('buyer_intent', 'N/A')}")
        
        # Display Included Items
        if image_brief.get("included_items"):
            with st.expander("📦 Items to Show in Images", expanded=False):
                for item in image_brief["included_items"]:
                    must_show = "✅ Must show" if item.get("must_show") else "Optional"
                    st.markdown(f"• **{item.get('count', '1')}x {item.get('item', 'Item')}** - {must_show}")
        
        st.markdown("---")
        
        # =========================================================
        # IMAGE GENERATION INTERFACE
        # =========================================================
        st.markdown('<p class="section-header">🖼️ Generate AI Product Images</p>', unsafe_allow_html=True)
        
        st.success("✨ **Ready to Generate!** Select image types below. Your analysis is preserved - generating images won't reset your data!")
        
        # Platform selection for image generation
        gen_platform = st.selectbox(
            "🎯 Generate images for platform:",
            ["Amazon", "Flipkart"],
            key="gen_platform_select"
        )
        
        # Image type selection
        image_types = {
            "hero": "🏆 Image 1 - Hero (Main Product Shot)",
            "contents": "📦 Image 2 - Contents (What's Inside)",
            "benefits": "✨ Image 3 - Benefits & USPs",
            "usage": "📖 Image 4 - How to Use",
            "detail": "🔍 Image 5 - Close-up Details",
            "lifestyle": "👨‍🎓 Image 6 - Lifestyle/Context",
            "trust": "⭐ Image 7 - Trust/Social Proof"
        }
        
        selected_images = st.multiselect(
            "🖼️ Select images to generate:",
            options=list(image_types.keys()),
            format_func=lambda x: image_types[x],
            default=["hero"],
            key="selected_images_multi"
        )
        
        # Show prompts before generation
        if selected_images:
            with st.expander("👀 Preview Generation Prompts", expanded=False):
                for img_type in selected_images:
                    st.markdown(f"**{image_types[img_type]}**")
                    prompt = build_image_gen_prompt(image_brief, img_type, gen_platform.lower())
                    st.text_area(f"Prompt for {img_type}", prompt, height=150, key=f"prompt_prev_{img_type}")
        
        # Generation button
        if st.button("🎨 Generate Selected Images", type="primary", key="gen_images_btn"):
            if not selected_images:
                st.warning("⚠️ Please select at least one image type to generate.")
            elif not user_api_key:
                st.error("❌ Please enter your OpenAI API key.")
            else:
                st.markdown('<p class="section-header">🎨 Generating Images...</p>', unsafe_allow_html=True)
                
                progress_bar = st.progress(0)
                total_images = len(selected_images)
                
                for idx, img_type in enumerate(selected_images):
                    st.markdown(f"### {image_types[img_type]}")
                    
                    with st.spinner(f"🎨 Creating {image_types[img_type]}..."):
                        try:
                            # Build the prompt
                            img_prompt = build_image_gen_prompt(image_brief, img_type, gen_platform.lower())
                            
                            # Generate image
                            img_response = client.images.generate(
                                model="gpt-image-1",
                                prompt=img_prompt,
                                size="1024x1024",
                                n=1
                            )
                            
                            # Update progress
                            progress_bar.progress((idx + 1) / total_images)
                            
                            # Get the image
                            img_bytes = None
                            if hasattr(img_response.data[0], 'b64_json') and img_response.data[0].b64_json:
                                img_bytes = base64.b64decode(img_response.data[0].b64_json)
                            elif hasattr(img_response.data[0], 'url') and img_response.data[0].url:
                                import urllib.request
                                with urllib.request.urlopen(img_response.data[0].url) as response:
                                    img_bytes = response.read()
                            
                            if img_bytes:
                                image = Image.open(BytesIO(img_bytes))
                                
                                # Display the image
                                st.image(image, caption=f"{gen_platform} - {image_types[img_type]}", use_container_width=True)
                                
                                # Store in session state
                                st.session_state.generated_images[f"{gen_platform}_{img_type}"] = img_bytes
                                
                                # Download button
                                st.download_button(
                                    label=f"📥 Download {img_type.capitalize()} Image",
                                    data=img_bytes,
                                    file_name=f"{gen_platform.lower()}_{img_type}_image.png",
                                    mime="image/png",
                                    key=f"dl_{gen_platform}_{img_type}_{time.time()}"
                                )
                                
                                # Show the prompt used
                                with st.expander(f"🔧 Prompt used for {img_type}"):
                                    st.code(img_prompt)
                            else:
                                st.error(f"No image data returned for {img_type}")
                            
                            st.markdown("---")
                            
                        except Exception as e:
                            st.error(f"Failed to generate {img_type}: {str(e)}")
                            with st.expander("Error details"):
                                st.code(str(e))
                
                st.success(f"✅ Image generation complete! All {len(selected_images)} images generated successfully.")
                st.balloons()
        
        # Show previously generated images
        if st.session_state.generated_images:
            st.markdown("---")
            st.markdown('<p class="section-header">📁 Generated Images Gallery</p>', unsafe_allow_html=True)
            
            # Display in grid
            img_keys = list(st.session_state.generated_images.keys())
            cols = st.columns(min(len(img_keys), 3))
            
            for idx, key in enumerate(img_keys):
                with cols[idx % 3]:
                    img_bytes = st.session_state.generated_images[key]
                    image = Image.open(BytesIO(img_bytes))
                    st.image(image, caption=key.replace("_", " ").title(), use_container_width=True)
                    st.download_button(
                        label=f"📥 Download",
                        data=img_bytes,
                        file_name=f"{key}.png",
                        mime="image/png",
                        key=f"dl_prev_{key}"
                    )
    
    else:
        st.warning("⚠️ Could not generate Image Brief. You can still use the analysis above for manual image creation.")
    
    # Reset button
    st.markdown("---")
    st.markdown("### 🔄 Start Fresh")
    if st.button("🗑️ Clear All & Start New Analysis", key="reset_btn"):
        st.session_state.product = None
        st.session_state.ai_response = None
        st.session_state.image_brief = None
        st.session_state.generated_images = {}
        st.session_state.analysis_done = False
        st.session_state.image_scorecards = []
        st.session_state.quick_summary = None
        st.rerun()

else:
    # Welcome screen when no analysis done yet
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; padding: 3rem 1rem;">
        <h2 style="color: #1e3c72;">👋 Welcome to Ecom Image SEO</h2>
        <p style="color: #6c757d; font-size: 1.1rem; max-width: 600px; margin: 1rem auto;">
            Transform your product listings with AI-powered image strategy. 
            Get detailed analysis and generate optimized product images for Amazon & Flipkart.
        </p>
        <br>
        <div style="display: flex; justify-content: center; gap: 2rem; flex-wrap: wrap;">
            <div style="background: #f8f9fa; padding: 1.5rem; border-radius: 12px; min-width: 200px;">
                <p style="font-size: 2rem; margin: 0;">🔑</p>
                <p style="font-weight: 600; margin: 0.5rem 0;">Step 1</p>
                <p style="color: #6c757d; margin: 0; font-size: 0.9rem;">Enter OpenAI API Key</p>
            </div>
            <div style="background: #f8f9fa; padding: 1.5rem; border-radius: 12px; min-width: 200px;">
                <p style="font-size: 2rem; margin: 0;">📥</p>
                <p style="font-weight: 600; margin: 0.5rem 0;">Step 2</p>
                <p style="color: #6c757d; margin: 0; font-size: 0.9rem;">Provide Product Details</p>
            </div>
            <div style="background: #f8f9fa; padding: 1.5rem; border-radius: 12px; min-width: 200px;">
                <p style="font-size: 2rem; margin: 0;">🎯</p>
                <p style="font-weight: 600; margin: 0.5rem 0;">Step 3</p>
                <p style="color: #6c757d; margin: 0; font-size: 0.9rem;">Generate Image Strategy</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# -------------------------------------------------
# FOOTER
# -------------------------------------------------
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #6c757d; padding: 1rem;">
    <p style="margin: 0; font-size: 0.85rem;">
        🛒 <strong>Ecom Image SEO</strong> | Built with ❤️ by <strong>Vishal Tiwari (PW17633)</strong> | Project Head: <strong>Kumar Sanskar</strong>
    </p>
    <p style="margin: 0.3rem 0 0 0; font-size: 0.75rem; color: #adb5bd;">
        Powered by OpenAI GPT-4o & DALL-E | © 2025 All Rights Reserved
    </p>
</div>
""", unsafe_allow_html=True)
