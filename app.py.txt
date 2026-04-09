import streamlit as st
import paho.mqtt.client as mqtt
import json
import time
from collections import deque

# --- CONFIG ---
MQTT_BROKER = "93be88c856bc40329b96e8fba46ac044.s1.eu.hivemq.cloud"
MQTT_USER = "kundan"
MQTT_PASS = "Kundan@1985"
TOPIC = "temperature/data"

if 'temp_history' not in st.session_state:
    st.session_state.temp_history = deque(maxlen=50)

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        # We look for "T" because that's what your ESP32 sends
        val = payload.get("T", 0) 
        st.session_state.temp_history.append(val)
    except Exception as e:
        print(f"Error: {e}")

st.title("🚀 Professional Live Sensor Dashboard")
st.write(f"Connected to Topic: {TOPIC}")
chart_placeholder = st.empty()

# MQTT Setup
client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
client.username_pw_set(MQTT_USER, MQTT_PASS)
client.tls_set()
client.on_message = on_message
client.connect(MQTT_BROKER, 8883)
client.subscribe(TOPIC)
client.loop_start()

# UI Refresh Loop
while True:
    if st.session_state.temp_history:
        chart_placeholder.line_chart(list(st.session_state.temp_history))
    time.sleep(1)
