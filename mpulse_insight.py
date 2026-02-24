import streamlit as st
import pandas as pd
import psycopg2
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

# 1. Page Configuration
st.set_page_config(page_title="mPulse Console", layout="wide", initial_sidebar_state="expanded")

# 2. Enhanced UI Styling
st.markdown("""
    <style>
        .main { background-color: #f4f7f9; }
        .stMetric { background-color: #ffffff; padding: 10px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
        .audit-panel {
            background-color: #ffffff;
            padding: 20px;
            border-left: 2px solid #e0e0e0;
            height: 80vh;
            overflow-y: auto;
        }
        .instruction-banner {
            background-color: #1a73e8;
            color: white;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
    </style>
""", unsafe_allow_html=True)

# 3. Logic Engine for Signals
def explain_logic(sig, inst, regime):
    if sig == "BULLISH" and inst == "STAY CASH":
        return f"🚨 **Risk Override:** Market is {regime}. Safety protocols prevent buying despite bullish momentum."
    if sig == "BEARISH" and inst == "STAY CASH":
        return "📉 **Alignment:** Trend is negative; capital is protected in cash."
    return f"⚡ **Active Mode:** {inst} order recommended based on {sig} signal."

# 4. Data Loading
@st.cache_data(ttl=60)
def load_data():
    try:
        creds = st.secrets["postgres"]
        conn = psycopg2.connect(host=creds["host"], port=creds["port"], database=creds["database"], 
                                user=creds["user"], password=creds["password"], sslmode="require")
        df = pd.read_sql("SELECT * FROM mpulse_execution_results ORDER BY tradedate ASC", conn)
        conn.close()
        if not df.empty:
            df['date_str'] = df['tradedate'].astype(str)
        return df
    except Exception as e:
        st.error(f"DB Error: {e}")
        return pd.DataFrame()

raw_df = load_data()

# 5. Sidebar: Perspective & Filters
with st.sidebar:
    st.title("🎯 Console Controls")
    perspective = st.radio(
        "Display Perspective",
        ["Daily Signal", "60-Day Signal", "Combined View"],
        index=0  # Default to Daily as requested
    )
    st.markdown("---")
    search_ticker = st.text_input("🔍 Search Symbol").upper()
    industry = st.selectbox("📂 Industry", ["All"] + sorted(raw_df['sector'].unique().tolist()) if not raw_df.empty else [])

# 6. The Meaningful Top Bar
if not raw_df.empty:
    latest = raw_df.iloc[-1]
    t1, t2, t3, t4 = st.columns([1.5, 1, 1, 1])
    with t1:
        st.markdown(f"""<div class='instruction-banner'>
            <small>MARKET ENVIRONMENT</small><br>
            <strong>{latest['final_regime']} ({latest['trend_regime']})</strong>
        </div>""", unsafe_allow_html=True)
    t2.metric("Market Vol (VIX)", f"{latest['vix']:.2f}")
    t3.metric("S&P 200DMA", f"{latest['spx_200dma']:,.0f}")
    t4.metric("Risk Status", "RESTRICTED" if latest['vix'] > 25 else "OPERATIONAL")

# 7. Main Interface Split (Grid + Vertical Audit Slider)
col_grid, col_audit = st.columns([2.2, 0.8])

if not raw_df.empty:
    # Filter Data
    grid_df = raw_df.copy()
    if search_ticker: grid_df = grid_df[grid_df['symbol'].str.contains(search_ticker)]
    if industry != "All": grid_df = grid_df[grid_df['sector'] == industry]

    # Map signals based on sidebar choice
    def map_sig(r):
        if perspective == "Daily Signal": return r['signal']
        if perspective == "60-Day Signal": return f"🛡️ {r['signal_60d']}"
        return f"{r['signal']} | {r['signal_60d']}"

    grid_df['display_val'] = grid_df.apply(map_sig, axis=1)
    
    # Create Pivot
    recent_dates = sorted(raw_df['date_str'].unique().tolist(), reverse=True)[:5]
    pivot = grid_df.pivot_table(index=['symbol', 'sector'], columns='date_str', values='display_val', aggfunc='first').reset_index()
    
    with col_grid:
        gb = GridOptionsBuilder.from_dataframe(pivot)
        gb.configure_column("symbol", pinned="left", width=90)
        gb.configure_selection(selection_mode="single")
        for d_col in recent_dates:
            gb.configure_column(d_col, width=160)
        
        st.markdown("### Execution Matrix")
        grid_out = AgGrid(pivot, gridOptions=gb.build(), height=500, theme="alpine", update_mode=GridUpdateMode.SELECTION_CHANGED)

    # 8. Vertical Audit Slider (Side Panel)
    with col_audit:
        st.markdown("### 🔬 Technical Audit")
        sel = grid_out.get('selected_rows')
        if sel is not None and len(sel) > 0:
            ticker = (sel.iloc[0] if isinstance(sel, pd.DataFrame) else sel[0])['symbol']
            d = raw_df[raw_df['symbol'] == ticker].sort_values('tradedate', ascending=False).iloc[0]
            
            # Logic Explanation Header
            st.markdown(f"**{ticker} Logic:**")
            st.info(explain_logic(d['signal'], d['suggested_action'], d['final_regime']))
            
            # The "Vertical Slider" style list
            st.markdown("<div class='audit-panel'>", unsafe_allow_html=True)
            audit_data = d.drop(['grid_display', 'display_val', 'date_str', 'cell_val'], errors='ignore')
            
            # Displaying as a vertical grid (Field Name | Value)
            for col_name in audit_data.index:
                val = audit_data[col_name]
                disp_val = f"{val:.4f}" if isinstance(val, float) else str(val)
                st.markdown(f"**{col_name}**")
                st.code(disp_val)
                st.markdown("---")
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.caption("Select a ticker to analyze all 40+ technical fields vertically.")
