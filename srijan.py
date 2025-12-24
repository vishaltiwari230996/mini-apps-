# app.py - FIXED VERSION
# Complete working version with Part 1 (original) and Part 2 (redesigned)

import os
import time
import json
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

import streamlit as st
import pandas as pd
from PIL import Image
import fitz  # PyMuPDF
import pytesseract
from openai import OpenAI

HIGH_CONFIDENCE_THRESHOLD = 0.95

# =============================
# CONFIGURATION
# =============================

class OperationMode(Enum):
    """Operation modes for Part 2"""
    GENERATE_FROM_TEXT = "generate_from_text"
    TRANSFORM_FROM_JSON = "transform_from_json"

# Configure Tesseract
if os.name == 'nt':
    possible_paths = [
        r"C:\Users\vishal tiwari\AppData\Local\Programs\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"
    ]
    for path in possible_paths:
        if os.path.exists(path):
            pytesseract.pytesseract.tesseract_cmd = path
            break

def build_openai_client(user_api_key: str | None) -> OpenAI | None:
    """Build OpenAI client"""
    api_key = user_api_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        st.error("Please provide an OpenAI API key to run extraction.")
        return None
    return OpenAI(api_key=api_key)

# =============================
# PROMPT TEMPLATES
# =============================

ENGINE_A_PROMPT = """
You are an expert exam question parser for competitive exams like NEET and JEE.

You will receive raw OCR text from a SINGLE PAGE of a PDF that contains questions,
options, answers, and sometimes solutions/explanations.

Your task:
1. Identify individual questions present ONLY on this page.
2. For each question, extract and structure as JSON with these keys:
   - "id": integer index starting from 1 for THIS PAGE
   - "question": full question stem as single string
   - "options": list of strings (["A. ...", "B. ...", ...])
   - "answer": correct answer if available, else null
   - "explanation": solution if available, else null
   - "page": integer page number
   - "has_figure": boolean (true if refers to diagram/figure)
   - "confidence": float 0-1 (certainty of OCR quality)

Rules:
- Return STRICTLY valid JSON array: [ { ... }, { ... }, ... ]
- No extra commentary
- Merge multi-line questions into single string
- Normalize options format
- Ignore headers/footers
""".strip()

ENGINE_B_PROMPT = ENGINE_A_PROMPT

GENERATION_PROMPT = """
You are an expert exam question generator for competitive exams like NEET and JEE.

You will receive study material text. Generate 3-5 high-quality MCQs based on the content.

For each question, provide JSON with:
- "id": integer starting from 1
- "question": question text
- "options": list of 4 options
- "answer": correct option label (A/B/C/D)
- "explanation": detailed explanation
- "page": page number provided
- "has_figure": false (usually)
- "confidence": 1.0

Rules:
- Return STRICTLY valid JSON array
- No extra commentary
- Ensure relevance to input text
""".strip()

TRANSFORMATION_PROMPT = """
You are an expert at transforming exam questions.

Transform questions according to user instructions while maintaining JSON structure.

Rules:
- Return STRICTLY valid JSON array
- Maintain structure (id, question, options, answer, explanation, page, has_figure, confidence)
- No extra commentary
""".strip()

# =============================
# UTILITY FUNCTIONS
# =============================

def _clean_model_output(content: str) -> str:
    """Clean model output artifacts"""
    content = content.strip()
    if content.startswith("```json"):
        content = content[7:]
    if content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]
    return content.strip()

def parse_questions_from_json(content: str) -> List[Dict]:
    """Parse and validate questions from JSON"""
    cleaned = _clean_model_output(content)
    questions = json.loads(cleaned)
    if not isinstance(questions, list):
        raise ValueError("Expected JSON array of questions")
    return questions

# =============================
# UI COMPONENTS (REUSABLE)
# =============================

class QuestionPreview:
    """Handles question rendering"""
    
    @staticmethod
    def render_single_question(question: Dict, index: int = None):
        """Render single question"""
        if index is not None:
            st.markdown(f"**Question {index}:**")
        
        st.markdown(f"**Q:** {question.get('question', '')}")
        
        if question.get("options"):
            st.markdown("**Options:**")
            for opt in question["options"]:
                st.write(f"  {opt}")
        
        if question.get("answer"):
            st.success(f"**Answer:** {question['answer']}")
        
        if question.get("explanation"):
            st.info(f"**Explanation:** {question['explanation']}")
    
    @staticmethod
    def render_question_list(questions: List[Dict], max_preview: int = 10):
        """Render list of questions"""
        preview_count = min(len(questions), max_preview)
        
        for i in range(preview_count):
            q = questions[i]
            preview_text = q.get('question', '')[:80]
            
            with st.expander(f"Q{i+1}: {preview_text}..."):
                QuestionPreview.render_single_question(q)
        
        if len(questions) > max_preview:
            st.info(f"Showing first {max_preview} of {len(questions)} questions.")

class DownloadButton:
    """Handles downloads"""
    
    @staticmethod
    def create_json_download(data: List[Dict], filename: str, label: str = "⬇️ Download JSON"):
        """Create JSON download button"""
        json_str = json.dumps(data, ensure_ascii=False, indent=2)
        st.download_button(
            label=label,
            data=json_str,
            file_name=filename,
            mime="application/json",
        )

# =============================
# CORE PROCESSING CLASSES
# =============================

class QuestionGenerator:
    """Generates questions from text"""
    
    def __init__(self, client: OpenAI, model_name: str):
        self.client = client
        self.model_name = model_name
    
    def generate(self, text: str, custom_prompt: Optional[str] = None) -> List[Dict]:
        """Generate questions using OpenAI"""
        prompt = custom_prompt or GENERATION_PROMPT
        
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"Generate questions from:\n\n{text}"},
            ],
            temperature=0.3,
        )
        
        content = response.choices[0].message.content.strip()
        return parse_questions_from_json(content)

class QuestionTransformer:
    """Transforms existing questions"""
    
    def __init__(self, client: OpenAI, model_name: str):
        self.client = client
        self.model_name = model_name
    
    def transform(
        self, 
        questions: List[Dict], 
        instruction: str,
        custom_prompt: Optional[str] = None
    ) -> List[Dict]:
        """Transform questions per instruction"""
        prompt = custom_prompt or TRANSFORMATION_PROMPT
        questions_json = json.dumps(questions, ensure_ascii=False, indent=2)
        
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"Instruction: {instruction}\n\nQuestions:\n{questions_json}"},
            ],
            temperature=0.3,
        )
        
        content = response.choices[0].message.content.strip()
        return parse_questions_from_json(content)

# =============================
# OCR FUNCTIONS (PART 1)
# =============================

def pdf_to_images(pdf_bytes: bytes, dpi: int = 300) -> List[Image.Image]:
    """Convert PDF to images"""
    pages: List[Image.Image] = []
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    zoom = dpi / 72
    mat = fitz.Matrix(zoom, zoom)

    for page in doc:
        pix = page.get_pixmap(matrix=mat)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        pages.append(img)

    doc.close()
    return pages

def ocr_image_to_text(img: Image.Image) -> str:
    """OCR image to text"""
    return pytesseract.image_to_string(img, lang="eng")

def extract_questions_from_page(
    client: OpenAI,
    ocr_text: str,
    page_num: int,
    system_prompt: str,
    model_name: str = "gpt-4o-mini"
) -> Tuple[List[Dict], str, float]:
    """Extract questions from page using OpenAI"""
    user_msg = f"[Page {page_num}]\n\n{ocr_text}"
    
    start_time = time.time()
    resp = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.3,
    )
    elapsed = time.time() - start_time
    
    content = resp.choices[0].message.content.strip()
    content = _clean_model_output(content)
    
    try:
        questions = json.loads(content)
        return questions, content, elapsed
    except json.JSONDecodeError:
        return [], content, elapsed

# =============================
# PART 2 UI FLOWS (REDESIGNED)
# =============================

class GenerateFromTextFlow:
    """Generate questions from text"""
    
    def __init__(self, client: OpenAI, model_name: str):
        self.generator = QuestionGenerator(client, model_name)
    
    def render(self):
        """Render generation UI"""
        st.subheader("✍️ Generate Questions from Text")
        
        # Custom prompt (optional)
        use_custom = st.checkbox("Use custom generation prompt", value=False)
        if use_custom:
            custom_prompt = st.text_area(
                "Custom Generation Prompt",
                value=GENERATION_PROMPT,
                height=200
            )
        else:
            custom_prompt = GENERATION_PROMPT
        
        # Text input
        user_text = st.text_area(
            "Paste study material or theory text",
            height=200,
            placeholder="Enter educational content here..."
        )
        
        # Generate button
        if st.button("🚀 Generate Questions", type="primary"):
            if not user_text.strip():
                st.warning("Please enter some text first.")
                return
            
            self._execute_generation(user_text, custom_prompt)
    
    def _execute_generation(self, text: str, prompt: str):
        """Execute generation"""
        with st.spinner("Generating questions..."):
            try:
                questions = self.generator.generate(text, prompt)
                
                st.success(f"✅ Generated {len(questions)} questions!")
                
                # Preview first question
                if questions:
                    st.markdown("### Preview of First Question:")
                    QuestionPreview.render_single_question(questions[0])
                    st.divider()
                
                # Show all questions
                st.markdown("### All Generated Questions:")
                QuestionPreview.render_question_list(questions)
                
                # Download
                DownloadButton.create_json_download(
                    questions,
                    "generated_questions.json",
                    "⬇️ Download Generated Questions"
                )
                
            except json.JSONDecodeError:
                st.error("Failed to parse AI response. Try simplifying your input.")
            except Exception as e:
                st.error(f"Error: {str(e)}")

class TransformFromJSONFlow:
    """Transform questions from JSON"""
    
    def __init__(self, client: OpenAI, model_name: str):
        self.transformer = QuestionTransformer(client, model_name)
    
    def render(self):
        """Render transformation UI"""
        st.subheader("📁 Transform Questions from JSON")
        
        # File upload
        uploaded_json = st.file_uploader(
            "Upload JSON with questions",
            type=["json"],
            help="From extraction or previous generation"
        )
        
        if uploaded_json is None:
            st.info("👆 Upload a JSON file to get started")
            return
        
        questions = self._load_questions(uploaded_json)
        if questions is None:
            return
        
        # Display loaded questions
        self._display_loaded_questions(questions)
        
        # Transformation interface
        self._render_transformation_interface(questions)
    
    def _load_questions(self, file) -> Optional[List[Dict]]:
        """Load questions from file"""
        try:
            questions = json.load(file)
            
            if not isinstance(questions, list):
                st.error("Invalid JSON. Expected array of questions.")
                return None
            
            st.success(f"✅ Loaded {len(questions)} questions!")
            return questions
            
        except json.JSONDecodeError:
            st.error("Invalid JSON file.")
            return None
        except Exception as e:
            st.error(f"Error loading file: {str(e)}")
            return None
    
    def _display_loaded_questions(self, questions: List[Dict]):
        """Display preview"""
        st.markdown("### 📋 Questions Preview")
        QuestionPreview.render_question_list(questions, max_preview=10)
        st.divider()
    
    def _render_transformation_interface(self, questions: List[Dict]):
        """Render transformation controls"""
        st.markdown("### 🔄 Transform Questions")
        
        # Custom prompt (optional)
        use_custom = st.checkbox("Use custom transformation prompt", value=False)
        if use_custom:
            custom_prompt = st.text_area(
                "Custom Transformation Prompt",
                value=TRANSFORMATION_PROMPT,
                height=150
            )
        else:
            custom_prompt = None
        
        # Transformation instruction
        col1, col2 = st.columns([3, 1])
        
        with col1:
            user_instruction = st.text_input(
                "What do you want to do?",
                placeholder="e.g., 'Make harder', 'Translate to Hindi', 'Add explanations'"
            )
        
        with col2:
            st.write("")
            st.write("")
            transform_btn = st.button("🔄 Transform", type="primary", use_container_width=True)
        
        # Quick templates
        with st.expander("💡 Quick Templates"):
            templates = {
                "Make Harder": "Increase difficulty with complex options",
                "Simplify": "Make easier with simpler language",
                "Add Explanations": "Add detailed explanations to all",
                "Hindi Translation": "Translate everything to Hindi",
                "Create Variations": "Create 2-3 variations per question",
                "Add Distractors": "Improve wrong options",
            }
            
            selected = st.selectbox("Choose template", ["Custom"] + list(templates.keys()))
            
            if selected != "Custom":
                st.code(templates[selected])
        
        # Execute transformation
        if transform_btn:
            if not user_instruction.strip():
                st.error("Please enter an instruction or select a template.")
                return
            
            self._execute_transformation(questions, user_instruction, custom_prompt)
    
    def _execute_transformation(
        self, 
        questions: List[Dict], 
        instruction: str,
        custom_prompt: Optional[str]
    ):
        """Execute transformation"""
        with st.spinner(f"Transforming {len(questions)} questions..."):
            try:
                transformed = self.transformer.transform(questions, instruction, custom_prompt)
                
                st.success(f"✅ Transformed {len(transformed)} questions!")
                
                # Comparison
                st.markdown("### 📊 Transformation Results")
                
                if transformed:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("**Original:**")
                        QuestionPreview.render_single_question(questions[0])
                    
                    with col2:
                        st.markdown("**Transformed:**")
                        QuestionPreview.render_single_question(transformed[0])
                
                st.divider()
                
                # All transformed
                st.markdown("### All Transformed Questions:")
                QuestionPreview.render_question_list(transformed)
                
                # Download
                DownloadButton.create_json_download(
                    transformed,
                    "transformed_questions.json",
                    "⬇️ Download Transformed Questions"
                )
                
            except json.JSONDecodeError:
                st.error("Failed to parse AI response. Try simpler instruction.")
            except Exception as e:
                st.error(f"Error: {str(e)}")

# =============================
# MAIN APPLICATION
# =============================

def main():
    st.set_page_config(
        page_title="Question Engine MVP",
        page_icon="📚",
        layout="wide"
    )
    
    st.title("📚 Exam Question Extraction & Generation Engine")
    st.markdown("Upload PDFs to extract questions or generate new ones")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        api_key_input = st.text_input(
            "OpenAI API Key",
            type="password",
            help="Enter API key or set OPENAI_API_KEY env var"
        )
        
        model_name = st.selectbox(
            "Model",
            options=["gpt-4o-mini", "gpt-4o", "gpt-4-turbo"],
            index=0
        )
        
        st.divider()
        st.markdown("### 📖 Guide")
        st.markdown("""
        **Part 1: Extract from PDF**
        - Upload PDF with questions
        - OCR + AI extraction
        
        **Part 2: Generate/Transform**
        - Generate from text
        - Transform existing questions
        """)
    
    # Main tabs
    tab1, tab2 = st.tabs(["📄 Part 1: Extract from PDF", "🎯 Part 2: Generate/Transform"])
    
    # =============================
    # PART 1: PDF EXTRACTION (ORIGINAL)
    # =============================
    with tab1:
        st.header("Part 1: Extract Questions from PDF")
        st.info("Upload a PDF containing exam questions. OCR + AI extraction.")
        
        uploaded_file = st.file_uploader(
            "Choose a PDF file",
            type=["pdf"],
            help="Upload PDF with exam questions"
        )
        
        if uploaded_file is not None:
            client = build_openai_client(api_key_input)
            if client is None:
                st.stop()
            
            engine_choice = st.radio(
                "Extraction Engine",
                ["Engine A (Default)", "Engine B (Alternative)"],
                horizontal=True
            )
            
            system_prompt = ENGINE_A_PROMPT if "Engine A" in engine_choice else ENGINE_B_PROMPT
            
            if st.button("🚀 Extract Questions", type="primary"):
                with st.spinner("Processing PDF..."):
                    try:
                        pdf_bytes = uploaded_file.read()
                        images = pdf_to_images(pdf_bytes)
                        
                        st.info(f"Converted to {len(images)} images. Running OCR...")
                        
                        all_questions = []
                        progress_bar = st.progress(0)
                        
                        for idx, img in enumerate(images):
                            ocr_text = ocr_image_to_text(img)
                            
                            questions, _, elapsed = extract_questions_from_page(
                                client, ocr_text, idx + 1, system_prompt, model_name
                            )
                            
                            all_questions.extend(questions)
                            progress_bar.progress((idx + 1) / len(images))
                        
                        st.success(f"✅ Extracted {len(all_questions)} questions from {len(images)} pages!")
                        
                        # Preview
                        if all_questions:
                            st.markdown("### Preview:")
                            QuestionPreview.render_question_list(all_questions[:5], max_preview=5)
                        
                        # Download
                        DownloadButton.create_json_download(
                            all_questions,
                            "extracted_questions.json",
                            "⬇️ Download Extracted Questions"
                        )
                        
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
    
    # =============================
    # PART 2: GENERATE/TRANSFORM (REDESIGNED)
    # =============================
    with tab2:
        st.header("Part 2: Generate or Transform Questions")
        
        # Build client
        client = build_openai_client(api_key_input)
        if client is None:
            st.warning("⚠️ Please provide OpenAI API key in sidebar.")
            st.stop()
        
        # Mode selection - Simple and clear
        operation_mode = st.radio(
            "Choose Operation Mode",
            options=["Generate from Text", "Transform from JSON"],
            horizontal=True,
            help="Generate creates new questions from text. Transform modifies existing questions."
        )
        
        st.divider()
        
        # Render appropriate flow
        if operation_mode == "Generate from Text":
            flow = GenerateFromTextFlow(client, model_name)
            flow.render()
        else:  # Transform from JSON
            flow = TransformFromJSONFlow(client, model_name)
            flow.render()

if __name__ == "__main__":
    main()
