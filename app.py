import streamlit as st
import paho.mqtt.client as mqtt
import time
import json
import pandas as pd
import plotly.graph_objects as go
from queue import Queue
import os

# --- CONFIG ---
MQTT_BROKER = "metro.proxy.rlwy.net"
MQTT_PORT = 55113

# --- APP SETUP ---
params = st.query_params
device_id = params.get("device", "sibiot233") 

st.set_page_config(page_title=f"Monitor: {device_id}", layout="centered")

# Professional Styling
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 8px; height: 3em; font-weight: bold; text-transform: uppercase; }
    div[data-testid="stButton"] > button:first-child:active { border-color: #ff4b4b; color: #ff4b4b; }
    /* Stop the flickering background */
    .main { background-color: #f8f9fa; }
    </style>
""", unsafe_allow_html=True)

# Initialize Session States
if "data_queue" not in st.session_state: st.session_state.data_queue = Queue()
if "history" not in st.session_state: st.session_state.history = []

# Thread-safe callback
def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        val = float(payload.get("temperature", 0.0))
        userdata['queue'].put({"Temperature": val})
    except: pass

# MQTT Connection
if "mqtt_client" not in st.session_state:
    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2, userdata={'queue': st.session_state.data_queue})
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT)
    client.subscribe(f"temperature/{device_id}")
    client.loop_start()
    st.session_state.mqtt_client = client

# --- 1. UI HEADER ---
st.title(f"🌡️ {device_id} Monitoring")

# --- 2. THE STABLE FRAGMENT (This stops the flickering) ---
@st.fragment(run_every=2)
def update_dashboard():
    # Process queue data into history
    while not st.session_state.data_queue.empty():
        item = st.session_state.data_queue.get()
        st.session_state.history.append(item)
        if len(st.session_state.history) > 50: 
            st.session_state.history.pop(0)

    if st.session_state.history:
        df = pd.DataFrame(st.session_state.history)
        current_temp = df["Temperature"].iloc[-1]
        
        # Live Metric
        st.metric(label="Live Temperature", value=f"{current_temp:.2f} °C")
            
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=list(range(len(df))), y=df["Temperature"],
            mode='lines', line=dict(color='#007BFF', width=3, shape='spline'),
            fill='tozeroy', fillcolor='rgba(0, 123, 255, 0.1)',
            name="Temp"
        ))
        
        # Dynamic sliding window for X-axis
        fig.update_layout(
            height=350, margin=dict(l=10, r=10, t=10, b=10),
            plot_bgcolor='white',
            xaxis=dict(title="Time (Last 50 Samples)", showgrid=False, range=[max(0, len(df)-30), len(df)-1]),
            yaxis=dict(title="Temp (°C)", showgrid=True, gridcolor='#f0f0f0')
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Waiting for temperature data from ESP32...")

# Run the live fragment
update_dashboard()

st.markdown("---")

# --- 3. SYSTEM CONTROLS (Static area - doesn't flicker) ---
with st.container():
    st.subheader("⚙️ System Controls")
    
    col_input, col_btn = st.columns([3, 1])
    with col_input:
        threshold = st.number_input("Buzzer Threshold (°C)", value=60.0, step=0.5)
    with col_btn:
        st.write("##") 
        if st.button("SET", type="primary"):
            st.session_state.mqtt_client.publish("temperature/setThreshold", str(threshold))
            st.toast("Threshold Updated ✅")

    btn_stop, btn_resume = st.columns(2)
    with btn_stop:
        if st.button("🛑 FORCE STOP"):
            st.session_state.mqtt_client.publish("temperature/buzzerControl", "OFF")
            st.toast("Buzzer Force-Stopped 🔕")
    with btn_resume:
        if st.button("🔄 RESUME AUTO"):
            st.session_state.mqtt_client.publish("temperature/buzzerControl", "ON")
            st.toast("Auto-Mode Active 🔄")
