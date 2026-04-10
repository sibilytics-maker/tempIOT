import streamlit as st
import paho.mqtt.client as mqtt
import pandas as pd
import time
from queue import Queue
import plotly.graph_objects as go

# --- CONFIGURATION ---
MQTT_BROKER = "93be88c856bc40329b96e8fba46ac044.s1.eu.hivemq.cloud"
MQTT_USER = "kundan"
MQTT_PASS = "Kundan@1985"

# --- PAGE CONFIG ---
st.set_page_config(page_title="Temperature Monitor", layout="centered")

# --- DEVICE NAME ---
params = st.query_params
device_id = params.get("device", "sibiot233") 

st.title(f"🌡️ {device_id}")
st.markdown("---")

if "data_queue" not in st.session_state: st.session_state.data_queue = Queue()
if "history" not in st.session_state: st.session_state.history = []

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        val = float(payload.get("temperature", 0.0))
        # Important: Put in queue
        userdata['queue'].put({"Temperature": val})
    except: pass

# --- MQTT SETUP ---
if "mqtt_client" not in st.session_state:
    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2, userdata={'queue': st.session_state.data_queue})
    client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.tls_set()
    client.on_message = on_message
    client.connect(MQTT_BROKER, 8883)
    client.subscribe(f"temperature/{device_id}")
    client.loop_start()
    st.session_state.mqtt_client = client

# --- UI PLACEHOLDERS (Must be created once) ---
status_text = st.empty()
metric_spot = st.empty()
chart_spot = st.empty()

# --- REFRESH LOOP ---
while True:
    # 1. Update data
    while not st.session_state.data_queue.empty():
        item = st.session_state.data_queue.get()
        st.session_state.history.append(item)
        if len(st.session_state.history) > 50: st.session_state.history.pop(0)

    # 2. Render
    if len(st.session_state.history) > 0:
        status_text.empty() # Clear "Waiting for data..."
        
        df = pd.DataFrame(st.session_state.history)
        current_temp = df["Temperature"].iloc[-1]
        
        # Calculate range
        min_temp = df["Temperature"].min()
        max_temp = df["Temperature"].max()
        buffer = 0.2 
        
        # Display
        metric_spot.metric("Latest Reading", f"{current_temp:.2f} °C")
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            y=df["Temperature"],
            mode='lines+markers',
            fill='tozeroy',
            fillcolor='rgba(59, 130, 246, 0.1)',
            line=dict(color='#3b82f6', width=3),
            marker=dict(size=12, color='#f59e0b', line=dict(width=2, color='white'))
        ))
        
        fig.update_layout(
            hovermode="x unified",
            margin=dict(l=0, r=0, t=20, b=0),
            plot_bgcolor='white',
            paper_bgcolor='white',
            yaxis=dict(
                title="Temperature (°C)", 
                range=[min_temp - buffer, max_temp + buffer]
            ),
        )
        chart_spot.plotly_chart(fig, use_container_width=True)
    else:
        status_text.write("⏳ Waiting for data from device... check if device is ON.")
            
    time.sleep(1)
