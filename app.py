from flask import Flask, render_template, request, jsonify
import os
from werkzeug.utils import secure_filename
from analyzer import extract_financial_data
from browser_utils import download_pdf_from_url

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
    
    # Handle File Upload
    if 'file' in request.files and request.files['file'].filename != '':
        file = request.files['file']
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
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
        data = extract_financial_data(file_path)
        if not data:
            return jsonify({'error': 'Could not extract financial data from the PDF'}), 400
            
        # Data now contains table_data, growth, observations, and recommendation
        return jsonify(data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5001)
