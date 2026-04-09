import streamlit as st
import paho.mqtt.client as mqtt
import json
from collections import deque
import pandas as pd
import time

# --- CONFIG ---
MQTT_BROKER = "93be88c856bc40329b96e8fba46ac044.s1.eu.hivemq.cloud"
MQTT_USER = "kundan"
MQTT_PASS = "Kundan@1985"
TOPIC = "temperature/data"

# --- Streamlit Session State Initialization ---
if 'x_data' not in st.session_state:
    st.session_state.x_data = deque(maxlen=50)
if 'g_data' not in st.session_state:
    st.session_state.g_data = deque(maxlen=50)

# --- MQTT Callbacks ---
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        st.success("Connected to MQTT Broker!")
        # IMPORTANT: Subscribe to your desired topic here
        client.subscribe("temperature/data") # <--- Replace "esp32/data" with your actual MQTT topic
    else:
        st.error(f"Failed to connect, return code {rc}\n")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        # Capture "X" and "G" from the ESP32 JSON
        st.session_state.x_data.append(payload.get("X", 0))
        st.session_state.g_data.append(payload.get("G", 0))
    except Exception as e:
        st.error(f"Error parsing MQTT message: {e}")

# --- MQTT Client Setup ---
# Only create the client once
if 'mqtt_client' not in st.session_state:
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    try:
        # Replace with your MQTT broker's IP or hostname and port
        client.connect("your_mqtt_broker_address", 1883, 60)
        client.loop_start() # Start the MQTT client in a non-blocking way
        st.session_state.mqtt_client = client
    except Exception as e:
        st.error(f"Could not connect to MQTT broker: {e}")
else:
    client = st.session_state.mqtt_client

# --- Streamlit UI ---
st.title("🔬 Precision Measurement Monitor")
placeholder = st.empty()

while True:
    if len(st.session_state.x_data) > 0:
        # Create a table/dataframe like your Excel image
        df = pd.DataFrame({
            "Value X [µm]": list(st.session_state.x_data),
            "Gray [µm]": list(st.session_state.g_data)
        })
        # Plot both lines
        with placeholder.container():
            st.line_chart(df)
            # Show the latest values as a table at the bottom
            st.table(df.tail(5))
    time.sleep(1)
