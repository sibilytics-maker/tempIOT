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

st.set_page_config(page_title="IoT Monitor", layout="centered")

# Professional Styling
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 8px; height: 3em; font-weight: bold; text-transform: uppercase; }
    /* Force Stop Highlight */
    div[data-testid="stButton"] > button:first-child { border: 2px solid #ff4b4b; color: #ff4b4b; }
    </style>
""", unsafe_allow_html=True)

# Initialize Session States
if "data_queue" not in st.session_state: st.session_state.data_queue = Queue()
if "history" not in st.session_state: st.session_state.history = []

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        val = float(payload.get("temperature", 0.0))
        userdata['queue'].put({"Temperature": val})
    except: pass

if "mqtt_client" not in st.session_state:
    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2, userdata={'queue': st.session_state.data_queue})
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT)
    client.subscribe("temperature/sibiot233")
    client.loop_start()
    st.session_state.mqtt_client = client

# --- 1. HEADER ---
st.title(f"🌡️ sibiot233 Monitoring")

# --- 2. THE LIVE FRAGMENT (Zoomed Axis) ---
@st.fragment(run_every=1)
def update_view():
    while not st.session_state.data_queue.empty():
        item = st.session_state.data_queue.get()
        st.session_state.history.append(item)
        if len(st.session_state.history) > 50: st.session_state.history.pop(0)

    if st.session_state.history:
        df = pd.DataFrame(st.session_state.history)
        current_temp = df["Temperature"].iloc[-1]
        st.metric(label="Live Temperature", value=f"{current_temp:.2f} °C")
            
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=list(range(len(df))), y=df["Temperature"],
            mode='lines', line=dict(color='#007BFF', width=3, shape='spline'),
            fill='tozeroy', fillcolor='rgba(0, 123, 255, 0.1)', name="Temp"
        ))
        
        # --- FIX: Dynamic Y-Axis (Auto-Zoom) ---
        # We set the range based on the min/max of the current data
        padding = 1.0
        y_min = df["Temperature"].min() - padding
        y_max = df["Temperature"].max() + padding

        fig.update_layout(
            height=350, margin=dict(l=10, r=10, t=10, b=10),
            plot_bgcolor='white',
            xaxis=dict(title="Time (Sliding)", showgrid=False, range=[max(0, len(df)-30), len(df)-1]),
            yaxis=dict(
                title="Temp (°C)", 
                showgrid=True, 
                gridcolor='#f0f0f0',
                # This line enables the "Zoom" effect
                range=[y_min, y_max], 
                autorange=False
            )
        )
        st.plotly_chart(fig, use_container_width=True)

update_view()

st.markdown("---")

# --- 3. SYSTEM CONTROLS (Reliable Logic) ---
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
    # Moved button logic to ensure it triggers correctly
    if st.button("🛑 FORCE STOP"):
        st.session_state.mqtt_client.publish("temperature/buzzerControl", "OFF")
        st.toast("Buzzer Force-Stopped 🔕")

with btn_resume:
    if st.button("🔄 RESUME AUTO"):
        st.session_state.mqtt_client.publish("temperature/buzzerControl", "ON")
        st.toast("Auto-Mode Active 🔄")
