# 4. Data Engine

# REMOVED @st.cache_resource to prevent holding "dead" connections
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
        # Fetch the data using the fresh connection
        df = pd.read_sql("SELECT * FROM mpulse_execution_results ORDER BY asatdate ASC", conn)
    except Exception as e:
        st.error(f"Query Error: {e}")
        return pd.DataFrame(), pd.DataFrame()
    finally:
        # Crucial: Always close the connection after the query finishes to prevent memory/connection leaks
        conn.close()
        
    if df.empty:
        return pd.DataFrame(), pd.DataFrame()

    df['date_str'] = df['asatdate'].astype(str)
    
    # Pivot to show 'execution_stance' instead of just signal for the top-level view
    pivot = df.pivot_table(index=['symbol', 'sector'], columns='date_str', values='execution_stance', aggfunc='first').reset_index().fillna('')
    cols = [c for c in pivot.columns if c not in ['symbol', 'sector']]
    recent = sorted(cols, reverse=True)[:5]
    
    return df, pivot[['symbol', 'sector'] + sorted(recent)]
