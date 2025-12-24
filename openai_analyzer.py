import logging
import base64
import json
from io import BytesIO
from openai import OpenAI
import fitz  # PyMuPDF
import logging
import base64
import json
from io import BytesIO
from openai import OpenAI
import fitz  # PyMuPDF
from PIL import Image

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def analyze_with_openai(pdf_path, api_key, max_pages=10, include_corp_actions=False, include_observations=False, include_recommendations=False):
    """
    Analyzes a financial PDF using OpenAI GPT-4 Vision API.
    """
    debug_logs = []
    def log(msg):
        logger.info(msg)
        debug_logs.append(msg)

    log(f"🚀 Starting OpenAI analysis for: {pdf_path}")
    
    try:
        # Initialize OpenAI client
        client = OpenAI(api_key=api_key)
        
        # Open PDF
        log(f"📂 Opening PDF for smart page selection: {pdf_path}")
        doc = fitz.open(pdf_path)
        
        # 1. Smart Page Selection Logic
        page_scores = []
        for i, page in enumerate(doc):
            text = page.get_text().lower()
            score = 0
            
            # Keywords that indicate a financial results table
            if any(k in text for k in ["revenue from operations", "net profit", "total income", "total expenses"]):
                score += 50
            if any(k in text for k in ["statement of", "financial results", "profit and loss"]):
                score += 30
            if "quarter ended" in text or "year ended" in text:
                score += 20
                
            # CRITICAL: Prioritize Consolidated
            if "consolidated" in text:
                score += 100
            elif "standalone" in text:
                score += 10 # Lower priority but still a table
                
            if score > 0:
                page_scores.append((score, i))
                log(f"🔍 Page {i+1}: Identified as potential results (Score: {score})")
        
        # Sort by score descending and pick top N pages based on max_pages
        page_scores.sort(key=lambda x: x[0], reverse=True)
        
        # For table extraction, we usually only need 1-3 pages. 
        # If we need corporate actions, we might need more.
        limit = 3 if not include_corp_actions else max_pages
        selected_pages = [idx for score, idx in page_scores[:limit]]
        
        # If no pages scored, fallback to first 2 pages
        if not selected_pages:
            log(f"⚠️ No relevant pages found via keyword scan. Falling back to first 2 pages.")
            selected_pages = list(range(min(2, len(doc))))
        else:
            # Sort selected pages by their original order
            selected_pages.sort()
            log(f"✅ Smart selection picked {len(selected_pages)} pages for AI: {[p+1 for p in selected_pages]}")

        # 2. Convert selected pages to images
        image_data_urls = []
        for page_num in selected_pages:
            page = doc[page_num]
            mat = fitz.Matrix(150/72, 150/72) # Higher DPI for better table reading
            pix = page.get_pixmap(matrix=mat)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            if img.width > 2000 or img.height > 2000:
                img.thumbnail((2000, 2000), Image.Resampling.LANCZOS)
            buffered = BytesIO()
            img.save(buffered, format="JPEG", quality=85)
            img_str = base64.b64encode(buffered.getvalue()).decode()
            image_data_urls.append(f"data:image/jpeg;base64,{img_str}")
            log(f"📸 Encoded Page {page_num + 1} for AI analysis")
            del pix
            del img
        
        doc.close()
        
        # Construct the prompt
        # ... (prompt construction same as before)
        optional_instructions = ""
        if include_corp_actions:
            optional_instructions += """
- Scan for Corporate Actions: Dividend (numeric), Capex (Amount in Lakhs), Management Change ("Yes" or "No"), Special Announcement (text)."""
        
        if include_observations:
            optional_instructions += "\n- Provide 3-5 Key Observations about the financial performance."
            
        if include_recommendations:
            optional_instructions += "\n- Provide a Recommendation (verdict, color, reasons) based on the results."

        prompt = f"""You are a professional financial data extractor. Analyze the attached quarterly results PDF.

CRITICAL INSTRUCTIONS:
1. If both "Consolidated" and "Standalone" results are present, ONLY extract the CONSOLIDATED results.
2. Focus on the main financial results table.
3. All figures should be in ₹ Crores. If the PDF shows figures in Lakhs, divide them by 100.
4. Extract data for FOUR periods: Current Quarter, Previous Quarter, Same Quarter Last Year (YoY Qtr), and Year Ended.

Extract the following:
- company_id: Scrip code (numeric) from Page 1.
- company_code: Symbol (text) from Page 1.
- quarter: Q1, Q2, Q3, or Q4.
- year: 4-digit year.
- result_type: Consolidated or Standalone.
- Metrics for EACH of the 4 periods: Revenue, Other Income, Total Expenses, Operating Profit, OPM %, PBT, Net Profit, EPS.{optional_instructions}

Calculate Growth Metrics (QoQ and YoY) for: Revenue, Operating Profit, PBT, Net Profit, and EPS.

IMPORTANT: Return ONLY valid JSON in this exact format:
{{
  "company_id": "513699",
  "company_code": "EICHERMOT",
  "quarter": "Q2", 
  "year": 2025,
  "result_type": "Consolidated",
  "table_data": [
    {{"period": "Current", "revenue": 100.0, "other_income": 5.0, "total_expenses": 80.0, "operating_profit": 20.0, "opm": 20.0, "pbt": 25.0, "net_profit": 18.0, "eps": 2.5}},
    {{"period": "Prev Qtr", "revenue": 90.0, "other_income": 4.0, "total_expenses": 75.0, "operating_profit": 15.0, "opm": 16.7, "pbt": 20.0, "net_profit": 15.0, "eps": 2.0}},
    {{"period": "YoY Qtr", "revenue": 85.0, "other_income": 3.0, "total_expenses": 70.0, "operating_profit": 15.0, "opm": 17.6, "pbt": 18.0, "net_profit": 14.0, "eps": 1.8}},
    {{"period": "Year Ended", "revenue": 400.0, "other_income": 20.0, "total_expenses": 320.0, "operating_profit": 80.0, "opm": 20.0, "pbt": 100.0, "net_profit": 72.0, "eps": 10.0}}
  ],
  "growth": {{
    "revenue_qoq": 11.1, "revenue_yoy": 17.6, 
    "operating_profit_qoq": 5.0, "operating_profit_yoy": 10.0,
    "pbt_qoq": 4.0, "pbt_yoy": 8.0,
    "net_profit_qoq": 5.2, "net_profit_yoy": 12.1,
    "eps_qoq": 2.0, "eps_yoy": 5.0
  }},
  "corporate_actions": {{ "dividend": "0", "capex": "0", "management_change": "No", "special_announcement": "Not mentioned" }},
  "observations": [],
  "recommendation": {{ "verdict": "Not requested", "color": "gray", "reasons": [] }}
}}
"""
        
        # Prepare messages with images
        content = [{"type": "text", "text": prompt}]
        for img_url in image_data_urls:
            content.append({
                "type": "image_url",
                "image_url": {"url": img_url, "detail": "high"}
            })
        
        log("📡 Sending request to OpenAI GPT-4 Vision API...")
        
        # Call OpenAI API with JSON mode
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": content}],
            response_format={"type": "json_object"},  # Force JSON output
            max_tokens=2000,
            temperature=0
        )
        
        # Extract response
        result_text = response.choices[0].message.content.strip()
        log(f"📥 Received response from OpenAI (length: {len(result_text)} chars)")
        
        # Parse JSON
        try:
            analysis = json.loads(result_text)
            analysis['debug_logs'] = debug_logs
            log("✨ Successfully parsed AI response")
            return analysis
        except json.JSONDecodeError as e:
            log(f"❌ Failed to parse OpenAI response as JSON: {e}")
            return {
                "error": "Failed to parse AI response.",
                "debug_logs": debug_logs
            }
        
    except Exception as e:
        log(f"❌ Error during OpenAI analysis: {e}")
        return {"error": str(e), "debug_logs": debug_logs}

