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

# --- STREAMLIT FRONTEND ---
params = st.query_params
device_id = params.get("device", "sibiot233") 

st.set_page_config(page_title=f"Monitor: {device_id}", layout="centered")

# Professional Styling
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 8px; height: 3em; font-weight: bold; }
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
        # Put data in queue; do not touch session_state here to avoid thread errors
        userdata['queue'].put({"Temperature": val})
    except: pass

# MQTT Connection
if "mqtt_client" not in st.session_state:
    # Pass the queue via userdata for thread safety
    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2, userdata={'queue': st.session_state.data_queue})
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT)
    client.subscribe(f"temperature/{device_id}")
    client.loop_start()
    st.session_state.mqtt_client = client

# UI Elements
st.title(f"🌡️ {device_id} Monitoring")
metric_placeholder = st.empty()
chart_placeholder = st.empty()

st.markdown("---")

with st.container():
    st.subheader("⚙️ System Controls")
    col_input, col_btn = st.columns([3, 1])
    with col_input:
        threshold_input = st.number_input("Buzzer Threshold (°C)", value=60.0, step=0.5)
    with col_btn:
        st.write("##")
        if st.button("SET", type="primary"):
            st.session_state.mqtt_client.publish("temperature/setThreshold", str(threshold_input))
            st.toast("Threshold Updated", icon="✅")

# --- MAIN LOOP (Optimized for Streamlit) ---
# Process all items currently in the queue
while not st.session_state.data_queue.empty():
    item = st.session_state.data_queue.get()
    st.session_state.history.append(item)
    if len(st.session_state.history) > 50: 
        st.session_state.history.pop(0)

# Render Chart and Metric if data exists
if st.session_state.history:
    df = pd.DataFrame(st.session_state.history)
    current_temp = df["Temperature"].iloc[-1]
    metric_placeholder.metric(label="Live Temperature", value=f"{current_temp:.2f} °C")
        
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df["Temperature"], mode='lines', 
                             line=dict(color='#007BFF', width=4, shape='spline'),
                             fill='tozeroy', name="Temp"))

    label_text, label_color = ("⚠️ HIGH", "Red") if current_temp >= threshold_input else ("✅ NORMAL", "Green")
    fig.add_annotation(x=len(df)-1, y=current_temp, text=label_text, bgcolor=label_color, font=dict(color="white"))
    
    fig.update_layout(height=350, plot_bgcolor='white', margin=dict(l=0,r=0,t=0,b=0))
    chart_placeholder.plotly_chart(fig, use_container_width=True)

# Auto-refresh the page every 2 seconds
time.sleep(2)
st.rerun()
