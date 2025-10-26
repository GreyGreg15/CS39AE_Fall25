import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import time

st.title(" Weather (Open-Meteo)")
st.caption("Denver temperature over time with caching + short history + auto-refresh.")

lat, lon = 39.7392, -104.9903  # Denver
wurl = (
    "https://api.open-meteo.com/v1/forecast"
    f"?latitude={lat}&longitude={lon}&current=temperature_2m,wind_speed_10m"
)
HEADERS = {"User-Agent": "msudenver-dataviz-class/1.0", "Accept": "application/json"}

@st.cache_data(ttl=600, show_spinner=False)  # 10 minutes
def get_weather():
    try:
        r = requests.get(wurl, timeout=10, headers=HEADERS)
        r.raise_for_status()
        j = r.json()["current"]
        return pd.DataFrame([{
            "time": pd.to_datetime(j["time"]),
            "temperature": j["temperature_2m"],
            "wind": j["wind_speed_10m"],
        }]), None
    except requests.RequestException as e:
        now = pd.Timestamp.utcnow().tz_convert(None)
        return pd.DataFrame([{"time": now, "temperature": None, "wind": None}]), f"Weather API error: {e}"

st.subheader("Auto Refresh Settings")
refresh_sec = st.slider("Refresh every (sec)", 10, 120, 30, key="wx_refresh")
auto_refresh = st.toggle("Enable auto-refresh", value=False, key="wx_auto")
st.caption(f"Last refreshed at: {time.strftime('%H:%M:%S')}")

df, err = get_weather()
if err:
    st.warning(err)

if "wx_history" not in st.session_state:
    st.session_state.wx_history = pd.DataFrame(columns=["time", "temperature", "wind"])
st.session_state.wx_history = pd.concat([st.session_state.wx_history, df], ignore_index=True)

now = pd.Timestamp.utcnow().tz_convert(None)
cutoff = now - pd.Timedelta(minutes=120)
wx_hist = (st.session_state.wx_history
           .dropna(subset=["temperature"])
           .query("time >= @cutoff")
           .sort_values("time"))

st.subheader("Temperature (last 120 min)")
if wx_hist.empty:
    st.info("Waiting for first successful fetch…")
else:
    fig = px.line(
        wx_hist, x="time", y="temperature", markers=True,
        labels={"time": "Time", "temperature": "Temp (°C)"}
    )
    st.plotly_chart(fig, use_container_width=True)

if not df.empty:
    c1, c2 = st.columns(2)
    t = df["temperature"].iloc[0]
    w = df["wind"].iloc[0]
    c1.metric("Current Temp (°C)", f"{t}" if pd.notnull(t) else "—")
    c2.metric("Wind (m/s)", f"{w}" if pd.notnull(w) else "—")

# Auto-refresh loop
if auto_refresh:
    time.sleep(refresh_sec)
    get_weather.clear()
    st.rerun()
