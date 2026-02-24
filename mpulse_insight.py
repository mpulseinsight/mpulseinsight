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
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            color: white;
            padding: 15px;
            border-radius: 12px;
            margin-bottom: 20px;
            text-align: center;
            font-weight: 600;
        }
        .signal-header {
            padding: 12px 16px;
            border-radius: 8px;
            margin-bottom: 16px;
            font-size: 1.2em;
            font-weight: bold;
        }
        .metric-container { margin-bottom: 8px; }
    </style>
""", unsafe_allow_html=True)

# 3. Plain English Mappings (Common Man Terms)
FACTOR_LABELS = {
    's_hybrid': 'Overall Score (Daily)',
    's_structural': 'Business Strength (60D)',
    'confidence_pct': 'Conviction Level',
    'sector_strength': 'Sector Health %',
    'smart_money_score': 'Big Investor Activity',
    'pipeline_score': 'Growth Pipeline',
    'f_score': 'Financial Quality',
    'risk_score': 'Risk Level',
    'gv_score': 'Growth vs Value Balance'
}

SIGNAL_COLORS = {
    '⚡ HIGH CONVICTION BUY': '#10b981',  # Green
    'BULLISH': '#059669',                # Dark Green
    '🛡️ STRUCTURAL_BUY': '#3b82f6',      # Blue
    'NEUTRAL': '#eab308',                # Yellow
    'BEARISH': '#ef4444',                # Red
    'EXHAUSTED': '#f97316',              # Orange
    'WEAK_SECTOR_BREADTH': '#f59e0b',    # Amber
    'AVOID': '#dc2626'                   # Dark Red
}

def explain_signal(signal, perspective):
    if 'HIGH CONVICTION BUY' in signal:
        return "🚀 **Buy Now!** All 3 keys aligned: Big investors buying, low risk, perfect market timing."
    elif 'BULLISH' in signal:
        return "📈 **Good Setup.** Momentum building, but wait for full alignment."
    elif 'STRUCTURAL_BUY' in signal:
        return "🏗️ **Long-Term Hold.** Strong business + sector support for 60+ days."
    elif 'NEUTRAL' in signal:
        return "⏳ **Wait & Watch.** Not yet aligned."
    elif 'BEARISH' in signal:
        return "📉 **Exit Position.** Risk outweighs reward."
    elif 'EXHAUSTED' in signal:
        return "🔥 **Too Hot.** Wait for pullback."
    elif 'WEAK_SECTOR_BREADTH' in signal:
        return "🏚️ **Sector Weak.** Avoid until peers recover."
    else:
        return "❌ **No Trade.** Multiple red flags."

# 4. FIXED Data Loading
@st.cache_data(ttl=60)
def load_data():
    try:
        creds = st.secrets["postgres"]
        conn = psycopg2.connect(host=creds["host"], port=creds["port"], database=creds["database"], 
                                user=creds["user"], password=creds["password"], sslmode="require")
        df = pd.read_sql("SELECT * FROM mpulse_execution_results ORDER BY tradedate DESC", conn)
        conn.close()
        
        if not df.empty:
            # FIX: Convert tradedate to datetime FIRST, THEN format
            df['tradedate'] = pd.to_datetime(df['tradedate'], errors='coerce')
            df['date_str'] = df['tradedate'].dt.strftime('%Y-%m-%d')
            
        return df
    except Exception as e:
        st.error(f"DB Error: {e}")
        return pd.DataFrame()

raw_df = load_data()

# 5. Sidebar: Controls
with st.sidebar:
    st.title("🎯 Signal Console")
    perspective = st.radio(
        "📊 View Mode",
        ["Daily Signals ⚡", "60-Day Signals 🛡️", "Combined View 🔄"],
        index=0,
        help="Daily: Tactical trades | 60D: Long holds | Combined: Both horizons"
    )
    st.markdown("---")
    search_ticker = st.text_input("🔍 Ticker", value="").upper()
    sector_filter = st.multiselect(
        "📂 Sector", 
        raw_df['sector'].unique() if not raw_df.empty else [],
        default=[]
    )

# 6. Top Banner: Market Context + Signal Summary
if not raw_df.empty:
    latest = raw_df.drop_duplicates('symbol', keep='last')
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        regime = latest.iloc[0]['final_regime']
        st.markdown(f"""
            <div class='instruction-banner'>
                <div style='font-size: 0.85em;'>Market Regime</div>
                <div style='font-size: 1.4em;'>{regime}</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.metric("VIX", f"{latest.iloc[0]['vix']:.1f}", delta=None)
    
    with col3:
        buy_count = len(latest[latest['signal'].isin(['⚡ HIGH CONVICTION BUY', 'BULLISH'])])
        st.metric("Buy Signals", buy_count)
    
    with col4:
        high_conv = len(latest[latest['confidence_pct'] >= 85])
        st.metric("High Conviction", high_conv)

# 7. Main Layout: Grid (Left 70%) + Audit (Right 30%)
col_left, col_right = st.columns([3, 1.3])

if not raw_df.empty:
    # Filter data
    df_filtered = raw_df.copy()
    if search_ticker:
        df_filtered = df_filtered[df_filtered['symbol'].str.contains(search_ticker, na=False)]
    if len(sector_filter) > 0:
        df_filtered = df_filtered[df_filtered['sector'].isin(sector_filter)]
    
    # Get recent dates (5 latest)
    recent_dates = sorted(df_filtered['date_str'].dropna().unique())[-5:]
    
    # Pivot for matrix
    pivot_df = df_filtered.pivot_table(
        index=['symbol', 'sector'], 
        columns='date_str', 
        values='signal' if "Daily" in perspective else 'signal_60d',
        aggfunc='last'
    ).fillna('').reset_index()
    
    with col_left:
        st.markdown("### 📈 Signal Matrix")
        
        # Color coding for cells
        cell_style_js = JsCode("""
        function(params) {
            const val = params.value;
            if (!val) return {};
            
            const colors = {
                '⚡ HIGH CONVICTION BUY': {'bg': '#10b981', 'color': 'white'},
                'BULLISH': {'bg': '#059669', 'color': 'white'},
                '🛡️ STRUCTURAL_BUY': {'bg': '#3b82f6', 'color': 'white'},
                'NEUTRAL': {'bg': '#eab308', 'color': 'black'},
                'BEARISH': {'bg': '#ef4444', 'color': 'white'},
                'EXHAUSTED': {'bg': '#f97316', 'color': 'white'},
                'WEAK_SECTOR_BREADTH': {'bg': '#f59e0b', 'color': 'white'},
                'AVOID': {'bg': '#dc2626', 'color': 'white'}
            };
            
            return colors[val] || {};
        }
        """)
        
        gb = GridOptionsBuilder.from_dataframe(pivot_df)
        gb.configure_column("symbol", pinned="left", width=100, headerName="Ticker")
        gb.configure_column("sector", pinned="left", width=120, headerName="Sector")
        
        # Color ALL date columns
        for date_col in recent_dates:
            if date_col in pivot_df.columns:
                gb.configure_column(date_col, cellStyle=cell_style_js, width=140)
        
        gb.configure_grid_options(domLayout='normal', suppressRowClickSelection=True)
        
        grid_response = AgGrid(
            pivot_df, 
            gridOptions=gb.build(), 
            height=650, 
            theme="streamlit", 
            allow_unsafe_jscode=True
        )
    
    # 8. Right Panel: Selected Signal Audit (Vertical Grid)
    with col_right:
        st.markdown("### 📊 Signal Audit")
        
        selected_rows = grid_response['selected_rows']
        if selected_rows:
            row_data = selected_rows[0] if isinstance(selected_rows, list) else selected_rows
            
            # Find latest data for this symbol
            symbol = row_data['symbol']
            latest_symbol_data = raw_df[raw_df['symbol'] == symbol].dropna(subset=['tradedate']).iloc[0]
            
            # Top: Signal Header with Color + Explanation
            current_signal = latest_symbol_data.get('signal', 'NEUTRAL')
            signal_color = SIGNAL_COLORS.get(current_signal, '#6b7280')
            
            st.markdown(f"""
                <div class='signal-header' style='
                    background-color: {signal_color}; 
                    color: white; 
                    text-align: center;
                    margin-bottom: 16px;
                '>
                    {current_signal}
                </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"**What to do:** {explain_signal(current_signal, perspective)}")
            
            # Vertical Metrics Grid (Common Man Terms)
            st.markdown("**Key Factors:**")
            metrics_data = {
                'confidence_pct': latest_symbol_data.get('confidence_pct', 0),
                's_hybrid': latest_symbol_data.get('s_hybrid', 0),
                's_structural': latest_symbol_data.get('s_structural', 0),
                'sector_strength': latest_symbol_data.get('sector_strength', 0),
                'smart_money_score': latest_symbol_data.get('smart_money_score', 0),
                'pipeline_score': latest_symbol_data.get('pipeline_score', 0),
                'f_score': latest_symbol_data.get('f_score', 0),
                'risk_score': latest_symbol_data.get('risk_score', 0)
            }
            
            for key, value in metrics_data.items():
                if pd.notna(value) and value is not None:
                    label = FACTOR_LABELS.get(key, key.replace('_', ' ').title())
                    val_str = f"{float(value):.1f}" if isinstance(value, (int, float)) else str(value)
                    color = '🟢' if float(value) > 70 else '🟡' if float(value) > 40 else '🔴'
                    
                    st.markdown(f"**{label}:** {color} {val_str}")
            
            # Regime & Action
            st.markdown("---")
            st.markdown(f"**Market Regime:** {latest_symbol_data.get('final_regime', 'N/A')}")
            st.markdown(f"**Recommended Action:** {latest_symbol_data.get('action', 'N/A')}")
            
        else:
            st.info("👆 Click a **Ticker** row to see its full signal analysis")
else:
    st.warning("No data loaded. Check database connection.")
