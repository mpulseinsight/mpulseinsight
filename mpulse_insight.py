import streamlit as st  # <--- This must be the first line
import pandas as pd
import psycopg2
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

# 1. Page Configuration (Must come before any other st. commands)
st.set_page_config(page_title="mPulse Pro v3.1", layout="wide", initial_sidebar_state="expanded")

# ... (CSS Section 2 and Sidebar Section 3 go here) ...

# 4. Data Engine (Ensure this is AFTER imports and Page Config)
def get_db_connection():
    try:
        creds = st.secrets["postgres"]
        return psycopg2.connect(
            host=creds["host"], port=creds["port"], database=creds["database"],
            user=creds["user"], password=creds["password"], sslmode="require"
        )
    except Exception as e:
        st.error(f"Connection Error: {e}")
        return None

@st.cache_data(ttl=60)
def load_data():
    conn = get_db_connection()
    if not conn: 
        return pd.DataFrame(), pd.DataFrame()
    
    try:
        df = pd.read_sql("SELECT * FROM mpulse_execution_results ORDER BY asatdate ASC", conn)
    except Exception as e:
        st.error(f"Query Error: {e}")
        return pd.DataFrame(), pd.DataFrame()
    finally:
        conn.close()
        
    if df.empty:
        return pd.DataFrame(), pd.DataFrame()

    df['date_str'] = df['asatdate'].astype(str)
    
    # Check if execution_stance exists in your DB, fallback to signal if not
    pivot_col = 'execution_stance' if 'execution_stance' in df.columns else 'signal'
    
    pivot = df.pivot_table(index=['symbol', 'sector'], columns='date_str', values=pivot_col, aggfunc='first').reset_index().fillna('')
    cols = [c for c in pivot.columns if c not in ['symbol', 'sector']]
    recent = sorted(cols, reverse=True)[:5]
    
    return df, pivot[['symbol', 'sector'] + sorted(recent)]

# Now call the function
raw_df, pivot_5_df = load_data()
