import streamlit as st
import pandas as pd
import psycopg2
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

# 1. Page Configuration
st.set_page_config(page_title="mPulse Intelligence", layout="wide", initial_sidebar_state="expanded")

# 2. CSS for the "Logic Header"
st.markdown("""
    <style>
        .instruction-box {
            background-color: #f0f7ff;
            border-left: 5px solid #1a73e8;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 10px;
        }
        .reason-text {
            color: #5F6368;
            font-size: 14px;
            font-style: italic;
        }
    </style>
""", unsafe_allow_html=True)

# 3. Dynamic Logic Explainer (The "Why")
def get_logic_reason(signal, instruction, regime, structural):
    """Explains why a Signal and Instruction might seem to contradict."""
    if signal == "BULLISH" and instruction == "STAY CASH":
        if regime in ["VOLATILE", "BEARISH"]:
            return "⚠️ MARKET OVERRIDE: Individual stock looks good, but the overall Market Regime is too dangerous for new longs."
        if structural == "BEARISH":
            return "⚠️ TREND MISMATCH: Daily momentum is up, but the 60-Day structural trend is still down. This is likely a 'Bull Trap'."
        return "⚠️ RISK LIMIT: High volatility or low liquidity has triggered a safety pause despite positive price action."
    
    if signal == "BEARISH" and instruction == "BUY":
        return "ℹ️ MEAN REVERSION: The stock is oversold in a strong Bull regime. We are buying the dip."
        
    return "✅ ALIGNED: Signal and Instruction are in sync with current risk parameters."

# 4. Technical Audit Popup
@st.dialog("Full Technical Audit", width="large")
def show_full_audit(ticker, raw_data):
    d = raw_data[raw_data['symbol'] == ticker].sort_values('tradedate', ascending=False).iloc[0]
    st.subheader(f"Technical DNA: {ticker}")
    cols = st.columns(3)
    for i, (col, val) in enumerate(d.items()):
        with cols[i % 3]:
            st.metric(label=col, value=str(round(val, 4)) if isinstance(val, float) else str(val))

# 5. Data Engine
@st.cache_data(ttl=60)
def load_data():
    try:
        creds = st.secrets["postgres"]
        conn = psycopg2.connect(host=creds["host"], port=creds["port"], database=creds["database"], 
                                user=creds["user"], password=creds["password"], sslmode="require")
        df = pd.read_sql("SELECT * FROM mpulse_execution_results ORDER BY tradedate ASC", conn)
        conn.close()
        df['date_str'] = df['tradedate'].astype(str)
        return df
    except: return pd.DataFrame()

raw_df = load_data()

# 6. Sidebar & Filters
with st.sidebar:
    st.title("Filters")
    view_daily = st.checkbox("Daily Perspective", value=True)
    view_60d = st.checkbox("60D Perspective", value=True)
    sector_list = ["All"] + sorted(raw_df['sector'].unique().tolist())
    sel_sector = st.selectbox("Industry", sector_list)

# 7. Main UI Layout
# ---------------------------------------------------------
# TOP SECTION: Dynamic Intel Bar (Appears when Ticker is Selected)
# ---------------------------------------------------------
grid_data = raw_df.copy()
if sel_sector != "All":
    grid_data = grid_data[grid_data['sector'] == sel_sector]

# We use a placeholder to update the header based on grid selection
header_placeholder = st.empty()

# 8. Matrix Rendering
st.markdown("### Market Matrix")
raw_df['cell_val'] = raw_df.apply(lambda r: f"{r['signal']} | 🛡️ {r['signal_60d']}", axis=1)
recent_dates = sorted(raw_df['date_str'].unique().tolist(), reverse=True)[:5]
pivot = grid_data.pivot_table(index=['symbol', 'sector'], columns='date_str', values='cell_val', aggfunc='first').reset_index()

gb = GridOptionsBuilder.from_dataframe(pivot)
gb.configure_column("symbol", pinned="left", width=100)
gb.configure_selection(selection_mode="single")
for d_col in recent_dates:
    gb.configure_column(d_col, width=200)

grid_out = AgGrid(pivot, gridOptions=gb.build(), height=400, theme="alpine", update_mode=GridUpdateMode.SELECTION_CHANGED)

# 9. Update the Top Header based on Grid Selection
sel = grid_out.get('selected_rows')
if sel is not None and len(sel) > 0:
    ticker = (sel.iloc[0] if isinstance(sel, pd.DataFrame) else sel[0])['symbol']
    d = raw_df[raw_df['symbol'] == ticker].sort_values('tradedate', ascending=False).iloc[0]
    
    # Generate the meaningful reason for Signal/Instruction combo
    reason = get_logic_reason(d['signal'], d['suggested_action'], d['final_regime'], d['signal_60d'])
    
    with header_placeholder.container():
        c1, c2, c3 = st.columns([1.5, 2, 1])
        with c1:
            st.markdown(f"## {ticker}")
            st.button("🔬 Audit All Fields", on_click=show_full_audit, args=(ticker, raw_df))
        with c2:
            st.markdown(f"""
                <div class="instruction-box">
                    <strong>INSTRUCTION:</strong> {d['suggested_action']}<br>
                    <span class="reason-text">{reason}</span>
                </div>
            """, unsafe_allow_html=True)
        with c3:
            st.metric("Pulse Score", f"{d['s_hybrid']:.2f}")
            st.metric("Structure", f"{d['s_structural']:.2f}")
        st.markdown("---")
