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

if 'x_data' not in st.session_state:
    st.session_state.x_data = deque(maxlen=50)
if 'g_data' not in st.session_state:
    st.session_state.g_data = deque(maxlen=50)

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        # Capture "X" and "G" from the ESP32 JSON
        st.session_state.x_data.append(payload.get("X", 0))
        st.session_state.g_data.append(payload.get("G", 0))
    except Exception as e:
        st.error(f"Error parsing: {e}")

# ... [Keep your MQTT Setup here] ...

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
        placeholder.line_chart(df)
        # Show the latest values as a table at the bottom
        st.table(df.tail(5)) 
    import time
    time.sleep(1)
