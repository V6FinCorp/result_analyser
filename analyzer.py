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
import logging

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def extract_financial_data(pdf_path):
    """
    Extracts financial data from a PDF file.
    Returns a dictionary with extracted metrics.
    """
    extracted_data = {}
    logger.info(f"Analyzing PDF: {pdf_path}")
    
    with pdfplumber.open(pdf_path) as pdf:
        # Strategy 1: Smart Table Selection
        # Scan ALL pages and ALL tables, score them, and pick the best one.
        candidates = [] # List of (score, page_idx, table_df)
        
        for i, page in enumerate(pdf.pages):
            logger.info(f"Scanning Page {i+1} for tables...")
            try:
                tables = page.extract_tables(table_settings={
                    "vertical_strategy": "text", 
                    "horizontal_strategy": "text",
                    "snap_tolerance": 5
                })
            except Exception as e:
                logger.warning(f"Failed to extract tables from Page {i+1}: {e}")
                continue
            
            for table in tables:
                df = pd.DataFrame(table).fillna('')
                # Clean up
                df = df.dropna(how='all').dropna(axis=1, how='all')
                
                score = score_table(df, page_idx=i+1)
                if score > 10: # Lower threshold to capture more candidates
                    candidates.append((score, i+1, df))
                    logger.info(f"Found candidate table on Page {i+1} with Score: {score}")

        # Sort candidates by score (descending)
        candidates.sort(key=lambda x: x[0], reverse=True)
        
        logger.info(f"Found {len(candidates)} candidate tables. Processing in order of score...")
        
        for score, page_idx, df in candidates:
            logger.info(f"Attempting to process table from Page {page_idx} (Score: {score})")
            data = process_financial_table(df)
            if data and data.get('table_data') and data['table_data'][0].get('revenue', 0) > 0:
                logger.info(f"Successfully extracted data from Page {page_idx}.")
                return data
            else:
                logger.warning(f"Table from Page {page_idx} failed processing or had zero revenue.")

        # Strategy 2: Text-Based Extraction (Fallback)
        logger.warning("Table extraction failed or yielded no data. Attempting text-based extraction...")
        full_text = ""
        for page in pdf.pages:
            full_text += page.extract_text() + "\n"
            
        data = extract_from_text(full_text)
        if data and data.get('revenue', 0) > 0:
            logger.info("Successfully extracted data from text.")
            wrapped_data = {
                'table_data': [{'period': 'Current', **data}],
                'growth': {},
                'observations': ["⚠️ Extracted from text. Comparison data unavailable."],
                'recommendation': generate_recommendation(data, [])
            }
            return wrapped_data

    logger.error("No valid financial data found.")
    return extracted_data

def score_table(df, page_idx=0):
    """
    Scores a dataframe based on its likelihood of being the Financial Results table.
    """
    score = 0
    df_str = df.astype(str).apply(lambda x: x.str.lower())
    text_content = " ".join(df_str.values.flatten())
    
    # CRITICAL: Prioritize Consolidated over Standalone
    if 'consolidated' in text_content:
        score += 50
        logger.info(f"Page {page_idx}: CONSOLIDATED results detected (+50 bonus)")
    elif 'standalone' in text_content:
        score -= 20
        logger.info(f"Page {page_idx}: Standalone results detected (-20 penalty)")
    
    # Keyword Scoring
    keywords = {
        'revenue': 10, 'sales': 10, 'income from operations': 15,
        'profit': 10, 'loss': 10, 'net profit': 20,
        'expenses': 10, 'expenditure': 10,
        'tax': 5, 'eps': 10, 'earnings per share': 15,
        'quarter': 5, 'ended': 5
    }
    
    for kw, points in keywords.items():
        if kw in text_content:
            score += points
            
    # Structure Scoring
    # 1. Must have multiple columns (Particulars + Data)
    if df.shape[1] < 2:
        return 0
        
    # 2. Numeric Density: Check if columns 1+ contain mostly numbers
    numeric_cols = 0
    for col in df.columns[1:]:
        numeric_count = 0
        total_count = 0
        for val in df[col]:
            val_str = str(val).strip()
            if not val_str: continue
            total_count += 1
            # Check if it looks like a number (allow commas, brackets)
            clean = val_str.replace(',', '').replace('(', '').replace(')', '')
            try:
                float(clean)
                numeric_count += 1
            except: pass
            
        if total_count > 0 and (numeric_count / total_count) > 0.4:
            numeric_cols += 1
            
    if numeric_cols > 0:
        score += (numeric_cols * 5)
    else:
        score -= 20
        
    return score

def process_financial_table(df):
    """Process dataframe to extract metrics for multiple periods."""
    df = df.astype(str)
    
    # Identify Particulars Column
    particulars_col_idx = -1
    for i, col in enumerate(df.columns):
        col_text = " ".join(df[col].astype(str)).lower()
        # Added 'particulars' to be more robust based on user screenshot
        if 'particulars' in col_text or 'revenue' in col_text or 'profit' in col_text or 'expenses' in col_text:
            particulars_col_idx = i
            break
            
    if particulars_col_idx == -1:
        lengths = df.apply(lambda x: x.str.len().mean())
        particulars_col_idx = lengths.idxmax()

    # Identify Data Columns (All columns with >3 numbers, excluding Sr No)
    data_col_indices = []
    for i, col in enumerate(df.columns):
        if i == particulars_col_idx: continue
        
        numeric_values = []
        for val in df[col]:
            lines = str(val).split('\n')
            for line in lines:
                clean = line.replace(',', '').replace('(', '-').replace(')', '').strip()
                try:
                    val_float = float(clean)
                    numeric_values.append(val_float)
                except: pass
        
        if len(numeric_values) > 3:
            # Heuristic to filter out Sr No column:
            # If max value is small (< 50) and all are integers, it's likely an index
            if max(numeric_values) < 50 and all(v.is_integer() for v in numeric_values):
                continue
            data_col_indices.append(i)
            
    if not data_col_indices: return None

    logger.info(f"Using Particulars Col: {particulars_col_idx}, Data Cols: {data_col_indices}")

    # Helper to find value in a specific column
    def find_val(keywords, col_idx):
        for _, row in df.iterrows():
            cell_text = str(row[particulars_col_idx])
            lines = cell_text.split('\n')
            
            match_line_idx = -1
            for idx, line in enumerate(lines):
                if any(k.lower() in line.lower() for k in keywords):
                    match_line_idx = idx
                    break
            
            if match_line_idx != -1:
                val_cell = str(row[col_idx])
                val_lines = val_cell.split('\n')
                val_lines = [l.strip() for l in val_lines if l.strip()]
                
                if not val_lines: continue
                if len(lines) == 0: continue
                
                ratio = len(val_lines) / len(lines)
                target_idx = math.floor(match_line_idx * ratio)
                target_idx = min(target_idx, len(val_lines) - 1)
                target_idx = max(target_idx, 0)
                
                val_str = val_lines[target_idx]
                try:
                    clean_val = val_str.replace(',', '').replace('(', '-').replace(')', '').strip()
                    return float(clean_val)
                except: continue
        return 0.0

    # Extract for all identified columns (up to 4: Current, Prev, YoY, YearEnd)
    periods = ['Current', 'Prev Qtr', 'YoY Qtr', 'Year Ended']
    extracted_results = []
    
    for i, col_idx in enumerate(data_col_indices[:4]):
        period_name = periods[i] if i < len(periods) else f"Period {i+1}"
        
        revenue = find_val(['Revenue from Operations', 'Income from Operations', 'Total Revenue'], col_idx)
        if revenue < 1.0: revenue = find_val(['Total Income'], col_idx)
        
        other_income = find_val(['Other Income'], col_idx)
        total_expenses = find_val(['Total Expenses', 'Total Expenditure'], col_idx)
        pbt = find_val(['Profit before Tax', 'Profit / (Loss) before Tax', 'Profit Before Exceptional'], col_idx)
        net_profit = find_val(['Net Profit', 'Profit for the period', 'Profit after Tax', 'Profit / (Loss) for the period', 'Profi/'], col_idx)
        eps = find_val(['Earnings Per Share', 'EPS', 'Basic'], col_idx)
        
        operating_profit = revenue - total_expenses
        opm = (operating_profit / revenue * 100) if revenue > 0 else 0
        
        extracted_results.append({
            'period': period_name,
            'revenue': revenue,
            'other_income': other_income,
            'total_expenses': total_expenses,
            'operating_profit': operating_profit,
            'opm': opm,
            'pbt': pbt,
            'net_profit': net_profit,
            'eps': eps
        })

    return analyze_results(extracted_results)

def analyze_results(results):
    """Analyze the extracted multi-period data to generate insights."""
    if not results: return {}
    
    current = results[0]
    prev = results[1] if len(results) > 1 else None
    yoy = results[2] if len(results) > 2 else None
    
    # Growth Calculation
    growth = {}
    if prev:
        growth['revenue_qoq'] = ((current['revenue'] - prev['revenue']) / prev['revenue'] * 100) if prev['revenue'] else 0
        growth['net_profit_qoq'] = ((current['net_profit'] - prev['net_profit']) / prev['net_profit'] * 100) if prev['net_profit'] else 0
    
    if yoy:
        growth['revenue_yoy'] = ((current['revenue'] - yoy['revenue']) / yoy['revenue'] * 100) if yoy['revenue'] else 0
        growth['net_profit_yoy'] = ((current['net_profit'] - yoy['net_profit']) / yoy['net_profit'] * 100) if yoy['net_profit'] else 0
        
    # Generate Observations
    observations = []
    
    # 1. Operating Profit Check
    if current['operating_profit'] < 0:
        observations.append(f"🚨 **CRITICAL RED FLAG: Operating Loss** of {current['operating_profit']:.2f} Lakhs. Core business is bleeding.")
    
    # 2. OPM Check
    if current['opm'] < 0:
        observations.append(f"⚠️ **Margin Collapse:** Operating Profit Margin (OPM) is negative at {current['opm']:.1f}%.")
    elif yoy and current['opm'] < yoy['opm']:
        observations.append(f"⚠️ **Margin Compression:** OPM fell to {current['opm']:.1f}% from {yoy['opm']:.1f}% YoY.")
        
    # 3. Other Income Dependency
    if current['net_profit'] > 0 and current['operating_profit'] < 0:
        observations.append(f"⚠️ **Masked Earnings:** Net Profit is positive only due to Other Income ({current['other_income']:.2f}).")
        
    # 4. Revenue Growth
    if growth.get('revenue_qoq', 0) < -10:
        observations.append(f"📉 **Revenue Collapse:** Revenue crashed {growth['revenue_qoq']:.1f}% QoQ.")
        
    # 5. Expense Check
    if yoy and current['total_expenses'] > yoy['total_expenses'] and current['revenue'] < yoy['revenue']:
        observations.append("⚠️ **Expense Mismanagement:** Expenses increased YoY while Revenue declined.")

    return {
        'table_data': results,
        'growth': growth,
        'observations': observations,
        'recommendation': generate_recommendation(current, observations)
    }

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

def generate_recommendation(data, observations):
    """Generates investment recommendation based on data and observations."""
    score = 0
    reasons = []
    
    # Negative scoring based on critical observations
    for obs in observations:
        if "CRITICAL" in obs: score -= 5
        if "Margin" in obs: score -= 2
        if "Masked" in obs: score -= 3
        if "Collapse" in obs: score -= 2
        
    # Base Financials
    if data['net_profit'] > 0: score += 1
    if data['operating_profit'] > 0: score += 2
    
    if score >= 2:
        verdict = "BUY / ACCUMULATE"
        color = "green"
    elif score > -3:
        verdict = "HOLD / NEUTRAL"
        color = "orange"
    else:
        verdict = "STRONG AVOID / SELL"
        color = "red"
        
    return {'verdict': verdict, 'color': color, 'reasons': observations}
