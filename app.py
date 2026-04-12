import streamlit as st
import paho.mqtt.client as mqtt
import json
import time
from collections import deque

# --- CONFIG ---
MQTT_BROKER = "93be88c856bc40329b96e8fba46ac044.s1.eu.hivemq.cloud"
MQTT_USER = "kundan"
MQTT_PASS = "Kundan@1985"
DATA_TOPIC = "temperature/sibiot233"      # Topic where ESP32 sends data
SET_TOPIC = "temperature/setThreshold"   # Topic to set buzzer threshold

if 'temp_history' not in st.session_state:
    st.session_state.temp_history = deque(maxlen=50)
if 'current_temp' not in st.session_state:
    st.session_state.current_temp = 0.0

# Callback when message is received from ESP32
def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        # Matches your ESP32 payload: {"temperature": xx.xx}
        val = payload.get("temperature", 0) 
        st.session_state.current_temp = val
        st.session_state.temp_history.append(val)
    except Exception as e:
        print(f"Error: {e}")

st.set_page_config(page_title="Railway Dashboard", layout="wide")
st.title("🚀 Professional Railway Sensor Dashboard")

# --- SIDEBAR CONTROL ---
st.sidebar.header("Buzzer Settings")
new_threshold = st.sidebar.number_input("Set Alert Threshold (°C)", min_value=0, max_value=100, value=45)

# MQTT Setup
if 'mqtt_client' not in st.session_state:
    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.tls_set()
    client.on_message = on_message
    client.connect(MQTT_BROKER, 8883)
    client.subscribe(DATA_TOPIC)
    client.loop_start()
    st.session_state.mqtt_client = client

# Button to send new threshold to ESP32
if st.sidebar.button("Update Buzzer Threshold"):
    st.session_state.mqtt_client.publish(SET_TOPIC, str(new_threshold))
    st.sidebar.success(f"Threshold set to {new_threshold}°C")

# --- MAIN UI ---
col1, col2 = st.columns(2)
col1.metric("Live Temperature", f"{st.session_state.current_temp} °C")
col2.metric("Active Threshold", f"{new_threshold} °C")

chart_placeholder = st.empty()

# UI Refresh Loop
if st.session_state.temp_history:
    chart_placeholder.line_chart(list(st.session_state.temp_history))

time.sleep(1)
st.rerun()
