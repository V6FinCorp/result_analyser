from flask import Flask, render_template, request, jsonify
import os
from werkzeug.utils import secure_filename
from analyzer import extract_financial_data
from browser_utils import download_pdf_from_url
from database_utils import upsert_analysis_data

import logging

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['DOWNLOAD_FOLDER'] = 'downloads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max limit

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['DOWNLOAD_FOLDER'], exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/favicon.ico')
def favicon():
    return '', 204

def is_high_confidence(data):
    """
    Evaluates if local extraction results are reliable enough.
    Returns True if confident, False if AI fallback is recommended.
    """
    if not data or 'error' in data:
        logger.info("❌ Confidence Check: Data has errors")
        return False
    
    table_data = data.get('table_data', [])
    if not table_data:
        logger.info("❌ Confidence Check: No table data found")
        return False
    
    current = table_data[0]
    
    # Check 1: Revenue must be positive
    if current.get('revenue', 0) <= 0:
        logger.info("❌ Confidence Check: Revenue is zero or negative")
        return False
    
    # Check 2: At least one profit metric should exist
    if current.get('net_profit') == 0 and current.get('pbt') == 0:
        logger.info("❌ Confidence Check: No profit data found")
        return False
    
    # Check 3: Should have multi-period data for comparison
    if len(table_data) < 2:
        logger.info("⚠️ Confidence Check: Only single period found (acceptable but not ideal)")
        # Don't fail on this - single period is still useful
    
    # Check 4: Operating profit should be calculated
    if current.get('operating_profit') == 0 and current.get('revenue', 0) > 0:
        logger.info("⚠️ Confidence Check: Operating profit calculation seems off")
        # Don't fail - might be legitimate zero
    
    logger.info("✅ Confidence Check: All critical metrics present - HIGH CONFIDENCE")
    return True

@app.route('/analyze', methods=['POST'])
def analyze():
    file_path = None
    api_key = None
    
    # Get Processing Mode
    processing_mode = request.form.get('processing_mode', 'smart')  # Default to smart mode
    
    # Get AI page limit (for AI and smart modes)
    ai_page_limit = int(request.form.get('ai_page_limit', 10))
    
    # Get API key from form (required for AI and smart modes)
    if processing_mode in ['ai', 'smart']:
        if 'api_key' in request.form:
            api_key = request.form['api_key'].strip()
        
        if not api_key:
            return jsonify({'error': 'OpenAI API key is required for AI and Smart modes.'}), 400
        
        if not api_key.startswith('sk-'):
            return jsonify({'error': 'Invalid API key format. OpenAI keys start with "sk-"'}), 400
    
    # Handle File Upload
    if 'file' in request.files and request.files['file'].filename != '':
        file = request.files['file']
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        logger.info(f"File uploaded: {filename}")
        
    # Handle URL Input
    elif 'url' in request.form and request.form['url'] != '':
        url = request.form['url']
        file_path = download_pdf_from_url(url, app.config['DOWNLOAD_FOLDER'])
        if not file_path:
            return jsonify({'error': 'Failed to download PDF from URL'}), 400
            
    else:
        return jsonify({'error': 'No file or URL provided'}), 400
    
    # Process the PDF
    try:
        if processing_mode == 'smart':
            # SMART MODE: Try local first, fallback to AI if needed
            logger.info("🧠 Starting SMART mode - trying local extraction first...")
            local_data = extract_financial_data(file_path)
            
            if is_high_confidence(local_data):
                logger.info("✅ Local extraction successful - using local results (COST: $0)")
                local_data['processing_method'] = 'Local'
                local_data['cost_saved'] = True
                return jsonify(local_data)
            else:
                logger.warning("⚠️ Low confidence in local results - falling back to AI...")
                from openai_analyzer import analyze_with_openai
                ai_data = analyze_with_openai(file_path, api_key, max_pages=ai_page_limit)
                ai_data['processing_method'] = 'AI (Fallback)'
                ai_data['cost_saved'] = False
                ai_data['fallback_reason'] = 'Local extraction had low confidence'
                logger.info("✅ AI analysis completed successfully")
                return jsonify(ai_data)
                
        elif processing_mode == 'ai':
            # AI MODE: Direct AI analysis
            from openai_analyzer import analyze_with_openai
            logger.info(f"🤖 Starting AI-based analysis (max {ai_page_limit} pages)...")
            data = analyze_with_openai(file_path, api_key, max_pages=ai_page_limit)
            data['processing_method'] = 'AI'
            data['cost_saved'] = False
            
        else:  # local mode
            # LOCAL MODE: Only local extraction
            logger.info("⚡ Starting Local-based analysis...")
            data = extract_financial_data(file_path)
            data['processing_method'] = 'Local'
            data['cost_saved'] = True
        
        # Check for errors in the response
        if not data or 'error' in data:
            error_msg = data.get('error', 'Unknown error during extraction')
            logger.error(f"Analysis error: {error_msg}")
            return jsonify({'error': error_msg}), 400
            
        # --- NEW: Save to Database ---
        try:
            db_success = upsert_analysis_data(data)
            data['saved_to_db'] = db_success
            if db_success:
                logger.info("Data successfully stored in database")
            else:
                logger.warning("Data extraction worked, but database storage failed")
        except Exception as db_err:
            logger.error(f"Database trigger error: {db_err}")
            data['saved_to_db'] = False

        logger.info("Analysis completed successfully")
        return jsonify(data)
        
    except Exception as e:
        logger.error(f"Error during analysis: {e}", exc_info=True)
        error_msg = str(e)
        
        # Provide user-friendly error messages
        if 'invalid_api_key' in error_msg.lower() or 'incorrect api key' in error_msg.lower():
            return jsonify({'error': 'Invalid OpenAI API key. Please check your key and try again.'}), 401
        elif 'rate_limit' in error_msg.lower():
            return jsonify({'error': 'OpenAI rate limit exceeded. Please wait a moment and try again.'}), 429
        elif 'insufficient_quota' in error_msg.lower():
            return jsonify({'error': 'Insufficient OpenAI credits. Please add credits to your account.'}), 402
        else:
            return jsonify({'error': f'Analysis failed: {error_msg}'}), 500

@app.errorhandler(Exception)
def handle_exception(e):
    logger.error(f"Unhandled Exception: {e}", exc_info=True)
    return jsonify({'error': f"Server Error: {str(e)}"}), 500

if __name__ == '__main__':
    # Set use_reloader=False if you experience connection resets during development
    app.run(debug=True, port=5001, use_reloader=False)
