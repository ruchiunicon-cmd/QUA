import os
import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Attempt to import Google Generative AI for real Pine Script generation
try:
    import google.generativeai as genai
    HAS_GEMINI_LIB = True
except ImportError:
    HAS_GEMINI_LIB = False

# ==========================================
# PAGE CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="QuantTerminal AI Studio",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# GLASSMORPHISM DARK THEME CSS
# ==========================================
st.markdown("""
    <style>
    /* Dark Gradient Background */
    .stApp {
        background: linear-gradient(135deg, #0d1117 0%, #161b22 50%, #090d16 100%);
        color: #e6edf3;
    }
    
    /* Glassmorphism Containers */
    div[data-testid="stMetricValue"], 
    .glass-card, 
    .stTabs [data-baseweb="tab-panel"] {
        background: rgba(22, 27, 34, 0.55);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        padding: 15px;
    }

    /* Glassmorphism Sidebar */
    section[data-testid="stSidebar"] {
        background: rgba(13, 17, 23, 0.75) !important;
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border-right: 1px solid rgba(255, 255, 255, 0.08);
    }

    /* Neon Accents & Glass Buttons */
    div.stButton > button {
        background: rgba(35, 134, 54, 0.3);
        backdrop-filter: blur(8px);
        color: #3fb950;
        border: 1px solid rgba(63, 185, 80, 0.4);
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    div.stButton > button:hover {
        background: rgba(46, 160, 67, 0.6);
        border-color: #3fb950;
        color: #ffffff;
        box-shadow: 0 0 15px rgba(63, 185, 80, 0.4);
    }

    /* Header Glass Container */
    .header-box {
        display: flex;
        align-items: center;
        gap: 20px;
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        padding: 18px;
        border-radius: 16px;
        margin-bottom: 25px;
    }
    
    .header-title {
        font-size: 26px;
        font-weight: 700;
        background: linear-gradient(90deg, #58a6ff, #bc8cff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
    }
    
    .header-subtitle {
        color: #8b949e;
        font-size: 14px;
        margin: 0;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# DATA FETCHING UTILITIES
# ==========================================
@st.cache_data(ttl=60, show_spinner=False)
def fetch_market_data(ticker_symbol: str, period_val: str, interval_val: str):
    try:
        ticker = yf.Ticker(ticker_symbol.strip())
        df = ticker.history(period=period_val, interval=interval_val)
        if df.empty:
            return None, "No data found for the specified ticker and timeframe."
        return df, None
    except Exception as e:
        return None, str(e)

@st.cache_data(ttl=300, show_spinner=False)
def fetch_market_summary(tickers):
    summary = []
    for t in tickers:
        try:
            tk = yf.Ticker(t)
            hist = tk.history(period="2d")
            if len(hist) >= 2:
                close = hist['Close'].iloc[-1]
                prev = hist['Close'].iloc[-2]
                chg = close - prev
                pct = (chg / prev) * 100
                summary.append({"Ticker": t, "Price": f"${close:,.2f}" if "USD" in t or "AAPL" in t else f"₹{close:,.2f}", "Change (%)": f"{pct:+.2f}%"})
        except Exception:
            pass
    return pd.DataFrame(summary)

# ==========================================
# SIDEBAR CONFIGURATION
# ==========================================
st.sidebar.markdown("### ⚡ Terminal Controls")
st.sidebar.markdown("---")

ticker_input = st.sidebar.text_input("Ticker Symbol", value="RELIANCE.NS", help="e.g., RELIANCE.NS, BTC-USD, AAPL, TCS.NS")
period_option = st.sidebar.selectbox("Timeframe Period", options=["1d", "5d", "1mo", "6mo", "1y", "2y", "max"], index=2)
interval_option = st.sidebar.selectbox("Candle Interval", options=["1m", "5m", "15m", "1h", "1d"], index=3)

st.sidebar.markdown("---")
st.sidebar.markdown("### 🔑 AI Config")

# API Key handling for Gemini
gemini_api_key = None
try:
    if "GEMINI_API_KEY" in st.secrets:
        gemini_api_key = st.secrets["GEMINI_API_KEY"]
except Exception:
    pass

if not gemini_api_key and "GEMINI_API_KEY" in os.environ:
    gemini_api_key = os.environ["GEMINI_API_KEY"]

if not gemini_api_key:
    gemini_api_key = st.sidebar.text_input("Gemini API Key", type="password", help="Enter key for live AI Pine Script generation")

# Technical Indicator Overlay Toggles
st.sidebar.markdown("---")
st.sidebar.markdown("### 📊 Chart Overlays")
show_sma = st.sidebar.checkbox("20/50 SMA", value=True)
show_rsi = st.sidebar.checkbox("RSI Subplot", value=True)

# ==========================================
# MAIN APP HEADER WITH LOGO
# ==========================================
st.markdown("""
    <div class="header-box">
        <img src="https://img.icons8.com/fluency/96/000000/financial-analytics.png" width="60" height="60" alt="Logo"/>
        <div>
            <p class="header-title">QuantMarket Terminal & Pine Script Studio</p>
            <p class="header-subtitle">Real-time market analytics, glassmorphism UI, and AI-powered Pine Script v5 generation</p>
        </div>
    </div>
""", unsafe_allow_html=True)

# Fetch Main Asset Data
df, error_msg = fetch_market_data(ticker_input, period_option, interval_option)

if error_msg or df is None or df.empty:
    st.error(f"❌ Error loading data for `{ticker_input}`: {error_msg}")
    st.stop()

if isinstance(df.columns, pd.MultiIndex):
    df.columns = df.columns.get_level_values(0)

df.index = pd.to_datetime(df.index)

# ==========================================
# CALCULATE INDICATORS
# ==========================================
df['SMA20'] = df['Close'].rolling(window=20).mean()
df['SMA50'] = df['Close'].rolling(window=50).mean()

# RSI Calculation
delta = df['Close'].diff()
gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
rs = gain / loss
df['RSI'] = 100 - (100 / (1 + rs))

# ==========================================
# MAIN TABS SETUP
# ==========================================
tab_chart, tab_overview, tab_ai = st.tabs([
    "📊 Interactive Glass Chart & Analytics", 
    "🌐 Multi-Market Overview", 
    "🤖 Real AI Pine Script Generator"
])

# ------------------------------------------
# TAB 1: INTERACTIVE CHART & METRICS
# ------------------------------------------
with tab_chart:
    latest_close = df['Close'].iloc[-1]
    prev_close = df['Close'].iloc[-2] if len(df) > 1 else latest_close
    price_change = latest_close - prev_close
    pct_change = (price_change / prev_close) * 100 if prev_close != 0 else 0
    period_high = df['High'].max()
    period_low = df['Low'].min()

    # Metrics Dashboard Cards
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Latest Close", f"{latest_close:,.2f}", f"{price_change:+,.2f} ({pct_change:+.2f}%)")
    k2.metric("Period High", f"{period_high:,.2f}")
    k3.metric("Period Low", f"{period_low:,.2f}")
    k4.metric("Last Vol", f"{int(df['Volume'].iloc[-1]):,}")
    k5.metric("Current RSI (14)", f"{df['RSI'].iloc[-1]:.1f}" if not pd.isna(df['RSI'].iloc[-1]) else "N/A")

    st.markdown("---")

    # Plotly Glass-Style Interactive Candlestick Chart
    rows_count = 3 if show_rsi else 2
    row_heights = [0.6, 0.2, 0.2] if show_rsi else [0.75, 0.25]
    
    fig = make_subplots(
        rows=rows_count, cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.03, 
        row_heights=row_heights
    )

    # Candlesticks
    fig.add_trace(go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
        name='OHLC', increasing_line_color='#26a69a', decreasing_line_color='#ef5350'
    ), row=1, col=1)

    # SMAs Overlay
    if show_sma:
        fig.add_trace(go.Scatter(x=df.index, y=df['SMA20'], name='SMA 20', line=dict(color='#58a6ff', width=1.5)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['SMA50'], name='SMA 50', line=dict(color='#bc8cff', width=1.5)), row=1, col=1)

    # Volume Subplot
    colors = ['#26a69a' if c >= o else '#ef5350' for c, o in zip(df['Close'], df['Open'])]
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name='Volume', marker_color=colors), row=2, col=1)

    # RSI Subplot
    if show_rsi:
        fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], name='RSI', line=dict(color='#e3b341', width=1.5)), row=3, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)

    # Styling for Glassmorphism Look
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(16, 22, 30, 0.6)",
        xaxis_rangeslider_visible=False,
        height=700,
        margin=dict(l=10, r=10, t=20, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(255,255,255,0.05)')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(255,255,255,0.05)')

    st.plotly_chart(fig, use_container_width=True)

# ------------------------------------------
# TAB 2: MULTI-MARKET OVERVIEW
# ------------------------------------------
with tab_overview:
    st.subheader("🌐 Real-Time Market Watch")
    st.markdown("Live price snapshot across major asset classes.")

    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 🇮🇳 Indian Equities & Indices")
        in_tickers = ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "^NSEI"]
        df_in = fetch_market_summary(in_tickers)
        if not df_in.empty:
            st.dataframe(df_in, use_container_width=True, hide_index=True)

    with col2:
        st.markdown("#### 🪙 Crypto & Global Assets")
        global_tickers = ["BTC-USD", "ETH-USD", "AAPL", "NVDA", "TSLA"]
        df_global = fetch_market_summary(global_tickers)
        if not df_global.empty:
            st.dataframe(df_global, use_container_width=True, hide_index=True)

# ------------------------------------------
# TAB 3: REAL AI PINE SCRIPT GENERATOR
# ------------------------------------------
with tab_ai:
    st.subheader("🤖 Senior Pine Script v5 AI Architect")
    st.markdown("Generates production-ready, custom TradingView Pine Script v5 code on demand using Google Gemini AI.")

    # Initialize Chat Messages State
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Hello! I am your AI Pine Script developer. Ask me to build any indicator or strategy (e.g., *'Create a multi-timeframe EMA crossover with trailing stop loss and alerts'*)."
            }
        ]

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Describe your indicator or strategy..."):
        if not gemini_api_key or not HAS_GEMINI_LIB:
            st.error("⚠️ Please enter a valid Gemini API Key in the left sidebar to enable live AI code generation.")
        else:
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                with st.spinner("Generating custom Pine Script v5 via Gemini AI..."):
                    try:
                        genai.configure(api_key=gemini_api_key)
                        
                        system_prompt = (
                            "You are an expert quantitative developer and TradingView Pine Script v5 specialist. "
                            "Write clean, error-free, optimized Pine Script v5 code based on user requirements. "
                            "Always wrap code blocks inside ```pine syntax highlighting blocks. "
                            "Provide concise notes explaining how to add the script to TradingView."
                        )
                        
                        # Preferred model name
                        model = genai.GenerativeModel(
                            model_name="gemini-1.5-pro",
                            system_instruction=system_prompt
                        )
                        
                        chat_history = [
                            {"role": m["role"] if m["role"] != "assistant" else "model", "parts": [m["content"]]}
                            for m in st.session_state.messages[:-1]
                        ]
                        
                        chat = model.start_chat(history=chat_history)
                        response = chat.send_message(prompt)
                        ai_response = response.text

                        st.markdown(ai_response)
                        st.session_state.messages.append({"role": "assistant", "content": ai_response})

                    except Exception as e:
                        st.error(f"AI Generation Error: {str(e)}")