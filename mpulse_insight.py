import streamlit as st
import pandas as pd
import psycopg2
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

# 1. Page Configuration
st.set_page_config(page_title="mPulse Pro Console", layout="wide", initial_sidebar_state="collapsed")

# 2. Professional CSS (Google/Bloomberg Aesthetic)
st.markdown("""
    <style>
        .main { background-color: #f8f9fa; }
        .hero-banner { background-color: white; border-bottom: 1px solid #dadce0; padding: 12px 24px; margin: -3rem -5rem 1rem -5rem; display: flex; justify-content: space-between; align-items: center; }
        
        /* Factor Scorecard */
        .factor-card { background: #ffffff; border: 1px solid #e0e0e0; border-radius: 8px; padding: 15px; margin-bottom: 10px; transition: 0.3s; }
        .factor-card:hover { border-color: #1a73e8; box-shadow: 0 1px 6px rgba(32,33,36,0.1); }
        .factor-label { font-size: 0.75rem; color: #5f6368; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; }
        .factor-value { font-size: 1.2rem; font-weight: 600; color: #202124; font-family: 'Courier New', monospace; }
        
        /* Visual Range Bar */
        .range-track { background: #e8eaed; height: 8px; border-radius: 4px; width: 100%; margin: 8px 0; position: relative; }
        .range-fill { background: #1a73e8; height: 100%; border-radius: 4px; }
        .range-marker { position: absolute; top: -4px; width: 4px; height: 16px; background: #202124; border-radius: 2px; }
        
        /* Alerts & Diagnostics */
        .diagnostic-box { background: #fffcf0; border: 1px solid #ffe082; padding: 15px; border-radius: 8px; color: #856404; }
        .dictionary-term { font-weight: 700; color: #1a73e8; }
    </style>
""", unsafe_allow_html=True)

# 3. Fixed Data Engine
@st.cache_data(ttl=60)
def load_and_process_data():
    try:
        creds = st.secrets["postgres"]
        conn = psycopg2.connect(host=creds["host"], port=creds["port"], database=creds["database"], 
                                user=creds["user"], password=creds["password"], sslmode="require")
        df = pd.read_sql("SELECT * FROM mpulse_execution_results", conn)
        conn.close()
        
        if df.empty: return pd.DataFrame()

        df['tradedate'] = pd.to_datetime(df['tradedate'])
        df['date_str'] = df['tradedate'].dt.strftime('%Y-%m-%d')
        
        # Rank signals for sorting: Buy/Bullish float to top
        rank_map = {'BUY': 5, 'BULLISH': 4, 'HOLD': 3, 'BEARISH': 2, 'SELL': 1}
        df['rank_score'] = df['signal'].fillna('').str.upper().apply(lambda x: next((v for k, v in rank_map.items() if k in x), 0))
        
        return df
    except Exception as e:
        st.error(f"Failed to connect to signal database: {e}")
        return pd.DataFrame()

# CALLED CORRECTLY NOW:
raw_df = load_and_process_data()

# 4. Top Section: Market Range Monitor (Collapsible)
with st.expander("📊 GLOBAL MARKET RANGES & SYSTEMIC FACTORS", expanded=True):
    if not raw_df.empty:
        # Get the absolute latest data point for global metrics
        latest_global = raw_df.sort_values('tradedate', ascending=False).iloc[0]
        
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("Market Regime", latest_global.get('final_regime', 'Neutral'))
        with m2:
            st.metric("VIX (Fear Index)", f"{latest_global.get('vix', 0):.2f}")
        with m3:
            # Z-Score Visual Range (-3 to +3)
            z = latest_global.get('zscore', 0)
            st.write(f"**Systemic Z-Score: {z:.2f}**")
            z_pos = max(0, min(100, (z + 3) / 6 * 100))
            st.markdown(f'<div class="range-track"><div class="range-marker" style="left:{z_pos}%;"></div></div>', unsafe_allow_html=True)
        with m4:
            st.metric("Total Active Assets", len(raw_df['symbol'].unique()))

# 5. Main Matrix: Last 5 Days
if not raw_df.empty:
    recent_dates = sorted(raw_df['date_str'].unique(), reverse=True)[:5]
    latest_date = recent_dates[0]
    
    # Filter to 5 days and apply search if any
    f_df = raw_df[raw_df['date_str'].isin(recent_dates)].copy()
    
    # Pivot & Sort by latest day's signal strength
    pivot = f_df.pivot_table(index=['symbol', 'sector'], columns='date_str', values='signal', aggfunc='first').reset_index()
    latest_ranks = f_df[f_df['date_str'] == latest_date][['symbol', 'rank_score']]
    pivot = pivot.merge(latest_ranks, on='symbol', how='left').sort_values(by='rank_score', ascending=False)

    st.subheader("Signal Matrix (5-Day Trend)")
    gb = GridOptionsBuilder.from_dataframe(pivot.drop(columns=['rank_score']))
    gb.configure_column("symbol", pinned="left", headerName="Ticker", width=120)
    gb.configure_selection(selection_mode="single")
    
    # Green/Red heatmap logic
    js_color = JsCode("""
    function(params) {
        if (!params.value) return {color: '#bdc3c7', fontStyle: 'italic'};
        const v = params.value.toUpperCase();
        if (v.includes('BUY')) return {backgroundColor: '#e6f4ea', color: '#137333', fontWeight: 'bold'};
        if (v.includes('SELL')) return {backgroundColor: '#fce8e6', color: '#c5221f', fontWeight: 'bold'};
        return {color: '#5f6368'};
    }
    """)
    for d in recent_dates: gb.configure_column(d, cellStyle=js_color)

    grid_resp = AgGrid(pivot, gridOptions=gb.build(), height=350, theme="balham", allow_unsafe_jscode=True)

# 6. Asset Intelligence Hub (The Expander / Card)
st.divider()
selection = grid_resp.get('selected_rows')

# Handle selection types safely
selected_row = None
if selection is not None:
    if isinstance(selection, pd.DataFrame) and not selection.empty: selected_row = selection.iloc[0]
    elif isinstance(selection, list) and len(selection) > 0: selected_row = selection[0]

if selected_row is not None:
    ticker = selected_row['symbol']
    # Get latest data record for factors
    asset_data = raw_df[(raw_df['symbol'] == ticker) & (raw_df['date_str'] == latest_date)]
    
    if not asset_data.empty:
        curr = asset_data.iloc[0]
        
        # --- DATA INTEGRITY GUARD ---
        # Check for empty values in key theoretical factors
        required_factors = ['zscore', 'rsi', 'atr']
        missing = [f for f in required_factors if pd.isna(curr.get(f))]

        if missing:
            st.markdown(f"""
                <div class="diagnostic-box">
                    <b>⚠️ Evaluation Suspended: {ticker}</b><br>
                    Missing core factors: <i>{', '.join(missing)}</i>. Signal strength cannot be verified. 
                    Historical baseline is being used for grid display only.
                </div>
            """, unsafe_allow_html=True)
        else:
            # Main Intelligence Card
            st.markdown(f"### Intelligence Card: {ticker}")
            
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                # Better Action Messaging
                raw_action = str(curr.get('suggested_action', 'HOLD')).upper()
                sig = str(curr.get('signal', '')).upper()
                display_action = "PREPARING ENTRY" if ("BULL" in sig and "CASH" in raw_action) else raw_action
                
                st.markdown(f'<div class="factor-card"><div class="factor-label">Action</div><div class="factor-value" style="color:#1a73e8;">{display_action}</div></div>', unsafe_allow_html=True)
            
            with c2:
                # Z-Score Tracking
                st.markdown(f'<div class="factor-card"><div class="factor-label">Z-Score (Factor)</div><div class="factor-value">{curr["zscore"]:.2f}</div></div>', unsafe_allow_html=True)
            
            with c3:
                st.markdown(f'<div class="factor-card"><div class="factor-label">RSI (Momentum)</div><div class="factor-value">{curr.get("rsi", 0):.1f}</div></div>', unsafe_allow_html=True)
                
            with c4:
                st.markdown(f'<div class="factor-card"><div class="factor-label">ATR (Volatility)</div><div class="factor-value">{curr.get("atr", 0):.2f}</div></div>', unsafe_allow_html=True)

            # --- THE DICTIONARY ---
            with st.expander("📘 Theory Dictionary & Data Legend"):
                st.markdown("""
                | Term | Meaning | Range |
                | :--- | :--- | :--- |
                | <span class="dictionary-term">Z-Score</span> | Distance from mean price. | **-2 to +2** (Normal), **>3** (Extremes) |
                | <span class="dictionary-term">RSI</span> | Measures speed/change of price. | **<30** (Oversold), **>70** (Overbought) |
                | <span class="dictionary-term">ATR</span> | Average True Range. | Higher = Higher Volatility / Risk |
                | <span class="dictionary-term">Signal</span> | Weighted output of all factors. | Bullish, Bearish, or Neutral |
                """)
    else:
        st.error("Historical data trace lost for this asset.")
else:
    st.info("💡 Select an asset from the matrix to load the Intelligence Card and Theory Dictionary.")
