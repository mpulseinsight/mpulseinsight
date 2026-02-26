import streamlit as st
import pandas as pd
import psycopg2
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

# 1. Page Config
st.set_page_config(page_title="mPulse Pro Console", layout="wide", initial_sidebar_state="collapsed")

# 2. State Management
if 'slider_state' not in st.session_state:
    st.session_state.slider_state = "open"

# 3. Enhanced CSS for the Slider and Typography
st.markdown("""
    <style>
        .hero-banner { background-color: #ffffff; border-bottom: 1px solid #DADCE0; padding: 10px 20px; margin: -3rem -5rem 1rem -5rem; display: flex; justify-content: space-between; align-items: center; }
        
        /* The Inspector (Slider) Styling */
        .inspector-container {
            background-color: #fcfcfc;
            border-left: 1px solid #eee;
            padding: 20px;
            height: 85vh;
            overflow-y: auto;
        }
        .instruction-box {
            background-color: #1A73E8;
            color: white !important;
            padding: 16px;
            border-radius: 12px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(26, 115, 232, 0.2);
        }
        .meta-row {
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid #f0f0f0;
        }
        .meta-label { color: #5F6368; font-size: 0.7rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; }
        .meta-value { color: #202124; font-size: 0.85rem; font-family: 'Monaco', monospace; font-weight: 600; }
        
        /* Buttons */
        .stButton>button { border-radius: 20px; }
    </style>
""", unsafe_allow_html=True)

# 4. Data Engine with Ranking Logic
@st.cache_data(ttl=60)
def load_and_rank_data():
    try:
        creds = st.secrets["postgres"]
        conn = psycopg2.connect(host=creds["host"], port=creds["port"], database=creds["database"], 
                                user=creds["user"], password=creds["password"], sslmode="require")
        df = pd.read_sql("SELECT * FROM mpulse_execution_results", conn)
        conn.close()
        
        if df.empty: return pd.DataFrame()

        # Convert dates and identify the last 5 days
        df['tradedate'] = pd.to_datetime(df['tradedate'])
        df['date_str'] = df['tradedate'].dt.strftime('%Y-%m-%d')
        
        # Ranking Logic: Map signals to numbers for sorting
        # BUY=5, BULLISH=4, HOLD=3, BEARISH=2, SELL=1
        rank_map = {'BUY': 5, 'BULLISH': 4, 'HOLD': 3, 'BEARISH': 2, 'SELL': 1}
        df['rank_score'] = df['signal'].str.upper().map(lambda x: next((v for k, v in rank_map.items() if k in str(x)), 0))
        
        return df
    except:
        return pd.DataFrame()

raw_df = load_and_rank_data()

# 5. Sidebar Filters
with st.sidebar:
    st.header("Intelligence Filters")
    trade_zone_only = st.checkbox("🚀 Show Trade Zone Only", value=False)
    search_input = st.text_input("🔍 Ticker Search").upper()
    st.divider()
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

# 6. Layout Definitions
if st.session_state.slider_state == "open":
    col_grid, col_meta = st.columns([2.2, 0.8])
else:
    col_grid, col_meta = st.columns([1, 0.0001])

# 7. Main Grid Logic
with col_grid:
    if not raw_df.empty:
        # Get only the 5 most recent dates across the whole dataset
        recent_5_dates = sorted(raw_df['date_str'].unique(), reverse=True)[:5]
        latest_date = recent_5_dates[0]

        # Filter DF to these 5 dates
        f_df = raw_df[raw_df['date_str'].isin(recent_5_dates)].copy()

        # Apply Trade Zone Filter (Strong Signals)
        if trade_zone_only:
            f_df = f_df[f_df['rank_score'] >= 4]

        if search_input:
            f_df = f_df[f_df['symbol'].str.contains(search_input)]

        # Pivot the data
        pivot = f_df.pivot_table(
            index=['symbol', 'sector'], 
            columns='date_str', 
            values='signal', 
            aggfunc='first'
        ).reset_index()

        # Add ranking back to the pivot for sorting the grid
        # We sort based on the signal of the MOST RECENT date
        latest_ranks = f_df[f_df['date_str'] == latest_date][['symbol', 'rank_score']]
        pivot = pivot.merge(latest_ranks, on='symbol', how='left').sort_values(by='rank_score', ascending=False)

        # AG-Grid Configuration
        gb = GridOptionsBuilder.from_dataframe(pivot.drop(columns=['rank_score']))
        gb.configure_default_column(resizable=True, filterable=True)
        gb.configure_column("symbol", pinned="left", width=100, headerName="Ticker")
        gb.configure_selection(selection_mode="single", use_checkbox=False)
        
        js_color = JsCode("""
        function(params) {
            if (!params.value) return {};
            const v = params.value.toUpperCase();
            if (v.includes('BUY') || v.includes('BULLISH')) return {backgroundColor: '#E6F4EA', color: '#137333', fontWeight: 'bold'};
            if (v.includes('SELL') || v.includes('BEARISH')) return {backgroundColor: '#FCE8E6', color: '#C5221F', fontWeight: 'bold'};
            return {color: '#5F6368'};
        }
        """)
        
        for d in recent_5_dates:
            gb.configure_column(d, cellStyle=js_color, width=130)

        # Toggle Button
        btn_label = "Close Inspector" if st.session_state.slider_state == "open" else "Open Inspector"
        if st.button(btn_label):
            st.session_state.slider_state = "closed" if st.session_state.slider_state == "open" else "open"
            st.rerun()

        grid_resp = AgGrid(
            pivot, 
            gridOptions=gb.build(), 
            height=600, 
            theme="balham", 
            allow_unsafe_jscode=True, 
            update_mode=GridUpdateMode.SELECTION_CHANGED
        )

# 8. Fixed Asset Inspector (The Slider)
if st.session_state.slider_state == "open":
    with col_meta:
        st.markdown('<div class="inspector-container">', unsafe_allow_html=True)
        selection = grid_resp.get('selected_rows')
        
        # Handle AgGrid Selection differences
        selected_row = None
        if selection is not None:
            if isinstance(selection, pd.DataFrame) and not selection.empty:
                selected_row = selection.iloc[0]
            elif isinstance(selection, list) and len(selection) > 0:
                selected_row = selection[0]

        if selected_row:
            ticker = selected_row['symbol']
            # Get latest data for this ticker
            data = raw_df[(raw_df['symbol'] == ticker) & (raw_df['date_str'] == latest_date)].iloc[0]
            
            # Meaningful Info Logic: Fix "Stay Cash" frustration
            raw_action = str(data.get('suggested_action', 'HOLD')).upper()
            sig = str(data.get('signal', '')).upper()
            
            # Override "Stay Cash" text if signal is actually Bullish
            if "BULLISH" in sig or "BUY" in sig:
                display_action = "PREPARING ENTRY" if "CASH" in raw_action else raw_action
                context = "Technical strength detected. Waiting for volume/macro confirmation."
            else:
                display_action = raw_action
                context = data.get('execution_stance', '')

            st.markdown(f"""
                <div class="instruction-box">
                    <small style="opacity:0.8; font-size:0.7rem; text-transform:uppercase;">Intelligent Action</small><br>
                    <b style="font-size:1.3rem;">{display_action}</b>
                    <div style="font-size:0.85rem; margin-top:8px; line-height:1.2; opacity:0.9;">{context}</div>
                </div>
                <h4 style="font-size:0.9rem; color:#1A73E8;">Technical Factors</h4>
            """, unsafe_allow_html=True)

            # Metadata Table
            for k, v in data.items():
                if k in ['date_str', 'tradedate', 'symbol', 'rank_score']: continue
                val_str = f"{v:.4f}" if isinstance(v, float) else str(v)
                st.markdown(f"""
                    <div class="meta-row">
                        <span class="meta-label">{k.replace('_', ' ')}</span>
                        <span class="meta-value">{val_str}</span>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Select a ticker to view technical insights.")
        
        st.markdown('</div>', unsafe_allow_html=True)
