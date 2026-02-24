import streamlit as st
import pandas as pd
import psycopg2
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode
import numpy as np

# 1. Page Configuration
st.set_page_config(page_title="mPulse Console", layout="wide", initial_sidebar_state="expanded")

# 2. Enhanced UI Styling
st.markdown("""
    <style>
        .main { background-color: #f4f7f9; }
        .stMetric { background-color: #ffffff; padding: 10px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
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
    </style>
""", unsafe_allow_html=True)

# 3. Plain English Mappings
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
    '⚡ HIGH CONVICTION BUY': '#10b981',
    'BULLISH': '#059669',
    '🛡️ STRUCTURAL_BUY': '#3b82f6',
    'NEUTRAL': '#eab308',
    'BEARISH': '#ef4444',
    'EXHAUSTED': '#f97316',
    'WEAK_SECTOR_BREADTH': '#f59e0b',
    'AVOID': '#dc2626'
}

def explain_signal(signal, perspective):
    explanations = {
        '⚡ HIGH CONVICTION BUY': "🚀 **Buy Now!** All 3 keys aligned: Big investors buying, low risk, perfect market timing.",
        'BULLISH': "📈 **Good Setup.** Momentum building, but wait for full alignment.",
        '🛡️ STRUCTURAL_BUY': "🏗️ **Long-Term Hold.** Strong business + sector support for 60+ days.",
        'NEUTRAL': "⏳ **Wait & Watch.** Not yet aligned.",
        'BEARISH': "📉 **Exit Position.** Risk outweighs reward.",
        'EXHAUSTED': "🔥 **Too Hot.** Wait for pullback.",
        'WEAK_SECTOR_BREADTH': "🏚️ **Sector Weak.** Avoid until peers recover.",
        'AVOID': "❌ **No Trade.** Multiple red flags."
    }
    return explanations.get(signal, "📊 **Analyzing...**")

# 4. SAFE Data Loading with Column Validation
@st.cache_data(ttl=60)
def load_data():
    try:
        creds = st.secrets["postgres"]
        conn = psycopg2.connect(host=creds["host"], port=creds["port"], database=creds["database"], 
                                user=creds["user"], password=creds["password"], sslmode="require")
        df = pd.read_sql("SELECT * FROM mpulse_execution_results ORDER BY tradedate DESC", conn)
        conn.close()
        
        if not df.empty:
            # Safe datetime conversion
            df['tradedate'] = pd.to_datetime(df['tradedate'], errors='coerce')
            df['date_str'] = df['tradedate'].dt.strftime('%Y-%m-%d')
            
            # Debug: Show available columns
            st.info(f"✅ Loaded {len(df)} rows with columns: {list(df.columns)[:10]}...")
        
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
        index=0
    )
    st.markdown("---")
    search_ticker = st.text_input("🔍 Ticker", value="").upper()
    if not raw_df.empty:
        sector_filter = st.multiselect(
            "📂 Sector", 
            raw_df['sector'].unique(),
            default=[]
        )

# 6. SAFE Top Banner (Column Existence Checks)
if not raw_df.empty:
    latest = raw_df.drop_duplicates('symbol', keep='last')
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # Safe regime access
        regime = latest['final_regime'].iloc[0] if 'final_regime' in latest.columns else 'UNKNOWN'
        st.markdown(f"""
            <div class='instruction-banner'>
                <div style='font-size: 0.85em;'>Market Regime</div>
                <div style='font-size: 1.4em;'>{regime}</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col2:
        # Safe VIX access
        vix_val = latest['vix'].iloc[0] if 'vix' in latest.columns else 0
        st.metric("VIX", f"{vix_val:.1f}")
    
    with col3:
        # Safe buy signal count
        buy_signals = 0
        if 'signal' in latest.columns:
            buy_signals = len(latest[latest['signal'].isin(['⚡ HIGH CONVICTION BUY', 'BULLISH'])])
        st.metric("Buy Signals", buy_signals)
    
    with col4:
        # Safe high conviction count
        high_conv = 0
        if 'confidence_pct' in latest.columns:
            high_conv = len(latest[latest['confidence_pct'] >= 85])
        st.metric("High Conviction", high_conv)

# 7. Main Layout
col_left, col_right = st.columns([3, 1.3])

if not raw_df.empty:
    # Safe filtering
    df_filtered = raw_df.copy()
    if search_ticker and 'symbol' in df_filtered.columns:
        df_filtered = df_filtered[df_filtered['symbol'].str.contains(search_ticker, na=False)]
    if len(sector_filter) > 0 and 'sector' in df_filtered.columns:
        df_filtered = df_filtered[df_filtered['sector'].isin(sector_filter)]
    
    # Safe recent dates
    recent_dates = sorted(df_filtered['date_str'].dropna().unique())[-5:]
    
    # Determine signal column safely
    signal_col = 'signal' if "Daily" in perspective else 'signal_60d'
    if signal_col not in df_filtered.columns:
        signal_col = 'signal' if 'signal' in df_filtered.columns else None
    
    if signal_col:
        pivot_df = df_filtered.pivot_table(
            index=['symbol', 'sector'], 
            columns='date_str', 
            values=signal_col,
            aggfunc='last'
        ).fillna('').reset_index()
        
        with col_left:
            st.markdown("### 📈 Signal Matrix")
            
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
            if 'sector' in pivot_df.columns:
                gb.configure_column("sector", pinned="left", width=120, headerName="Sector")
            
            for date_col in recent_dates:
                if date_col in pivot_df.columns:
                    gb.configure_column(date_col, cellStyle=cell_style_js, width=140)
            
            grid_response = AgGrid(
                pivot_df, 
                gridOptions=gb.build(), 
                height=650, 
                theme="streamlit", 
                allow_unsafe_jscode=True
            )
        
        # Right panel
        with col_right:
            st.markdown("### 📊 Signal Audit")
            selected_rows = grid_response['selected_rows']
            
            if selected_rows:
                row_data = selected_rows[0] if isinstance(selected_rows, list) else selected_rows
                symbol = row_data['symbol']
                
                # Safe symbol lookup
                symbol_data = raw_df[raw_df['symbol'] == symbol]
                if not symbol_data.empty:
                    latest_symbol_data = symbol_data.iloc[0]
                    
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
                    
                    st.markdown("**Key Factors:**")
                    for key in ['confidence_pct', 's_hybrid', 's_structural', 'sector_strength']:
                        if key in latest_symbol_data and pd.notna(latest_symbol_data[key]):
                            label = FACTOR_LABELS.get(key, key.replace('_', ' ').title())
                            value = float(latest_symbol_data[key])
                            val_str = f"{value:.1f}"
                            color = '🟢' if value > 70 else '🟡' if value > 40 else '🔴'
                            st.markdown(f"**{label}:** {color} {val_str}")
                    
                    st.markdown("---")
                    st.markdown(f"**Regime:** {latest_symbol_data.get('final_regime', 'N/A')}")
                    st.markdown(f"**Action:** {latest_symbol_data.get('action', 'N/A')}")
            else:
                st.info("👆 Click a **Ticker** row to see signal analysis")
    else:
        st.warning("No signal columns found in data")
else:
    st.warning("No data loaded. Check database connection.")
