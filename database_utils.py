import mysql.connector
import json
import logging
from config import config

logger = logging.getLogger(__name__)

def get_db_connection():
    """Establishes and returns a connection to the MySQL database."""
    try:
        conn = mysql.connector.connect(
            host=config.DB_HOST,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            database=config.DB_NAME
        )
        return conn
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return None

def get_analysis_data(company_id, quarter, year):
    """Retrieves analysis data from the database if it exists."""
    if not company_id: return None
    conn = get_db_connection()
    if not conn: return None

    try:
        cursor = conn.cursor(dictionary=True)
        sql = f"SELECT raw_json FROM {config.DB_TABLE} WHERE company_id = %s AND quarter = %s AND year = %s"
        cursor.execute(sql, (company_id, quarter, year))
        result = cursor.fetchone()
        if result and result['raw_json']:
            return json.loads(result['raw_json'])
        return None
    except Exception as e:
        logger.error(f"Failed to fetch data: {e}")
        return None
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def upsert_analysis_data(data):
    """
    Saves or updates extracted financial data in the MySQL table.
    Scales currency values from Lakhs (PDF) to Crores (Table).
    """
    conn = get_db_connection()
    if not conn:
        return False

    try:
        cursor = conn.cursor()
        
        # Scaling helper (Data is already normalized to Crores by engines)
        def scale(val):
            try:
                return float(val) 
            except (ValueError, TypeError):
                return 0.0

        # Extract current record from table_data (usually the first entry)
        current = data.get('table_data', [{}])[0]
        growth = data.get('growth', {})
        corp_actions = data.get('corporate_actions', {})
        rec = data.get('recommendation', {})

        # Prepare field values
        company_id = data.get('company_id')
        company_code = data.get('company_code')
        quarter = data.get('quarter', 'Q1')
        year = data.get('year', 2025)
        result_type = data.get('result_type', 'Standalone')
        
        sales = scale(current.get('revenue'))
        other_income = scale(current.get('other_income'))
        total_expenses = scale(current.get('total_expenses'))
        operating_profit = scale(current.get('operating_profit'))
        pbt = scale(current.get('pbt'))
        net_profit = scale(current.get('net_profit'))
        
        margin = current.get('opm', 0.0)
        eps = current.get('eps', 0.0)
        
        revenue_qoq = growth.get('revenue_qoq', 0.0)
        revenue_yoy = growth.get('revenue_yoy', 0.0)
        net_profit_qoq = growth.get('net_profit_qoq', 0.0)
        net_profit_yoy = growth.get('net_profit_yoy', 0.0)
        
        dividend = corp_actions.get('dividend', 0.0)
        if isinstance(dividend, str):
            import re
            m = re.search(r'\d+(?:\.\d+)?', dividend)
            dividend = float(m.group(0)) if m else 0.0
            
        capex = scale(corp_actions.get('capex'))
        mgmt_change = corp_actions.get('management_change', 'No')
        spec_ann = corp_actions.get('special_announcement', '')
        
        observations = "\n".join(data.get('observations', []))
        rec_verdict = rec.get('verdict', 'HOLD / NEUTRAL')
        raw_json = json.dumps(data)

        sql = f"""
            INSERT INTO {config.DB_TABLE} (
                company_id, company_code, quarter, year, result_type,
                sales, other_income, total_expenses, operating_profit, pbt, net_profit,
                margin, eps, revenue_growth_qoq, revenue_growth_yoy,
                net_profit_growth_qoq, net_profit_growth_yoy,
                dividend, capex, management_change, special_announcement,
                observations, recommendation_verdict, raw_json
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s
            )
            ON DUPLICATE KEY UPDATE
                company_code = VALUES(company_code),
                result_type = VALUES(result_type),
                sales = VALUES(sales),
                other_income = VALUES(other_income),
                total_expenses = VALUES(total_expenses),
                operating_profit = VALUES(operating_profit),
                pbt = VALUES(pbt),
                net_profit = VALUES(net_profit),
                margin = VALUES(margin),
                eps = VALUES(eps),
                revenue_growth_qoq = VALUES(revenue_growth_qoq),
                revenue_growth_yoy = VALUES(revenue_growth_yoy),
                net_profit_growth_qoq = VALUES(net_profit_growth_qoq),
                net_profit_growth_yoy = VALUES(net_profit_growth_yoy),
                dividend = VALUES(dividend),
                capex = VALUES(capex),
                management_change = VALUES(management_change),
                special_announcement = VALUES(special_announcement),
                observations = VALUES(observations),
                recommendation_verdict = VALUES(recommendation_verdict),
                raw_json = VALUES(raw_json)
        """

        params = (
            company_id, company_code, quarter, year, result_type,
            sales, other_income, total_expenses, operating_profit, pbt, net_profit,
            margin, eps, revenue_qoq, revenue_yoy,
            net_profit_qoq, net_profit_yoy,
            dividend, capex, mgmt_change, spec_ann,
            observations, rec_verdict, raw_json
        )

        cursor.execute(sql, params)
        conn.commit()
        logger.info(f"Successfully saved analysis for {company_id or company_code} ({quarter} {year})")
        return True

    except Exception as e:
        logger.error(f"Failed to upsert data: {e}", exc_info=True)
        return False
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def get_all_analysis_data():
    """Retrieves all analysis records from the database."""
    conn = get_db_connection()
    if not conn:
        return []

    try:
        cursor = conn.cursor(dictionary=True)
        # Select all columns except raw_json to save bandwidth
        sql = f"""
            SELECT 
                company_id, company_code, quarter, year, result_type,
                sales, other_income, total_expenses, operating_profit, pbt, net_profit,
                margin, eps, 
                revenue_growth_qoq, revenue_growth_yoy,
                net_profit_growth_qoq, net_profit_growth_yoy,
                dividend, capex, management_change, special_announcement,
                recommendation_verdict, created_at
            FROM {config.DB_TABLE}
            ORDER BY year DESC, quarter DESC, company_code ASC
        """
        cursor.execute(sql)
        results = cursor.fetchall()
        return results
    except Exception as e:
        logger.error(f"Failed to fetch all data: {e}")
        return []
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()
