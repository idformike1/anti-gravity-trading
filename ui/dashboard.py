import streamlit as st
import requests
import pandas as pd
import time

st.set_page_config(layout="wide", page_title="Anti-Gravity Dashboard")

API_URL = "http://localhost:8000"

st.title("🚀 Anti-Gravity Trading System")

def get_system_state():
    try:
        resp = requests.get(f"{API_URL}/state")
        return resp.json()
    except:
        return None

state = get_system_state()

if not state:
    st.error("Could not connect to Control API. Ensure the system is running.")
    st.stop()

# --- Top Metrics ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Mode", state["mode"])
col2.metric("Kill Switch", "ACTIVE" if state["kill_switch"] else "OFF")
col3.metric("Available Funds", f"₹{state['funds']['available']}")
# Calculate PnL locally for display
total_pnl = sum(p["realized_pnl"] + p["unrealized_pnl"] for p in state["positions"].values())
col4.metric("Total PnL", f"₹{total_pnl}", delta=f"{total_pnl}")

# --- Controls ---
st.sidebar.header("System Controls")
new_mode = st.sidebar.selectbox("Switch Mode", ["LIVE", "PAPER", "REPLAY"], index=["LIVE", "PAPER", "REPLAY"].index(state["mode"]))
if st.sidebar.button("Update Mode"):
    requests.post(f"{API_URL}/mode", json={"mode": new_mode})
    st.rerun()

if st.sidebar.button("TRIGGER KILL SWITCH", type="primary"):
    requests.post(f"{API_URL}/killswitch", json={"active": True})
    st.rerun()

if st.sidebar.button("RESET KILL SWITCH"):
    requests.post(f"{API_URL}/killswitch", json={"active": False})
    st.rerun()

# --- Tabs ---
tab1, tab2, tab3 = st.tabs(["Positions", "Orders", "Market Data"])

with tab1:
    st.header("Active Positions")
    if state["positions"]:
        df_p = pd.DataFrame(state["positions"].values())
        st.dataframe(df_p)
    else:
        st.write("No active positions.")

with tab2:
    st.header("Order Log")
    if state["orders"]:
        df_o = pd.DataFrame(state["orders"].values())
        st.dataframe(df_o)
    else:
        st.write("No orders placed.")

with tab3:
    st.header("Live Feed")
    if state["market_data"]:
        df_m = pd.DataFrame(state["market_data"].values())
        st.dataframe(df_m)
    else:
        st.write("Waiting for market data...")

# Auto-refresh
time.sleep(1)
st.rerun()
