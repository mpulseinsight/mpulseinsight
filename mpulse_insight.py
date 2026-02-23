import streamlit as st
import pandas as pd
import psycopg2
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

# 1. Page Configuration & Professional Right-Side Sidebar
st.set_page_config(page_title="mPulse Insight Terminal", layout="wide")

st.markdown("""
    <style>
        [data-testid="stSidebar"] { left: auto; right: 0; border-left: 1px solid #464e5f; width: 450px !important; }
        section[data-testid="stSidebar"] > div { padding-top: 1rem; }
    </style>
""", unsafe_allow_html=True)

# 2. Database Connection
@st.cache_resource
def get_db_connection():
    return psycopg2.connect(
        host="mpulseinsight.cw94024som2q.us-east-1.rds.amazonaws.com",
        port=5432, dbname="postgres", user="postgres", 
        password="mpulseinsight", sslmode="require"
    )

# 3. Data Loading & Horizontal Pivot
@st.cache_data(ttl=300)
def load_mpulse_data():
    conn = get_db_connection()
    # Pulling all columns from your specific table
    query = """
        SELECT symbol, sector, asatdate, signal, 
               s_hybrid, f_score, gv_score, analyst_score, 
               kelly_fraction, final_weight, vix_regime, trend_regime
        FROM mpulse_execution_results 
        WHERE asatdate >= CURRENT_DATE - INTERVAL '30 days'
        ORDER BY asatdate ASC
    """
    raw_df = pd.read_sql(query, conn)
    raw_df['date_str'] = pd.to_datetime(raw_df['asatdate']).dt.strftime('%Y-%m-%d')
    
    # Pivot: Symbols as rows, Dates as columns, Signal as the value
    pivot_df = raw_df.pivot_table(
        index=['symbol', 'sector'], 
        columns='date_str', 
        values='signal', 
        aggfunc='first'
    ).reset_index().fillna('')
    
    return pivot_df, raw_df

# 4. "Common Man" Narrative Engine
def get_plain_english_verdict(row):
    """Translates DB scores into human recommendations."""
    # Hybrid score represents the core strength (typically 0-1 range)
    strength = row.get('s_hybrid', 0)
    sig = str(row.get('signal', '')).upper()
    
    if "BUY" in sig:
        if strength > 0.8: return "🟢 STRONGLY RECOMMENDED", "Top-tier setup. High fundamental quality meets strong price momentum."
        if strength > 0.5: return "✅ WORTH BUYING", "Solid signal with healthy institutional backing."
        return "⚖️ SPECULATIVE BUY", "Entering a positive trend, but exercise caution with position size."
    elif "SELL" in sig:
        return "🛑 STRONGLY AVOID", "The system detects a trend breakdown. Protect your capital and stay away."
    return "⏳ WAITING", "No clear edge. The stock is currently in a neutral noise zone."

# 5. UI Layout
st.title("⚡ mPulse Signal Timeline")
st.info("👈 **Drilldown:** Click a row to see the plain-English 'Why' behind the signals in the right panel.")

try:
    pivot_df, raw_df = load_mpulse_data()
    date_cols = [c for c in pivot_df.columns if c not in ['symbol', 'sector']]

    # AG Grid Config
    gb = GridOptionsBuilder.from_dataframe(pivot_df)
    gb.configure_column("symbol", pinned="left", headerName="Ticker", width=120)
    gb.configure_column("sector", headerName="Sector", width=150, rowGroup=True) # Enables Grouping
    
    # Heatmap Coloring
    cell_style = JsCode("""
    function(params) {
        if (!params.value) return {};
        const val = params.value.toUpperCase();
        if (val.includes('BUY')) return {backgroundColor: '#1b5e20', color: 'white', fontWeight: 'bold'};
        if (val.includes('SELL')) return {backgroundColor: '#b71c1c', color: 'white', fontWeight: 'bold'};
        return {backgroundColor: '#f9a825', color: 'black'};
    }
    """)
    for d_col in date_cols:
        gb.configure_column(d_col, cellStyle=cell_style, width=110)

    gb.configure_selection(selection_mode="single")
    gb.configure_grid_options(rowGroupPanelShow='always')
    
    grid_response = AgGrid(
        pivot_df, 
        gridOptions=gb.build(), 
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        allow_unsafe_jscode=True,
        theme="alpine",
        height=500
    )

    # 6. RIGHT SIDE: THE MEANINGFUL ANALYSIS
    selected = grid_response.get('selected_rows')
    if isinstance(selected, pd.DataFrame):
        selected_row = selected.iloc[0].to_dict() if not selected.empty else None
    else:
        selected_row = selected[0] if selected else None

    with st.sidebar:
        if selected_row:
            sym = selected_row['symbol']
            # Get the most recent data point for the detailed view
            meta = raw_df[raw_df['symbol'] == sym].sort_values('asatdate', ascending=False).iloc[0]
            
            st.header(f"🔍 {sym} Analysis")
            verdict, description = get_plain_english_verdict(meta)
            
            # The Verdict Box
            if "Strongly" in verdict: st.success(f"### {verdict}")
            elif "Avoid" in verdict: st.error(f"### {verdict}")
            else: st.warning(f"### {verdict}")
            st.write(description)
            
            st.divider()
            
            # Meaningful Bullet Points based on your Table Columns
            st.subheader("Why this signal?")
            st.markdown(f"- **The Engine:** Hybrid Score is **{meta['s_hybrid']:.2f}** (Overall system confidence).")
            st.markdown(f"- **The Fundamentals:** Score is **{meta['f_score']:.2f}**, suggesting business health is {'improving' if meta['f_score'] > 0.5 else 'stagnant'}.")
            st.markdown(f"- **Wall Street View:** Analyst score of **{meta['analyst_score']:.2f}** shows institutional sentiment.")
            st.markdown(f"- **Suggested Size:** Invest **{meta['kelly_fraction']*100:.1f}%** of your trade capital (Kelly Criterion).")
            
            st.divider()
            
            # Market Context
            st.subheader("Market Context")
            st.write(f"**VIX Regime:** `{meta['vix_regime']}`")
            st.write(f"**Trend Mode:** `{meta['trend_regime']}`")
            st.progress(min(meta['s_hybrid'], 1.0), text="System Conviction Range")

        else:
            st.write("### ⬅️ Select a ticker")
            st.info("The mPulse Insight engine will translate the math into a recommendation here.")

except Exception as e:
    st.error(f"Database/Pivot Error: {e}")