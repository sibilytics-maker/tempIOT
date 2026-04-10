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

# --- DEVICE ID FROM URL ---
# Open your app like this: your-app.railway.app/?device=sibiot233
params = st.query_params
device_id = params.get("device", "default_device")

st.set_page_config(page_title=f"Monitor: {device_id}", layout="wide")
st.title(f"🌡️ Temperature Monitor: {device_id}")

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
    client.subscribe(f"temperature/{device_id}") # Subscribe to device specific topic
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
        
        # --- THE FIX: CALCULATE ZOOM RANGE ---
        # Add a small buffer (0.5) so the line isn't touching the top/bottom
        y_min = df["Temperature"].min() - 0.5
        y_max = df["Temperature"].max() + 0.5

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            y=df["Temperature"],
            mode='lines+markers',
            fill='tozeroy', 
            fillcolor='rgba(0, 100, 250, 0.15)',
            line=dict(color='rgba(0, 100, 250, 0.8)', width=3),
            marker=dict(size=14, color='Orange', line=dict(width=2, color='White'))
        ))
        
        # --- THE FIX: APPLY ZOOM ---
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            yaxis=dict(
                showgrid=True, 
                gridcolor='lightgray',
                range=[y_min, y_max]  # This forces the chart to zoom!
            )
        )

        with chart_place.container():
            st.plotly_chart(fig, use_container_width=True, key=f"t_{chart_count}")
            chart_count += 1
    time.sleep(1)
