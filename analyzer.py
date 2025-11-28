import pdfplumber
import re
import pandas as pd
import math

def extract_financial_data(pdf_path):
    """
    Extracts financial data from a PDF file.
    Returns a dictionary with extracted metrics.
    """
    extracted_data = {}
    
    with pdfplumber.open(pdf_path) as pdf:
        print(f"Analyzing PDF: {pdf_path}")
        
        # Strategy 1: Table Extraction with Text Strategy (Robust for this PDF)
        for i, page in enumerate(pdf.pages):
            # Use text strategy to handle complex layouts/interleaving
            tables = page.extract_tables(table_settings={
                "vertical_strategy": "text", 
                "horizontal_strategy": "text",
                "snap_tolerance": 5
            })
            
            for table in tables:
                df = pd.DataFrame(table).fillna('')
                
                # Clean up
                df = df.dropna(how='all').dropna(axis=1, how='all')
                
                # Check for financial keywords in the raw table (multiline)
                df_str = df.astype(str)
                row_text = df_str.apply(lambda x: ' '.join(x), axis=1).str.lower()
                
                if row_text.str.contains('revenue|sales|income from operations').any() and \
                   row_text.str.contains('profit|loss').any():
                    print(f"Page {i+1}: Found Financial Table via Text Strategy")
                    data = process_financial_table(df)
                    if data and data.get('revenue', 0) > 0:
                        return data

        # Strategy 2: Text-Based Extraction (Fallback)
        print("Table extraction failed. Attempting text-based extraction...")
        full_text = ""
        for page in pdf.pages:
            full_text += page.extract_text() + "\n"
            
        data = extract_from_text(full_text)
        if data and data.get('revenue', 0) > 0:
            print("Successfully extracted data from text.")
            return data

    print("No valid financial data found.")
    return extracted_data

def process_financial_table(df):
    """Process dataframe to extract metrics."""
    df = df.astype(str)
    
    # Find data column (first column with >3 numbers)
    # Note: Cells are multiline, so we need to check content
    data_col_idx = -1
    for col in df.columns[1:]:
        numeric_count = 0
        for val in df[col]:
            # Check if any line in the cell is a number
            lines = str(val).split('\n')
            for line in lines:
                clean = line.replace(',', '').replace('(', '-').replace(')', '').strip()
                try:
                    float(clean)
                    numeric_count += 1
                except: pass
        if numeric_count > 3:
            data_col_idx = col
            break
            
    # Identify Particulars Column (contains keywords)
    particulars_col_idx = -1
    for i, col in enumerate(df.columns):
        col_text = " ".join(df[col].astype(str)).lower()
        if 'revenue' in col_text or 'profit' in col_text or 'expenses' in col_text:
            particulars_col_idx = i
            break
            
    if particulars_col_idx == -1:
        # Fallback: Use column 0 or 1 depending on content length
        # Usually Particulars is the widest text column
        lengths = df.apply(lambda x: x.str.len().mean())
        particulars_col_idx = lengths.idxmax()

    print(f"Using Column {data_col_idx} for Data and Column {particulars_col_idx} for Particulars")

    def find_val(keywords):
        for _, row in df.iterrows():
            # Check Particulars column
            cell_text = str(row[particulars_col_idx])
            lines = cell_text.split('\n')
            
            # Find which line matches the keyword
            match_line_idx = -1
            for idx, line in enumerate(lines):
                if any(k.lower() in line.lower() for k in keywords):
                    match_line_idx = idx
                    break
            
            if match_line_idx != -1:
                # Found keyword at line `match_line_idx`
                print(f"DEBUG: Found keyword '{keywords[0]}' at line {match_line_idx} in text: {lines[match_line_idx]}")
                
                # Get value cell
                val_cell = str(row[data_col_idx])
                val_lines = val_cell.split('\n')
                val_lines = [l.strip() for l in val_lines if l.strip()] # Remove empty lines
                
                print(f"DEBUG: Value lines: {val_lines}")
                
                if not val_lines: continue
                
                # Proportional Mapping
                # value_index = floor( text_index * (len(value) / len(text)) )
                # We use len(lines) as text length
                
                if len(lines) == 0: continue
                
                # Calculate target index
                ratio = len(val_lines) / len(lines)
                target_idx = math.floor(match_line_idx * ratio)
                
                # Clamp index
                target_idx = min(target_idx, len(val_lines) - 1)
                target_idx = max(target_idx, 0)
                
                val_str = val_lines[target_idx]
                print(f"DEBUG: Mapped to index {target_idx}, value: {val_str}")
                
                try:
                    clean_val = val_str.replace(',', '').replace('(', '-').replace(')', '').strip()
                    return float(clean_val)
                except: continue
                
        return 0.0

    return calculate_metrics(find_val)

def extract_from_text(text):
    """Parse raw text to find financial metrics."""
    lines = text.split('\n')
    
    def find_val_in_text(keywords):
        for line in lines:
            if any(k.lower() in line.lower() for k in keywords):
                matches = re.findall(r'(?<!\d)\(?\d{1,3}(?:,\d{3})*\.?\d*\)?(?!\d)', line)
                valid_numbers = []
                for match in matches:
                    try:
                        clean = match.replace(',', '').replace('(', '-').replace(')', '')
                        val = float(clean)
                        if len(valid_numbers) == 0 and val < 20 and val.is_integer(): continue
                        valid_numbers.append(val)
                    except: continue
                
                if len(valid_numbers) >= 2:
                    return valid_numbers[0]
        return 0.0

    return calculate_metrics(find_val_in_text)

def calculate_metrics(finder_func):
    """Common logic to calculate metrics using a finder function."""
    revenue = finder_func(['Revenue from Operations', 'Income from Operations', 'Total Revenue'])
    if revenue < 1.0: revenue = finder_func(['Total Income'])
    
    other_income = finder_func(['Other Income'])
    total_expenses = finder_func(['Total Expenses', 'Total Expenditure'])
    pbt = finder_func(['Profit before Tax', 'Profit / (Loss) before Tax', 'Profit Before Exceptional'])
    
    # Added 'Profi/' to handle typo in PDF
    net_profit = finder_func(['Net Profit', 'Profit for the period', 'Profit after Tax', 'Profit / (Loss) for the period', 'Profi/'])
    
    eps = finder_func(['Earnings Per Share', 'EPS', 'Basic'])
    
    operating_profit = revenue - total_expenses
    opm = (operating_profit / revenue * 100) if revenue > 0 else 0
    
    return {
        'revenue': revenue,
        'other_income': other_income,
        'total_expenses': total_expenses,
        'operating_profit': operating_profit,
        'opm': opm,
        'pbt': pbt,
        'net_profit': net_profit,
        'eps': eps
    }

def generate_recommendation(data):
    """Generates investment recommendation."""
    reasons = []
    score = 0
    
    if data['operating_profit'] < 0:
        reasons.append(f"CRITICAL: Operating Loss of {data['operating_profit']:.2f}")
        score -= 5
    elif data['opm'] < 10:
        reasons.append(f"Warning: Low Operating Margin ({data['opm']:.1f}%)")
        score -= 1
    else:
        score += 2
        
    if data['net_profit'] < 0:
        reasons.append("CRITICAL: Net Loss reported.")
        score -= 5
    elif data['net_profit'] > 0 and data['operating_profit'] < 0:
        reasons.append("Warning: Profit driven by Other Income, not Core Ops.")
        score -= 3
        
    if score >= 2:
        verdict = "BUY / ACCUMULATE"
        color = "green"
    elif score > -2:
        verdict = "HOLD / NEUTRAL"
        color = "orange"
    else:
        verdict = "AVOID / SELL"
        color = "red"
        
    return {'verdict': verdict, 'color': color, 'reasons': reasons}
