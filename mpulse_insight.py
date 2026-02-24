# 4. Data Engine (HARDENED)
def get_db_connection():
    try:
        # Check if secrets exist at all
        if "postgres" not in st.secrets:
            st.error("Database secrets are missing! Check your secrets.toml or Cloud settings.")
            return None
            
        creds = st.secrets["postgres"]
        return psycopg2.connect(
            host=creds.get("host"), 
            port=creds.get("port"), 
            database=creds.get("database"),
            user=creds.get("user"), 
            password=creds.get("password"), 
            sslmode="require",
            connect_timeout=10 # Stop the "infinite loading" spin
        )
    except Exception as e:
        st.error(f"⚠️ Connection Failed: {str(e)}")
        return None

@st.cache_data(ttl=60)
def load_data():
    conn = get_db_connection()
    if not conn: 
        return pd.DataFrame(), pd.DataFrame()
    
    try:
        df = pd.read_sql("SELECT * FROM mpulse_execution_results ORDER BY asatdate ASC", conn)
        conn.close() # Close immediately after fetch
    except Exception as e:
        st.error(f"⚠️ SQL Query Error: {str(e)}")
        return pd.DataFrame(), pd.DataFrame()
        
    if df.empty:
        st.info("Database is connected, but the 'mpulse_execution_results' table is empty.")
        return pd.DataFrame(), pd.DataFrame()

    # Create a string date for the pivot columns
    df['date_str'] = df['asatdate'].astype(str)
    
    # SAFE PIVOT: Fallback logic if your new columns aren't in the DB yet
    pivot_val = 'execution_stance' if 'execution_stance' in df.columns else 'signal'
    
    try:
        pivot = df.pivot_table(
            index=['symbol', 'sector'], 
            columns='date_str', 
            values=pivot_val, 
            aggfunc='first'
        ).reset_index().fillna('')
        
        cols = [c for c in pivot.columns if c not in ['symbol', 'sector']]
        recent = sorted(cols, reverse=True)[:5]
        return df, pivot[['symbol', 'sector'] + sorted(recent)]
    except Exception as e:
        st.error(f"⚠️ Pivot Logic Error: {str(e)}")
        return df, pd.DataFrame()

# Trigger data load
with st.spinner("Connecting to mPulse Intelligence..."):
    raw_df, pivot_5_df = load_data()

# EMERGENCY STOP: If data is missing, don't try to render the rest of the UI
if raw_df.empty or pivot_5_df.empty:
    st.warning("Dashboard waiting for data. Please check your database connection.")
    st.stop()
