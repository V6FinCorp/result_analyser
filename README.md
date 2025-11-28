# Result Analyser

A Flask-based web application for analyzing financial PDF documents.

## Setup

### Quick Setup (Windows)
Run the setup script to install all dependencies:
```powershell
.\setup.ps1
```

### Manual Setup
1. Install Python dependencies:
```powershell
pip install -r requirements.txt
```

2. Install Playwright browsers:
```powershell
playwright install chromium
```

## Running the Application

```powershell
python .\app.py
```

The application will be available at: http://127.0.0.1:5001

## Features

- Upload PDF files for analysis
- Download and analyze PDFs from URLs
- Extract financial data from documents
- Generate recommendations based on financial data
