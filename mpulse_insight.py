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
            font-size: 13px;
            font-style: italic;
            margin-top: 5px;
            display: block;
        }
    </style>
""", unsafe_allow_html=True)

# 3. Dynamic Logic Explainer
def get_logic_reason(signal, instruction, regime, structural_sig):
    if signal == "BULLISH" and instruction == "STAY CASH":
        if regime in ["VOLATILE", "BEARISH"]:
            return "⚠️ MARKET OVERRIDE: Individual stock looks good, but the overall Market Regime is too dangerous for new longs."
        if structural_sig == "BEARISH":
            return "⚠️ TREND MISMATCH: Daily momentum is up, but the 60-Day structural trend is still down (Bull Trap Risk)."
        return "⚠️ RISK LIMIT: High volatility or low confidence scores triggered a safety override."
    return "✅ ALIGNED: Signal and Instruction are in sync with current risk parameters."

# 4. Popups
@st.dialog("Complete Technical Audit & Dictionary", width="large")
def show_full_audit(ticker, raw_data):
    d = raw_data[raw_data['symbol'] == ticker].sort_values('tradedate', ascending=False).iloc[0]
    st.subheader(f"Technical DNA: {ticker}")
    
    tab1, tab2 = st.tabs(["📊 Current Values", "📖 Field Definitions"])
    with tab1:
        cols = st.columns(3)
        for i, (col, val) in enumerate(d.items()):
            if col in ['grid_display', 'cell_val', 'date_str']: continue
            with cols[i % 3]:
                st.write(f"**{col}**")
                st.code(val)
    with tab2:
        st.write("**s_hybrid:** Daily Pulse Score (0-1)")
        st.write("**s_structural:** 60-Day Strength Score (0-1)")
        st.write("**kelly_fraction:** Math-based confidence sizing.")

# 5. Data Engine
@st.cache_data(ttl=60)
def load_data():
    try:
        creds = st.secrets["postgres"]
        conn = psycopg2.connect(host=creds["host"], port=creds["port"], database=creds["database"], 
                                user=creds["user"], password=creds["password"], sslmode="require")
        df = pd.read_sql("SELECT * FROM mpulse_execution_results ORDER BY tradedate ASC", conn)
        conn.close()
        
        if not df.empty:
            # CREATE PIVOT COLUMNS IMMEDIATELY ON LOAD
            df['date_str'] = df['tradedate'].astype(str)
            df['cell_val'] = df.apply(lambda r: f"{r['signal']} | 🛡️ {r['signal_60d']}", axis=1)
        return df
    except Exception as e:
        st.error(f"Database Error: {e}")
        return pd.DataFrame()

# --- LOAD DATA ---
raw_df = load_data()

# 6. Sidebar & Filters
with st.sidebar:
    st.title("Filters")
    search_query = st.text_input("🔍 Search Ticker").upper()
    sector_list = ["All"] + (sorted(raw_df['sector'].unique().tolist()) if not raw_df.empty else [])
    sel_sector = st.selectbox("Industry", sector_list)

# 7. Header Logic (Above the Grid)
header_placeholder = st.empty()

if not raw_df.empty:
    # APPLY FILTERS
    grid_data = raw_df.copy()
    if search_query:
        grid_data = grid_data[grid_data['symbol'].str.contains(search_query)]
    if sel_sector != "All":
        grid_data = grid_data[grid_data['sector'] == sel_sector]

    # 8. Matrix Rendering with Error Catching
    if not grid_data.empty:
        try:
            recent_dates = sorted(raw_df['date_str'].unique().tolist(), reverse=True)[:5]
            # Ensure index and columns actually exist in grid_data before pivoting
            pivot = grid_data.pivot_table(
                index=['symbol', 'sector'], 
                columns='date_str', 
                values='cell_val', 
                aggfunc='first'
            ).reset_index()

            # Ensure all 5 dates are present in pivot (if they exist in filtered data)
            available_dates = [d for d in recent_dates if d in pivot.columns]

            gb = GridOptionsBuilder.from_dataframe(pivot[['symbol', 'sector'] + available_dates])
            gb.configure_column("symbol", pinned="left", width=100)
            gb.configure_selection(selection_mode="single")
            for d_col in available_dates:
                gb.configure_column(d_col, width=200)

            st.markdown("### Market Matrix")
            grid_out = AgGrid(pivot, gridOptions=gb.build(), height=400, theme="alpine", update_mode=GridUpdateMode.SELECTION_CHANGED)

            # 9. Dynamic Header Update
            sel = grid_out.get('selected_rows')
            if sel is not None and (isinstance(sel, pd.DataFrame) and not sel.empty or len(sel) > 0):
                selected_ticker = (sel.iloc[0] if isinstance(sel, pd.DataFrame) else sel[0])['symbol']
                d = raw_df[raw_df['symbol'] == selected_ticker].sort_values('tradedate', ascending=False).iloc[0]
                
                reason = get_logic_reason(d['signal'], d['suggested_action'], d['final_regime'], d['signal_60d'])
                
                with header_placeholder.container():
                    c1, c2, c3 = st.columns([1.5, 2, 1])
                    with c1:
                        st.markdown(f"## {selected_ticker}")
                        st.button("🔬 Audit All Fields", on_click=show_full_audit, args=(selected_ticker, raw_df))
                    with c2:
                        st.markdown(f"""
                            <div class="instruction-box">
                                <strong>INSTRUCTION:</strong> {d['suggested_action']}<br>
                                <span class="reason-text">{reason}</span>
                            </div>
                        """, unsafe_allow_html=True)
                    with c3:
                        st.metric("Pulse Score", f"{d['s_hybrid']:.2f}")
                        st.metric("Structure", f"{d.get('s_structural', 0):.2f}")
                    st.markdown("---")
            else:
                header_placeholder.info("💡 Select a ticker in the matrix below to view instructions and audit details.")

        except KeyError as e:
            st.error(f"Filtering Error: The selected filter removed required data columns ({e}). Try a different search.")
    else:
        st.warning("No tickers found matching your search criteria.")
else:
    st.error("Wait... No data found in the database. Please check your ingestion pipeline.")
