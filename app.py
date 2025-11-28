from flask import Flask, render_template, request, jsonify
import os
from werkzeug.utils import secure_filename
from analyzer import extract_financial_data
from browser_utils import download_pdf_from_url

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

@app.route('/analyze', methods=['POST'])
def analyze():
    file_path = None
    api_key = None
    
    # Get API key from form
    if 'api_key' in request.form:
        api_key = request.form['api_key'].strip()
    
    if not api_key:
        return jsonify({'error': 'OpenAI API key is required. Please enter your API key.'}), 400
    
    # Validate API key format
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
    
    # Process the PDF using OpenAI
    try:
        from openai_analyzer import analyze_with_openai
        
        logger.info("Starting OpenAI-based analysis...")
        data = analyze_with_openai(file_path, api_key)
        
        # Check for errors in the response
        if 'error' in data:
            logger.error(f"OpenAI analysis error: {data['error']}")
            return jsonify({'error': data['error']}), 400
            
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

if __name__ == '__main__':
    app.run(debug=True, port=5001)
