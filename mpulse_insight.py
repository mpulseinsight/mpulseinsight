import streamlit as st
import pandas as pd
import psycopg2
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

# 1. Page Configuration
st.set_page_config(page_title="mPulse Pro v3.1", layout="wide", initial_sidebar_state="expanded")

# 2. HARDENED CSS (Forcing Black Text and Zero Margins)
st.markdown("""
    <style>
        /* Force Global Font Visibility */
        html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
            background-color: #FFFFFF !important;
        }
        
        /* Remove Top Header */
        header, [data-testid="stToolbar"], [data-testid="stDecoration"] { display: none !important; }
        .block-container { padding-top: 0rem !important; margin-top: -20px; }

        /* Force Sidebar Text Visibility */
        [data-testid="stSidebar"] { background-color: #F8F9FA !important; border-right: 1px solid #DADCE0; }
        [data-testid="stSidebar"] * { color: #202124 !important; }

        /* Force Dropdown Visibility (Fixes the 'Blank' Font Issue) */
        div[data-baseweb="select"] * { color: #202124 !important; font-weight: 600 !important; }
        div[role="listbox"] * { color: #202124 !important; background-color: #FFFFFF !important; }

        /* Force Dialog/Popup Visibility */
        div[role="dialog"] { background-color: #FFFFFF !important; color: #202124 !important; border: 1px solid #DADCE0; }
        div[role="dialog"] * { color: #202124 !important; }

        /* Metric Contrast */
        [data-testid="stMetricValue"] { color: #1A73E8 !important; font-weight: 800 !important; }
        [data-testid="stMetricLabel"] { color: #5F6368 !important; font-weight: 700 !important; }

        /* Button Hardening */
        div.stButton > button {
            background-color: #1A73E8 !important; color: #FFFFFF !important;
            border-radius: 4px !important; font-weight: 700 !important;
        }
    </style>
""", unsafe_allow_html=True)

# 3. Sidebar Dictionary (Updated for Dual-Horizon)
with st.sidebar:
    st.markdown('<h2 style="color:#202124; margin-bottom:5px;">📖 Dictionary</h2>', unsafe_allow_html=True)
    dict_html = """
    <div style="background-color:#FFFFFF; border:1px solid #DADCE0; padding:10px; border-radius:5px;">
        <table style="width:100%; border-collapse:collapse; color:#202124; font-size:14px;">
            <tr style="border-bottom:1px solid #EEEEEE;"><td>⚡ <b>Tactical</b></td><td style="text-align:right;">Daily Bounce</td></tr>
            <tr style="border-bottom:1px solid #EEEEEE;"><td>🛡️ <b>Structural</b></td><td style="text-align:right;">60-Day Hold</td></tr>
            <tr style="border-bottom:1px solid #EEEEEE;"><td>👑 <b>Core Long</b></td><td style="text-align:right;">Daily + 60D Match</td></tr>
            <tr style="border-bottom:1px solid #EEEEEE;"><td>🤝 <b>Breadth</b></td><td style="text-align:right;">Sector Support %</td></tr>
            <tr style="border-bottom:1px solid #EEEEEE;"><td>📉 <b>Vol Scale</b></td><td style="text-align:right;">Beta Penalty</td></tr>
            <tr style="border-bottom:1px solid #EEEEEE;"><td>🎯 <b>Confidence</b></td><td style="text-align:right;">0 - 100%</td></tr>
        </table>
    </div>
    """
    st.markdown(dict_html, unsafe_allow_html=True)
    st.markdown('<p style="color:#5F6368; font-size:11px; margin-top:10px;">CORE LONG represents maximum alignment (Size 1.0x).</p>', unsafe_allow_html=True)

# 4. Data Engine
@st.cache_resource
def get_db_connection():
    try:
        creds = st.secrets["postgres"]
        return psycopg2.connect(host=creds["host"], port=creds["port"], database=creds["database"],
                                user=creds["user"], password=creds["password"], sslmode="require")
    except: return None

@st.cache_data(ttl=60)
def load_data():
    conn = get_db_connection()
    if not conn: return pd.DataFrame(), pd.DataFrame()
    df = pd.read_sql("SELECT * FROM mpulse_execution_results ORDER BY asatdate ASC", conn)
    df['date_str'] = df['asatdate'].astype(str)
    
    # Pivot to show 'execution_stance' instead of just signal for the top-level view
    pivot = df.pivot_table(index=['symbol', 'sector'], columns='date_str', values='execution_stance', aggfunc='first').reset_index().fillna('')
    cols = [c for c in pivot.columns if c not in ['symbol', 'sector']]
    recent = sorted(cols, reverse=True)[:5]
    return df, pivot[['symbol', 'sector'] + sorted(recent)]

raw_df, pivot_5_df = load_data()

# 5. Fixed History Dialog (Updated for Audit Columns)
@st.dialog("Full Audit Trail", width="large")
def show_audit(symbol):
    st.markdown(f'<h2 style="color:#202124;">Activity Log: {symbol}</h2>', unsafe_allow_html=True)
    data = raw_df[raw_df['symbol'] == symbol].sort_values('asatdate', ascending=False).head(20)
    
    if data.empty:
        st.warning("No records found in database for this ticker.")
    else:
        disp_df = data[['asatdate', 'execution_stance', 'signal', 'signal_60d', 'final_weight']].rename(columns={
            'asatdate': 'Date', 'execution_stance': 'Stance', 'signal': 'Daily', 'signal_60d': '60-Day', 'final_weight': 'Alloc %'
        })
        st.dataframe(disp_df, use_container_width=True, hide_index=True)

# 6. Upper Space Navigation
m1, m2, m3, m4 = st.columns([1, 1, 1, 1])
with m1: search = st.text_input("🔍 Ticker Search", placeholder="AAPL...").upper()
with m2: sector = st.selectbox("📁 Sector", options=["All Sectors"] + sorted(pivot_5_df['sector'].unique().tolist()))
with m3: st.metric("Market Fear (VIX)", f"{raw_df['vix'].iloc[-1]:.2f}" if not raw_df.empty else "0.00")
with m4: st.metric("Regime Status", f"{raw_df['final_regime'].iloc[-1]}" if not raw_df.empty else "N/A")

# 7. Main Dashboard Split
col_grid, col_intel = st.columns([1.5, 1.5])

filtered = pivot_5_df.copy()
if search: filtered = filtered[filtered['symbol'].str.contains(search)]
if sector != "All Sectors": filtered = filtered[filtered['sector'] == sector]

with col_grid:
    st.markdown('<h3 style="color:#202124; margin-bottom:5px;">🗓️ Execution Matrix</h3>', unsafe_allow_html=True)
    gb = GridOptionsBuilder.from_dataframe(filtered)
    gb.configure_column("symbol", pinned="left", width=90)
    
    js_style = JsCode("""
    function(params) {
        if (!params.value) return {};
        const v = params.value.toUpperCase();
        if (v.includes('CORE_LONG')) return {backgroundColor: '#FEF7E0', color: '#B06000', fontWeight: 'bold'};
        if (v.includes('STRUCTURAL')) return {backgroundColor: '#E6F4EA', color: '#137333', fontWeight: 'bold'};
        if (v.includes('TACTICAL')) return {backgroundColor: '#E8F0FE', color: '#1A73E8', fontWeight: 'bold'};
        if (v.includes('WATCH')) return {backgroundColor: '#F8F9FA', color: '#5F6368'};
        return {backgroundColor: '#FFFFFF', color: '#3C4043'};
    }
    """)
    for c in [x for x in filtered.columns if x not in ['symbol', 'sector']]:
        gb.configure_column(c, cellStyle=js_style, width=120)
    
    gb.configure_selection(selection_mode="single")
    grid_out = AgGrid(
        filtered, gridOptions=gb.build(), update_mode=GridUpdateMode.SELECTION_CHANGED, 
        allow_unsafe_jscode=True, theme="alpine", height=650, fit_columns_on_grid_load=True
    )

with col_intel:
    sel = grid_out.get('selected_rows')
    if sel is not None and len(sel) > 0:
        row_data = sel.iloc[0] if isinstance(sel, pd.DataFrame) else sel[0]
        ticker = row_data['symbol']
        
        c_head, c_btn = st.columns([1.5, 1])
        with c_head: st.markdown(f'<h2 style="color:#202124; margin:0;">{ticker}</h2>', unsafe_allow_html=True)
        with c_btn: 
            if st.button("📊 VIEW FULL HISTORY"): show_audit(ticker)
        
        hist = raw_df[raw_df['symbol'] == ticker].sort_values('asatdate', ascending=False)
        date = st.selectbox("Review Date", options=hist['date_str'].tolist()[:10])
        d = hist[hist['date_str'] == date].iloc[0]

        # --- EXECUTION BLOCK (Top Focus) ---
        stance_color = "#137333" if "LONG" in d['execution_stance'] or "STRUCTURAL" in d['execution_stance'] else "#1A73E8" if "TACTICAL" in d['execution_stance'] else "#5F6368"
        st.markdown(f'''
        <div style="margin-top:10px; padding:15px; background-color:#F8F9FA; border-left: 5px solid {stance_color}; border-radius:4px; border-top:1px solid #DADCE0; border-right:1px solid #DADCE0; border-bottom:1px solid #DADCE0;">
            <p style="color:#5F6368; font-size:12px; margin:0; text-transform:uppercase; font-weight:700;">Action Plan</p>
            <h3 style="color:{stance_color}; margin:0;">{d["suggested_action"]} ({d["execution_stance"]})</h3>
            <p style="color:#202124; font-size:13px; margin-top:5px; margin-bottom:0;"><b>Target Wt:</b> {d["final_weight"]:.2%} | <b>Confidence:</b> {d.get("kelly_fraction", 0)*100:.0f}%</p>
        </div>
        ''', unsafe_allow_html=True)

        st.markdown("<hr style='margin: 15px 0px; border-color: #DADCE0;'>", unsafe_allow_html=True)

        # --- DUAL HORIZON SPLIT ---
        col_daily, col_60d = st.columns(2)
        
        with col_daily:
            st.markdown('<h4 style="color:#202124; margin-bottom:5px;">⚡ Daily Tactical</h4>', unsafe_allow_html=True)
            st.markdown(f'<p style="color:#1A73E8; font-weight:bold; margin:0;">{d["signal"]}</p>', unsafe_allow_html=True)
            st.markdown(f'<p style="color:#5F6368; font-size:12px;">Score: {d["s_hybrid"]:.4f}</p>', unsafe_allow_html=True)
            
            st.progress(min(max(float(d['s_hybrid']), 0.0), 1.0))
            st.markdown(f'<p style="color:#202124; font-size:13px; margin-top:10px;"><b>Smart Money:</b> {d["smart_money_score"]:.1f}</p>', unsafe_allow_html=True)
            st.markdown(f'<p style="color:#202124; font-size:13px;"><b>Risk Score:</b> {d["risk_score"]*100:.1f}</p>', unsafe_allow_html=True)

        with col_60d:
            st.markdown('<h4 style="color:#202124; margin-bottom:5px;">🛡️ 60-Day Structural</h4>', unsafe_allow_html=True)
            st.markdown(f'<p style="color:#137333; font-weight:bold; margin:0;">{d["signal_60d"]}</p>', unsafe_allow_html=True)
            st.markdown(f'<p style="color:#5F6368; font-size:12px;">Score: {d.get("s_structural", 0):.4f}</p>', unsafe_allow_html=True)
            
            st.progress(min(max(float(d.get('s_structural', 0)), 0.0), 1.0))
            st.markdown(f'<p style="color:#202124; font-size:13px; margin-top:10px;"><b>Sector Breadth:</b> {d.get("sector_strength", 0)*100:.1f}%</p>', unsafe_allow_html=True)
            st.markdown(f'<p style="color:#202124; font-size:13px;"><b>Business Health:</b> {d["f_score"]:.1f}</p>', unsafe_allow_html=True)

        # --- MATH AUDIT TRAIL ---
        with st.expander("🔍 View Sizing Audit Trail"):
            st.markdown(f"""
            <div style="color:#202124; font-size:13px;">
                <p><b>1. Base Kelly (Confidence):</b> {d.get('w_kelly', 0):.4%}</p>
                <p><b>2. Beta Volatility Adj:</b> x {d.get('vol_scale', 1):.2f}</p>
                <p><b>3. Pre-Sector Weight:</b> = {d.get('w_final_pre_sector', 0):.4%}</p>
                <p><b>4. Sector Penalty applied:</b> x {d.get('sector_penalty', 1):.1f}</p>
                <p style="color:#1A73E8; font-weight:bold; border-top:1px solid #DADCE0; padding-top:5px;">Final Allocated Weight: {d["final_weight"]:.4%}</p>
            </div>
            """, unsafe_allow_html=True)
            
    else:
        st.markdown('<div style="padding:20px; border:1px dashed #DADCE0; text-align:center; color:#5F6368;">Select a Ticker to load Dual-Horizon Intelligence</div>', unsafe_allow_html=True)
