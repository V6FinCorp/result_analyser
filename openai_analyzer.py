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

def analyze_with_openai(pdf_path, api_key, max_pages=10):
    """
    Analyzes a financial PDF using OpenAI GPT-4 Vision API.
    
    Args:
        pdf_path: Path to the PDF file
        api_key: OpenAI API key (provided by user, not stored)
        max_pages: Maximum number of pages to send to OpenAI (default: 10)
                   Higher = more accurate but more expensive
                   Options: 5, 10, 15, 20
    
    Returns:
        Dictionary with analysis results matching the frontend format
    """
    logger.info(f"Starting OpenAI analysis for: {pdf_path}")
    
    try:
        # Initialize OpenAI client
        client = OpenAI(api_key=api_key)
        
        # Open PDF
        logger.info(f"Opening PDF for smart page selection: {pdf_path}")
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
        
        # Sort by score descending and pick top N pages based on max_pages
        page_scores.sort(key=lambda x: x[0], reverse=True)
        selected_pages = [idx for score, idx in page_scores[:max_pages]]
        
        # If no pages scored, fallback to first N pages (half of max_pages)
        if not selected_pages:
            fallback_count = max(5, max_pages // 2)
            logger.warning(f"No relevant pages found via keyword scan. Falling back to first {fallback_count} pages.")
            selected_pages = list(range(min(fallback_count, len(doc))))
        else:
            # Sort selected pages by their original order
            selected_pages.sort()
            logger.info(f"Smart selection picked {len(selected_pages)} pages: {[p+1 for p in selected_pages]} (max_pages={max_pages})")

        # 2. Convert selected pages to images
        image_data_urls = []
        for page_num in selected_pages:
            page = doc[page_num]
            # Use 120 DPI to balance quality and payload size
            mat = fitz.Matrix(120/72, 120/72) 
            pix = page.get_pixmap(matrix=mat)
            
            # Convert to PIL Image
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            
            # Resize if still too large
            if img.width > 1600 or img.height > 1600:
                img.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
            
            # Convert to base64 using JPEG
            buffered = BytesIO()
            img.save(buffered, format="JPEG", quality=80)
            img_str = base64.b64encode(buffered.getvalue()).decode()
            image_data_urls.append(f"data:image/jpeg;base64,{img_str}")
            
            logger.info(f"Processed and encoded page {page_num + 1}")
            
            # Explicitly clear memory
            del pix
            del img
        
        doc.close()
        logger.info(f"Successfully encoded {len(image_data_urls)} pages for AI analysis")
        
        # Construct the prompt
        prompt = """You are a financial analyst. Analyze the attached quarterly results PDF and provide a comprehensive analysis.

CRITICAL INSTRUCTIONS:
1. If both "Consolidated" and "Standalone" results are present, ONLY analyze the CONSOLIDATED results.
2. Look for the main financial results table (usually titled "Statement of Profit and Loss" or similar).
3. All figures should be in ₹ Crores (Indian Rupees in Crores). If the PDF shows figures in Lakhs, divide them by 100 to get Crores.

 Extract the following data for FOUR periods (Current Quarter, Previous Quarter, Same Quarter Last Year, and Year Ended):
- company_id: Scrip code (numeric) from Page 1.
- company_code: Symbol (text) from Page 1.
- quarter: Q1, Q2, Q3, or Q4.
- year: 4-digit year.
- result_type: Consolidated or Standalone.
- Metrics for EACH of the 4 periods: Revenue, Other Income, Total Expenses, Operating Profit, OPM %, PBT, Net Profit, EPS.

Also, scan for Corporate Actions:
- Dividend: Numeric value.
- Capex: Amount in Lakhs.
- Management Change: "Yes" or "No".
- Special Announcement: Text summary.

Calculate Growth Metrics:
- revenue_qoq, net_profit_qoq, revenue_yoy, net_profit_yoy.

IMPORTANT: Return ONLY valid JSON in this exact format. Ensure "table_data" has exactly 4 entries matching the periods:
{
  "company_id": "513699",
  "company_code": "EICHERMOT",
  "quarter": "Q2", 
  "year": 2025,
  "result_type": "Consolidated",
  "table_data": [
    {"period": "Current", "revenue": 100.0, "other_income": 5.0, "total_expenses": 80.0, "operating_profit": 20.0, "opm": 20.0, "pbt": 25.0, "net_profit": 18.0, "eps": 2.5},
    {"period": "Prev Qtr", "revenue": 90.0, ...},
    {"period": "YoY Qtr", "revenue": 85.0, ...},
    {"period": "Year Ended", "revenue": 400.0, ...}
  ],
  "growth": {
    "revenue_qoq": 11.1, "net_profit_qoq": 5.2, "revenue_yoy": 17.6, "net_profit_yoy": 12.1
  },
  "corporate_actions": {
    "dividend": "4.5", "capex": "5000", "management_change": "Yes", "special_announcement": "..."
  },
  "observations": [ ... ],
  "recommendation": { "verdict": "...", "color": "...", "reasons": [...] }
}

If you cannot find certain data, use "Not mentioned" for corporate actions and 0 for numeric values. Ensure all numeric values are numbers (not strings).
"""
        
        # Prepare messages with images
        content = [{"type": "text", "text": prompt}]
        for img_url in image_data_urls:
            content.append({
                "type": "image_url",
                "image_url": {"url": img_url, "detail": "high"}
            })
        
        logger.info("Sending request to OpenAI GPT-4 Vision API...")
        
        # Call OpenAI API with JSON mode
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": content}],
            response_format={"type": "json_object"},  # Force JSON output
            max_tokens=2000,
            temperature=0.1
        )
        
        # Extract response
        result_text = response.choices[0].message.content.strip()
        logger.info(f"Received response from OpenAI (length: {len(result_text)} chars)")
        
        # Parse JSON (response_format ensures it's already JSON, no need to strip markdown)
        try:
            analysis = json.loads(result_text)
            logger.info("Successfully parsed JSON response")
            return analysis
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse OpenAI response as JSON: {e}")
            logger.error(f"Response text (first 1000 chars): {result_text[:1000]}")
            return {
                "error": "Failed to parse AI response. The model may have returned invalid JSON.",
                "details": str(e),
                "raw_response": result_text[:500]
            }
        
    except Exception as e:
        logger.error(f"Error during OpenAI analysis: {e}")
        return {"error": str(e)}
