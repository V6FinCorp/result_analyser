import pdfplumber
import pandas as pd
import re
import math
import logging
from pathlib import Path

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def normalize(s):
    return re.sub(r'[^a-z0-9]', '', s.lower())

class LocalAnalyzer:
    def __init__(self, pdf_path, include_corp_actions=False, include_observations=False, include_recommendations=False):
        self.path = pdf_path
        self.include_corp_actions = include_corp_actions
        self.include_observations = include_observations
        self.include_recommendations = include_recommendations
        self.target = "Consolidated"
        self.periods = ["Current", "Prev Qtr", "YoY Qtr", "Year Ended"]
        self.results = { p: {
            "revenue": 0.0, "other_income": 0.0, "total_expenses": 0.0, 
            "operating_profit": 0.0, "opm": 0.0, "pbt": 0.0, "net_profit": 0.0, "eps": 0.0
        } for p in self.periods }
        
        self.found_priority = {p: {k: 99 for k in self.results[p].keys()} for p in self.periods}
        self.helpers = {p: {"Dep": 0.0, "Int": 0.0, "Other": 0.0, "TotalInc": 0.0} for p in self.periods}
        self.debug_logs = []

    def log(self, msg):
        logger.info(msg)
        self.debug_logs.append(msg)

    def get_rows(self, page):
        words = page.extract_words(x_tolerance=2, y_tolerance=2)
        if not words: return []
        rows = {}
        for w in words:
            y = round(w['top'], 0)
            found = False
            for ry in rows.keys():
                if abs(y - ry) < 5: rows[ry].append(w); found = True; break
            if not found: rows[y] = [w]
        
        res = []
        for y in sorted(rows.keys()):
            r_words = sorted(rows[y], key=lambda x: x['x0'])
            parts = []
            if r_words:
                c_txt, c_x0, c_x1 = r_words[0]['text'], r_words[0]['x0'], r_words[0]['x1']
                for i in range(1, len(r_words)):
                    w = r_words[i]
                    if (w['x0'] - c_x1) < 4: c_txt += w['text']; c_x1 = w['x1']
                    else: parts.append((c_txt, c_x0)); c_txt, c_x0, c_x1 = w['text'], w['x0'], w['x1']
                parts.append((c_txt, c_x0))
            res.append(parts)
        return res

    def parse_val(self, s):
        if s is None: return None
        s = str(s).replace(',', '').replace('(', '-').replace(')', '').replace("'", '').strip()
        if not re.search(r'\d', s): return None
        if s.count('.') > 1:
            idx = s.rfind('.')
            s = s[:idx].replace('.', '') + s[idx:]
        try:
            m = re.search(r'-?\d+\.?\d*', s)
            return float(m.group()) if m else None
        except: return None

    def analyze(self):
        self.log(f"🔍 Analyzing: {Path(self.path).name}")
        with pdfplumber.open(self.path) as pdf:
            first_page_text = pdf.pages[0].extract_text() or ""
            txt_all = "".join([p.extract_text() or "" for p in pdf.pages[:min(12, len(pdf.pages))]]).lower()
            self.target = "Consolidated" if "consolidated" in txt_all else "Standalone"
            self.log(f"🎯 Target Result Type: {self.target}")
            
            # Global Scale Filter
            global_scale = 1.0
            if "crore" in txt_all: 
                global_scale = 1.0
                self.log("📏 Global Scale: Crores (No conversion)")
            elif any(x in txt_all for x in ["lakh", "lac", "lacs"]): 
                global_scale = 100.0
                self.log("📏 Global Scale: Lakhs (Will divide by 100)")
            
            mapping = {
                "revenue": [("revenuefromoperations", 1), ("incomefromoperations", 2), ("netsales", 3)],
                "TotalInc": [("totalincome", 1), ("totalrevenue", 1)],
                "total_expenses": [("totalexpenses", 1), ("totalexpenditure", 2)],
                "pbt": [("profitbeforetax", 1), ("profitlossbeforetax", 2), ("pbt", 3), ("profitbeforeexceptional", 4)],
                "net_profit": [("netprofit", 1), ("profitfortheperiod", 1), ("profitaftertax", 3), ("profitfortheyear", 1), ("profi", 5)],
                "eps": [("basicearningspershare", 1), ("basiceps", 1), ("earningpershare", 2), ("basic", 3)],
                "Dep": [("depreciation", 1)], 
                "Int": [("financecost", 1), ("interestcost", 1)], 
                "other_income": [("otherincome", 1)]
            }

            best_pages = []
            for i, page in enumerate(pdf.pages):
                text = page.extract_text()
                if not text: continue
                txt = text.lower()
                score = 0
                if "ended" in txt: score += 50
                if "particulars" in txt: score += 50
                if self.target.lower() in txt: score += 100
                if score >= 100:
                    best_pages.append((i, page))

            if not best_pages:
                self.log("⚠️ No high-confidence result pages found.")
            
            for page_idx, page in best_pages:
                self.log(f"📄 Processing Page {page_idx + 1}...")
                txt = page.extract_text().lower()
                is_con = "consolidated" in txt
                prio = 1 if is_con else (2 if "standalone" in txt else 3)
                
                # Page-specific scale override
                page_scale = global_scale
                scale_area = re.search(r'in\s*(lakh|lac|crore|million|rs|rupee)', txt)
                if scale_area:
                    skw = scale_area.group(1)
                    if "crore" in skw: page_scale = 1.0
                    elif "lakh" in skw or "lac" in skw: page_scale = 100.0
                
                rows = self.get_rows(page)
                self.log(f"📊 Found {len(rows)} text rows on page.")
                
                for r in rows:
                    nums = []
                    for t, x in r:
                        v = self.parse_val(t)
                        if v is not None: nums.append((v, x))
                    
                    if not nums: continue
                    
                    r_str = " ".join([p[0] for p in r])
                    match = re.search(r'-?\d', r_str)
                    lbl_text = r_str[:match.start()] if match else r_str
                    lbl = normalize(lbl_text)
                    
                    target_key = None
                    for k, kws in mapping.items():
                        for kw, rk in kws:
                            if normalize(kw) in lbl:
                                if k == "Int" and "income" in lbl: continue
                                if k == "net_profit" and any(x in lbl for x in ["comprehensive", "minority", "equity"]): continue
                                target_key = k; break
                        if target_key: break
                    
                    if target_key:
                        self.log(f"✅ Found Metric: {target_key} (Labels: '{lbl_text.strip()}')")
                        for i, (val, x) in enumerate(nums[:4]):
                            p_name = self.periods[i]
                            # Normalization: If Lakhs -> Crores (div 100). If EPS -> No conversion.
                            divisor = 1.0 if (target_key == "eps" or page_scale == 1.0) else 100.0
                            s_val = round(val / divisor, 2)
                            
                            if target_key in ["Dep", "Int", "TotalInc"]:
                                if self.helpers[p_name][target_key] == 0: 
                                    self.helpers[p_name][target_key] = s_val
                            else:
                                curr_prio = self.found_priority[p_name].get(target_key, 99)
                                if prio < curr_prio or (prio == curr_prio and self.results[p_name][target_key] == 0):
                                    self.results[p_name][target_key] = s_val
                                    self.found_priority[p_name][target_key] = prio
                                    self.log(f"   ∟ {p_name}: {s_val} Cr")

            # Post-processing
            self.log("🔧 Finalizing calculations...")
            for p in self.periods:
                if self.results[p]["revenue"] == 0 and self.helpers[p]["TotalInc"] != 0:
                    self.results[p]["revenue"] = round(self.helpers[p]["TotalInc"] - self.results[p]["other_income"], 2)
                
                if self.results[p]["operating_profit"] == 0 and self.results[p]["revenue"] != 0:
                    self.results[p]["operating_profit"] = round(
                        self.results[p]["pbt"] + self.helpers[p]["Dep"] + self.helpers[p]["Int"] - self.results[p]["other_income"], 2
                    )
                
                if self.results[p]["revenue"] != 0:
                    self.results[p]["opm"] = round((self.results[p]["operating_profit"] / self.results[p]["revenue"]) * 100, 2)

            table_data = []
            for p in self.periods:
                row = self.results[p]
                row['period'] = p
                table_data.append(row)

            full_text = ""
            for p in pdf.pages: full_text += (p.extract_text() or "") + "\n"
            
            ids = extract_identifiers_and_period(full_text, first_page_text)
            self.log(f"🆔 Company ID: {ids['company_id']} | Code: {ids['company_code']}")
            
            actions = extract_corporate_actions(full_text) if self.include_corp_actions else {}
            output = analyze_results(table_data, self.include_observations, self.include_recommendations)
            output.update(ids)
            output['corporate_actions'] = actions
            output['debug_logs'] = self.debug_logs
            output['result_type'] = self.target
            
            return output

def extract_financial_data(pdf_path, **kwargs):
    analyzer = LocalAnalyzer(pdf_path, **kwargs)
    return analyzer.analyze()

def extract_corporate_actions(text):
    actions = {"dividend": "Not mentioned", "capex": "Not mentioned", "management_change": "No", "special_announcement": "Not mentioned"}
    lines = text.split('\n')
    for line in lines:
        l = line.lower()
        if any(k in l for k in ['dividend', 'declared']):
            m = re.findall(r'\d+(?:\.\d+)?', line)
            if m: actions['dividend'] = ", ".join(m)
        if any(k in l for k in ['capex', 'capital expenditure', 'expansion']):
            m = re.findall(r'\d+(?:,\d+)*(?:\.\d+)?', line)
            if m: actions['capex'] = max([float(x.replace(',', '')) for x in m])
        if any(k in l for k in ['appointment', 'resignation', 'ceo', 'cfo', 'director']):
            actions['management_change'] = "Yes"
    return actions

def extract_identifiers_and_period(text, first_page_text):
    res = {"company_id": None, "company_code": None, "quarter": "Q1", "year": 2025}
    m = re.search(r"(?:Scrip code no:|Security Code:|Scrip code:)\s*(\d{6})", first_page_text, re.I)
    if m: res["company_id"] = m.group(1)
    m = re.search(r"(?:Symbol:|NSE Symbol :|NSE CODE:)\s*([A-Z0-9]+)", first_page_text, re.I)
    if m: res["company_code"] = m.group(1)
    
    # Improved Quarter Detection: Handle "September, 2025" or "September 2025"
    m = re.search(r"(june|september|december|march|jun|sep|dec|mar)[^a-z0-9]*(20\d{2})", text.lower()[:3000])
    if m:
        mo = m.group(1)
        res["quarter"] = {"jun":"Q1","sep":"Q2","dec":"Q3","mar":"Q4"}.get(mo[:3], "Q1")
        res["year"] = int(m.group(2))
    return res

def analyze_results(results, include_obs=False, include_rec=False):
    if not results: return {}
    curr, prev, yoy = results[0], results[1], results[2]
    
    # Calculate growth for all metrics
    metrics = ['revenue', 'other_income', 'total_expenses', 'operating_profit', 'opm', 'pbt', 'net_profit', 'eps']
    growth = {}
    for m in metrics:
        growth[f"{m}_qoq"] = round(((curr[m] - prev[m])/prev[m]*100), 2) if prev[m] else 0
        growth[f"{m}_yoy"] = round(((curr[m] - yoy[m])/yoy[m]*100), 2) if yoy[m] else 0
    
    observations = []
    if include_obs:
        if curr['operating_profit'] < 0: observations.append("🚨 CRITICAL RED FLAG: Operating Loss.")
        if curr['opm'] < 0: observations.append("⚠️ Margin Collapse.")
        if growth['revenue_qoq'] < -10: observations.append("📉 Significant Revenue decline QoQ.")
        if growth['net_profit_yoy'] > 20: observations.append("🚀 Strong Profit growth YoY.")
    
    recommendation = {}
    if include_rec:
        recommendation = generate_recommendation(curr, observations)
    
    return {
        "table_data": results,
        "growth": growth,
        "observations": observations,
        "recommendation": recommendation
    }

def generate_recommendation(data, obs):
    score = 0
    for o in obs:
        if "CRITICAL" in o: score -= 5
        elif "⚠️" in o: score -= 2
        elif "📉" in o: score -= 1
        elif "🚀" in o: score += 2
    if data['net_profit'] > 0: score += 2
    
    if score >= 2: return {"verdict": "BUY / ACCUMULATE", "color": "green", "reasons": obs}
    if score > -3: return {"verdict": "HOLD / NEUTRAL", "color": "orange", "reasons": obs}
    return {"verdict": "STRONG AVOID / SELL", "color": "red", "reasons": obs}
