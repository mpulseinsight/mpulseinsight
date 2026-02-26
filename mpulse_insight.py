import streamlit as st
import pandas as pd
import psycopg2
import numpy as np
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

# 1. Page Config
st.set_page_config(page_title="mPulse Pro Console", layout="wide")

# 2. Professional CSS (Google Cloud / Bloomberg Style)
st.markdown("""
    <style>
        .main { background-color: #f8f9fa; }
        .hero-banner { background-color: white; border-bottom: 1px solid #dadce0; padding: 12px 24px; margin: -3rem -5rem 1rem -5rem; display: flex; justify-content: space-between; align-items: center; }
        
        /* Factor Scorecard */
        .factor-card { background: #ffffff; border: 1px solid #e0e0e0; border-radius: 8px; padding: 15px; margin-bottom: 10px; }
        .factor-label { font-size: 0.75rem; color: #5f6368; font-weight: 700; text-transform: uppercase; }
        .factor-value { font-size: 1.1rem; font-weight: 600; color: #202124; font-family: 'Roboto Mono', monospace; }
        
        /* Status Tags */
        .tag-missing { background: #feefc3; color: #b05a00; padding: 4px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: 600; }
        .tag-active { background: #e6f4ea; color: #137333; padding: 4px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: 600; }
        
        /* Range Bar */
        .range-bg { background: #eee; height: 6px; border-radius: 3px; width: 100%; margin-top: 8px; position: relative; }
        .range-pointer { background: #1a73e8; height: 12px; width: 4px; position: absolute; top: -3px; border-radius: 2px; }
    </style>
""", unsafe_allow_html=True)

# 3. Data Engine
@st.cache_data(ttl=60)
def load_and_process():
    try:
        creds = st.secrets["postgres"]
        conn = psycopg2.connect(host=creds["host"], port=creds["port"], database=creds["database"], 
                                user=creds["user"], password=creds["password"], sslmode="require")
        df = pd.read_sql("SELECT * FROM mpulse_execution_results", conn)
        conn.close()
        
        if df.empty: return pd.DataFrame()

        df['tradedate'] = pd.to_datetime(df['tradedate'])
        df['date_str'] = df['tradedate'].dt.strftime('%Y-%m-%d')
        
        # Mapping signals to rank for sorting
        rank_map = {'BUY': 5, 'BULLISH': 4, 'HOLD': 3, 'BEARISH': 2, 'SELL': 1}
        df['rank_score'] = df['signal'].fillna('').str.upper().apply(lambda x: next((v for k, v in rank_map.items() if k in x), 0))
        
        return df
    except Exception as e:
        st.error(f"Database Connection Error: {e}")
        return pd.DataFrame()

raw_df = load_process()

# 4. Top Section: Market Range & Global Context
with st.expander("🌐 GLOBAL MARKET REGIME & FACTOR RANGES", expanded=True):
    if not raw_df.empty:
        top_data = raw_df.iloc[0]
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Market Regime", top_data.get('final_regime', 'N/A'))
        with c2:
            st.metric("VIX Level", f"{top_data.get('vix', 0):.2f}")
        with c3:
            # Theoretical Z-Score Range Display
            z_val = top_data.get('zscore', 0)
            st.write("**Systemic Z-Score**")
            st.markdown(f"Value: `{z_val:.2f}`")
            # Visual Range (Simple -3 to +3 bar)
            pos = max(0, min(100, (z_val + 3) / 6 * 100))
            st.markdown(f'<div class="range-bg"><div class="range-pointer" style="left: {pos}%;"></div></div>', unsafe_allow_html=True)
        with c4:
            st.metric("Signals Found", len(raw_df[raw_df['date_str'] == top_data['date_str']]))

# 5. Main Matrix (Last 5 Days)
st.markdown("### 5-Day Alpha Matrix")
if not raw_df.empty:
    recent_dates = sorted(raw_df['date_str'].unique(), reverse=True)[:5]
    latest_date = recent_dates[0]
    
    # Filter & Pivot
    f_df = raw_df[raw_df['date_str'].isin(recent_dates)].copy()
    pivot = f_df.pivot_table(index=['symbol', 'sector'], columns='date_str', values='signal', aggfunc='first').reset_index()
    
    # Sort by the most recent day's rank
    latest_ranks = f_df[f_df['date_str'] == latest_date][['symbol', 'rank_score']]
    pivot = pivot.merge(latest_ranks, on='symbol', how='left').sort_values(by='rank_score', ascending=False)

    gb = GridOptionsBuilder.from_dataframe(pivot.drop(columns=['rank_score']))
    gb.configure_column("symbol", pinned="left", headerName="Ticker", width=120)
    gb.configure_selection(selection_mode="single")
    
    js_color = JsCode("""
    function(params) {
        if (!params.value) return {color: '#d1d1d1', fontStyle: 'italic'};
        const v = params.value.toUpperCase();
        if (v.includes('BUY')) return {backgroundColor: '#e6f4ea', color: '#137333', fontWeight: 'bold'};
        if (v.includes('SELL')) return {backgroundColor: '#fce8e6', color: '#c5221f', fontWeight: 'bold'};
        return {color: '#5f6368'};
    }
    """)
    for d in recent_dates: gb.configure_column(d, cellStyle=js_color)

    grid_resp = AgGrid(pivot, gridOptions=gb.build(), height=350, theme="balham", allow_unsafe_jscode=True)

# 6. Intelligence Hub (Bottom Section)
st.divider()
selection = grid_resp.get('selected_rows')

# Helper to normalize selection from AgGrid
selected_row = None
if selection is not None:
    if isinstance(selection, pd.DataFrame) and not selection.empty:
        selected_row = selection.iloc[0]
    elif isinstance(selection, list) and len(selection) > 0:
        selected_row = selection[0]

if selected_row is not None:
    ticker = selected_row['symbol']
    # Get all historical data for this ticker to see signal change
    ticker_history = raw_df[raw_df['symbol'] == ticker].sort_values('tradedate', ascending=False)
    
    if not ticker_history.empty:
        curr = ticker_history.iloc[0]
        
        # CHECK FOR MISSING EVALUATION DATA
        critical_factors = ['zscore', 'signal', 'rsi'] # Add your theory's key factors here
        missing_fields = [f for f in critical_factors if pd.isna(curr.get(f)) or curr.get(f) == '']

        if missing_fields:
            st.warning(f"⚠️ **Incomplete Evaluation:** Information for **{ticker}** is limited due to missing technical inputs: {', '.join(missing_fields)}.")
            st.info("The system is currently monitoring this asset but cannot confirm a signal change until data parity is reached.")
        else:
            # Display Key Theory Factors
            st.markdown(f"#### 🔍 Factor Deep-Dive: {ticker}")
            
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.markdown('<div class="factor-card">', unsafe_allow_html=True)
                st.markdown(f'<div class="factor-label">Primary Signal</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="factor-value" style="color:#1a73e8;">{curr["signal"]}</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
            
            with c2:
                # Display Z-Score Change
                prev_z = ticker_history.iloc[1]['zscore'] if len(ticker_history) > 1 else curr['zscore']
                delta_z = curr['zscore'] - prev_z
                st.markdown('<div class="factor-card">', unsafe_allow_html=True)
                st.markdown(f'<div class="factor-label">Z-Score (Trend)</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="factor-value">{curr["zscore"]:.2f} <small style="font-size:0.7rem; color:{"green" if delta_z >=0 else "red"};">({delta_z:+.2f})</small></div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

            with c3:
                st.markdown('<div class="factor-card">', unsafe_allow_html=True)
                st.markdown(f'<div class="factor-label">Volatility (ATR)</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="factor-value">{curr.get("atr", 0):.2f}</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

            with c4:
                st.markdown('<div class="factor-card">', unsafe_allow_html=True)
                st.markdown(f'<div class="factor-label">Suggested Action</div>', unsafe_allow_html=True)
                action = curr.get('suggested_action', 'WAIT')
                st.markdown(f'<div class="factor-value">{action if action else "MONITOR"}</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

            # Metadata Table Expander
            with st.expander("Full Technical Dictionary"):
                st.table(ticker_history[['date_str', 'signal', 'zscore', 'vix', 'suggested_action']].head(5))
    else:
        st.error("No historical records found for this ticker.")
else:
    st.info("💡 Select an asset from the matrix to analyze the underlying factors (Z-Score, RSI, ATR).")
