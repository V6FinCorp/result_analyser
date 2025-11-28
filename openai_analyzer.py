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

def analyze_with_openai(pdf_path, api_key):
    """
    Analyzes a financial PDF using OpenAI GPT-4 Vision API.
    
    Args:
        pdf_path: Path to the PDF file
        api_key: OpenAI API key (provided by user, not stored)
    
    Returns:
        Dictionary with analysis results matching the frontend format
    """
    logger.info(f"Starting OpenAI analysis for: {pdf_path}")
    
    try:
        # Initialize OpenAI client
        client = OpenAI(api_key=api_key)
        
        # Convert PDF to images using PyMuPDF (first 5 pages)
        logger.info("Converting PDF pages to images using PyMuPDF...")
        doc = fitz.open(pdf_path)
        images = []
        
        for page_num in range(min(5, len(doc))):  # First 5 pages
            page = doc[page_num]
            # Render page to image (matrix for 150 DPI)
            mat = fitz.Matrix(150/72, 150/72)  # 150 DPI
            pix = page.get_pixmap(matrix=mat)
            
            # Convert to PIL Image
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            images.append(img)
        
        doc.close()
        logger.info(f"Converted {len(images)} pages to images")
        
        # Encode images to base64
        image_data_urls = []
        for i, img in enumerate(images):
            # Resize if too large (OpenAI has size limits)
            if img.width > 2000 or img.height > 2000:
                img.thumbnail((2000, 2000), Image.Resampling.LANCZOS)
            
            # Convert to base64
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            image_data_urls.append(f"data:image/png;base64,{img_str}")
            logger.info(f"Encoded page {i+1}")
        
        # Construct the prompt
        prompt = """You are a financial analyst. Analyze the attached quarterly results PDF and provide a comprehensive analysis.

CRITICAL INSTRUCTIONS:
1. If both "Consolidated" and "Standalone" results are present, ONLY analyze the CONSOLIDATED results.
2. Look for the main financial results table (usually titled "Statement of Profit and Loss" or similar).
3. All figures should be in ₹ Lakhs (Indian Rupees in Lakhs).

Extract the following data:
- Revenue from Operations
- Other Income
- Total Expenses
- Operating Profit (Revenue from Operations - Total Expenses)
- OPM % (Operating Profit / Revenue from Operations * 100)
- Profit Before Tax
- Net Profit
- EPS (Earnings Per Share)

For each metric, extract values for up to 4 periods (if available):
- Current Quarter (most recent quarter)
- Previous Quarter (sequential quarter before current)
- Year-over-Year Quarter (same quarter last year)
- Year Ended (full year audited results)

Calculate Growth Metrics:
- QoQ Growth % for Revenue and Net Profit: ((Current - Previous) / Previous * 100)
- YoY Growth % for Revenue and Net Profit: ((Current - YoY Quarter) / YoY Quarter * 100)

Generate Key Observations (use emojis for visual impact):
- 🚨 If Operating Profit is negative, flag as "CRITICAL RED FLAG: Operating Loss"
- ⚠️ If OPM is negative or declining significantly, flag as "Margin Collapse" or "Margin Compression"
- 📉 If Revenue dropped >10% QoQ or YoY, flag as "Revenue Collapse"
- ⚠️ If Expenses increased while Revenue declined, flag as "Expense Mismanagement"

Provide Investment Recommendation:
- Verdict: "BUY / ACCUMULATE", "HOLD / NEUTRAL", or "STRONG AVOID / SELL"
- Color: "green", "orange", or "red"
- Reasons: List of key observations

IMPORTANT: Return ONLY valid JSON in this exact format (no markdown, no code blocks, just raw JSON):
{
  "table_data": [
    {"period": "Current", "revenue": 295.16, "other_income": 138.41, "total_expenses": 381.43, "operating_profit": -86.27, "opm": -29.2, "pbt": 52.14, "net_profit": 39.02, "eps": 0.26},
    {"period": "Prev Qtr", "revenue": 478.61, "other_income": 2.12, "total_expenses": 418.84, "operating_profit": 59.77, "opm": 12.5, "pbt": 61.89, "net_profit": 46.31, "eps": 0.31},
    {"period": "YoY Qtr", "revenue": 306.57, "other_income": 1.06, "total_expenses": 235.82, "operating_profit": 70.75, "opm": 23.1, "pbt": 71.81, "net_profit": 53.74, "eps": 0.44},
    {"period": "Year Ended", "revenue": 1445.26, "other_income": 61.33, "total_expenses": 1385.27, "operating_profit": 59.99, "opm": 4.2, "pbt": 121.32, "net_profit": 88.52, "eps": 0.72}
  ],
  "growth": {
    "revenue_qoq": -38.3,
    "net_profit_qoq": -15.7,
    "revenue_yoy": -3.7,
    "net_profit_yoy": -27.4
  },
  "observations": [
    "🚨 CRITICAL RED FLAG: Operating Loss of -86.27 Lakhs. Core business is bleeding.",
    "⚠️ Margin Collapse: Operating Profit Margin (OPM) is negative at -29.2%.",
    "📉 Revenue Collapse: Revenue crashed -38.3% QoQ."
  ],
  "recommendation": {
    "verdict": "STRONG AVOID / SELL",
    "color": "red",
    "reasons": ["Operating Loss", "Margin Collapse", "Revenue Decline"]
  }
}

If you cannot find certain data, use 0 as the value. Ensure all numeric values are numbers (not strings).
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
