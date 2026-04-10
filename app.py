import streamlit as st
import paho.mqtt.client as mqtt
import json
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

# --- UI LAYOUT ---
# Using columns to center everything
col1, col2, col3 = st.columns([1, 4, 1])
with col2:
    st.title(f"🌡️ {device_id}")
    st.markdown("---")

if "data_queue" not in st.session_state: st.session_state.data_queue = Queue()
if "history" not in st.session_state: st.session_state.history = []

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        val = float(payload.get("temperature", 0.0))
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

chart_place = st.empty()
chart_count = 0

while True:
    while not st.session_state.data_queue.empty():
        item = st.session_state.data_queue.get()
        st.session_state.history.append(item)
        if len(st.session_state.history) > 50: st.session_state.history.pop(0)

    if st.session_state.history:
        df = pd.DataFrame(st.session_state.history)
        current_temp = df["Temperature"].iloc[-1]
        
        # --- CALCULATE ZOOM ---
        # Add a buffer of 0.2 degrees above and below the min/max
        min_temp = df["Temperature"].min()
        max_temp = df["Temperature"].max()
        buffer = 0.2 
        
        # --- RE-RENDER ---
        with col2: # Ensure it renders inside the centered column
            st.metric(label="Latest Reading", value=f"{current_temp:.2f} °C")
            
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
                xaxis=dict(title="Time (Samples)", showgrid=False, linecolor='lightgray'),
                yaxis=dict(
                    title="Temperature (°C)", 
                    showgrid=True, 
                    gridcolor='#f1f5f9',
                    # FORCE THE RANGE HERE
                    range=[min_temp - buffer, max_temp + buffer] 
                ),
            )
            st.plotly_chart(fig, use_container_width=True, key=f"t_{chart_count}")
            chart_count += 1
            
    time.sleep(1)
