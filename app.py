import streamlit as st
import paho.mqtt.client as mqtt
import json
import pandas as pd
import time
from collections import deque

# --- CONFIG ---
# Ensure these match your HiveMQ dashboard EXACTLY
MQTT_BROKER = "93be88c856bc40329b96e8fba46ac044.s1.eu.hivemq.cloud"
MQTT_USER = "kundan"
MQTT_PASS = "Kundan@1985"
TOPIC = "temperature/data"

# --- Streamlit Session State ---
if 'x_data' not in st.session_state:
    st.session_state.x_data = deque(maxlen=50)
if 'g_data' not in st.session_state:
    st.session_state.g_data = deque(maxlen=50)

# --- MQTT Callbacks ---
def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        # We use .get(key, default) to prevent crashes if a key is missing
        st.session_state.x_data.append(payload.get("X", 0))
        st.session_state.g_data.append(payload.get("G", 0))
    except Exception as e:
        print(f"Error parsing: {e}")

# --- MQTT Client Setup (Singleton pattern for Streamlit) ---
if 'mqtt_client' not in st.session_state:
    # Use newer Callback API Version
    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.tls_set() # Mandatory for HiveMQ Cloud
    client.on_message = on_message
    
    try:
        client.connect(MQTT_BROKER, 8883)
        client.subscribe(TOPIC)
        client.loop_start()
        st.session_state.mqtt_client = client
        st.success("Successfully connected to HiveMQ Cloud!")
    except Exception as e:
        st.error(f"Connection Failed: {e}")

# --- UI ---
st.title("🔬 Precision Measurement Monitor")
chart_placeholder = st.empty()
table_placeholder = st.empty()

while True:
    if len(st.session_state.x_data) > 0:
        df = pd.DataFrame({
            "Value X [µm]": list(st.session_state.x_data),
            "Gray [µm]": list(st.session_state.g_data)
        })
        chart_placeholder.line_chart(df)
        table_placeholder.table(df.tail(5))
    time.sleep(1)
