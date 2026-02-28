import streamlit as st
import pandas as pd
import psycopg2
import plotly.graph_objects as go
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

# 1. Page Configuration
st.set_page_config(page_title="mPulse Pro Terminal", layout="wide")

# 2. Modern Terminal CSS (Cleaner for 2026)
st.markdown("""
    <style>
        .main { background-color: #0e1117; color: #fafafa; }
        div[data-testid="stMetricValue"] { font-size: 1.8rem; color: #00d4ff; }
        .status-card {
            background: #161b22;
            border-radius: 10px;
            padding: 1.5rem;
            border-left: 5px solid #00d4ff;
            margin-bottom: 1rem;
        }
        .advice-box {
            background: #1c2128;
            padding: 15px;
            border-radius: 5px;
            border: 1px solid #30363d;
        }
    </style>
""", unsafe_allow_html=True)

# 3. Enhanced Data Engine
@st.cache_data(ttl=60)
def load_market_data():
    try:
        # Use st.connection for more stable PostgreSQL pooling in 2026
        creds = st.secrets["postgres"]
        conn = psycopg2.connect(
            host=creds["host"], port=creds["port"], database=creds["database"], 
            user=creds["user"], password=creds["password"], sslmode="require"
        )
        query = "SELECT * FROM mpulse_execution_results ORDER BY tradedate DESC"
        df = pd.read_sql(query, conn)
        conn.close()
        
        df.columns = [c.lower() for c in df.columns]
        if 'tradedate' in df.columns:
            df['tradedate'] = pd.to_datetime(df['tradedate'])
            df['date_str'] = df['tradedate'].dt.strftime('%Y-%m-%d')
        return df
    except Exception as e:
        st.error(f"⚠️ Connection Failed: {e}")
        return pd.DataFrame()

df = load_market_data()

# --- SIDEBAR & FILTERING ---
with st.sidebar:
    st.header("🎛️ Command Controls")
    search = st.text_input("Search Ticker (e.g. NVDA, BTC)", "").upper()
    lookback = st.slider("Signal Lookback (Days)", 5, 60, 15)

# --- MAIN DASHBOARD ---
if not df.empty:
    # 4. Global Market Pulse
    latest_snap = df.iloc[0]
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Market Regime", latest_snap.get('final_regime', 'Neutral'))
    m2.metric("VIX Volatility", f"{latest_snap.get('vix', 0):.2f}")
    m3.metric("Trend Strength", "💪 Strong" if latest_snap.get('adx', 0) > 25 else "😴 Sideways")
    m4.metric("Data Freshness", latest_snap['date_str'])

    # 5. The Insight Matrix
    st.subheader("📡 Recent Signal Matrix")
    recent_dates = sorted(df['date_str'].unique(), reverse=True)[:lookback]
    matrix_df = df[df['date_str'].isin(recent_dates)].copy()
    
    if search:
        matrix_df = matrix_df[matrix_df['symbol'].str.contains(search)]

    # Pivot for a "Heatmap" view
    pivot = matrix_df.pivot_table(
        index=['symbol', 'sector'], 
        columns='date_str', 
        values='signal', 
        aggfunc='first'
    ).reset_index().fillna("-")

    # Configure Grid
    gb = GridOptionsBuilder.from_dataframe(pivot)
    gb.configure_selection('single', use_checkbox=True)
    gb.configure_side_bar()
    gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=10)
    
    # Simple color coding for "Common Man" clarity
    cells_js = JsCode("""
    function(params) {
        if (params.value === 'BUY' || params.value.includes('BULL')) return {'color': 'white', 'backgroundColor': '#008000'};
        if (params.value === 'SELL' || params.value.includes('BEAR')) return {'color': 'white', 'backgroundColor': '#d32f2f'};
        return {'color': '#888'};
    }
    """)
    for col in recent_dates:
        gb.configure_column(col, cellStyle=cells_js)

    grid_data = AgGrid(
        pivot, 
        gridOptions=gb.build(), 
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        allow_unsafe_jscode=True,
        theme='alpine'
    )

    # 6. Deep Intelligence Hub
    selected = grid_data['selected_rows']
    
    # Fix: AgGrid selection returns differently depending on version
    if selected is not None and (isinstance(selected, list) and len(selected) > 0):
        # Handle both list of dicts and DataFrame return types
        s_row = selected[0] if isinstance(selected, list) else selected.iloc[0]
        ticker = s_row['symbol']
        
        hist = df[df['symbol'] == ticker].head(60) # Last 60 days
        current = hist.iloc[0]

        st.divider()
        st.header(f"🔍 Intelligence Report: {ticker}")
        
        c1, c2 = st.columns([1, 2])
        
        with c1:
            st.markdown(f"### 💡 Directional Advice")
            # Logic to simplify technicals for the "Common Man"
            rsi = current.get('rsi', 50)
            zscore = current.get('zscore', 0)
            
            if rsi > 70:
                advice = "⚠️ **EXTREME CAUTION**: Asset is overbought. High risk of a pullback."
            elif rsi < 30:
                advice = "✅ **OPPORTUNITY**: Asset is oversold. Potential value entry."
            elif zscore > 2:
                advice = "📉 **MEAN REVERSION**: Price is too far above average. Expect a drop."
            else:
                advice = "⚖️ **STABLE**: Price is moving within normal ranges."

            st.info(advice)
            st.write(f"**Suggested Action:** {current.get('suggested_action', 'Hold')}")
            st.write(f"**Sector Context:** {current.get('sector', 'N/A')}")

        with c2:
            # 7. Visual Trend (60 Days)
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=hist['tradedate'], y=hist['rsi'], name="RSI (Momentum)"))
            fig.add_trace(go.Scatter(x=hist['tradedate'], y=[70]*60, name="Overbought", line=dict(dash='dash', color='red')))
            fig.add_trace(go.Scatter(x=hist['tradedate'], y=[30]*60, name="Oversold", line=dict(dash='dash', color='green')))
            fig.update_layout(title=f"{ticker} 60-Day Momentum (RSI)", height=300, template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)

else:
    st.warning("No data found in the `mpulse_execution_results` table.")

st.markdown("---")
st.caption("mPulse Intelligence Engine | Systems Nominal")
