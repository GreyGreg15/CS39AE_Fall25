import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import time

st.set_page_config(page_title="Live API Demo (Simple)", page_icon="📡", layout="wide")
st.markdown("""
    <style>
      [data-testid="stPlotlyChart"], .stPlotlyChart, .stElementContainer {
        transition: none !important; opacity: 1 !important;
      }
    </style>
""", unsafe_allow_html=True)

st.title("📡 Simple Live Data Demo (CoinGecko)")
st.caption("Manual refresh + caching + short history, with a safe fallback if the API hiccups.")

COINS = ["bitcoin", "ethereum"]
VS = "usd"
HEADERS = {"User-Agent": "msudenver-dataviz-class/1.0", "Accept": "application/json"}

def build_url(ids):
    return f"https://api.coingecko.com/api/v3/simple/price?ids={','.join(ids)}&vs_currencies={VS}"

API_URL = build_url(COINS)

# Tiny fallback so the demo doesn’t die if rate-limited
SAMPLE_DF = pd.DataFrame(
    [{"coin": "bitcoin", VS: 68000}, {"coin": "ethereum", VS: 3500}]
)

@st.cache_data(ttl=300, show_spinner=False)
def fetch_prices(url: str):
    """Return (df, error_message). Never raise."""
    try:
        r = requests.get(url, timeout=10, headers=HEADERS)
        if r.status_code == 429:
            retry_after = r.headers.get("Retry-After", "a bit")
            return None, f"429 Too Many Requests — try again after {retry_after}s"
        r.raise_for_status()
        data = r.json()
        df = pd.DataFrame(data).T.reset_index().rename(columns={"index": "coin"})
        return df, None
    except requests.RequestException as e:
        return None, f"Network/HTTP error: {e}"

st.subheader("Auto Refresh Settings")
refresh_sec = st.slider("Refresh every (sec)", 10, 120, 30)
auto_refresh = st.toggle("Enable auto-refresh", value=False)
st.caption(f"Last refreshed at: {time.strftime('%H:%M:%S')}")

st.subheader("Prices")
df, err = fetch_prices(API_URL)
if err:
    st.warning(f"{err}\nShowing sample data so the demo continues.")
    df = SAMPLE_DF.copy()

st.dataframe(df, use_container_width=True)

if "cg_history" not in st.session_state:
    st.session_state.cg_history = pd.DataFrame(columns=["time", "coin", VS])

now = pd.Timestamp.utcnow().tz_convert(None)
snapshot = df.assign(time=now)[["time", "coin", VS]]
st.session_state.cg_history = pd.concat([st.session_state.cg_history, snapshot], ignore_index=True)

cutoff = now - pd.Timedelta(minutes=60)
hist = st.session_state.cg_history.query("time >= @cutoff")

fig = px.line(
    hist, x="time", y=VS, color="coin",
    labels={"time": "Time", VS: f"Price ({VS.upper()})"},
    title=f"Rolling 60-minute prices ({VS.upper()})"
)
st.plotly_chart(fig, use_container_width=True)

# Auto-refresh loop
if auto_refresh:
    time.sleep(refresh_sec)
    fetch_prices.clear()
    st.rerun()

