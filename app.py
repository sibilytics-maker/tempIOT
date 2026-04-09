import streamlit as st
import paho.mqtt.client as mqtt
import json
import pandas as pd
import time
from queue import Queue

# --- CONFIGURATION ---
MQTT_BROKER = "93be88c856bc40329b96e8fba46ac044.s1.eu.hivemq.cloud"
MQTT_USER = "kundan"
MQTT_PASS = "Kundan@1985"
TOPIC = "temperature/data"

# 1. Thread-safe Data Queue
if "data_queue" not in st.session_state:
    st.session_state.data_queue = Queue()

if "history" not in st.session_state:
    st.session_state.history = []

# --- MQTT CALLBACK ---
def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        # We put data into a queue because background threads 
        # cannot touch st.session_state directly in Streamlit
        userdata['queue'].put({
            "Value X [µm]": payload.get("X", 0),
            "Gray [µm]": payload.get("G", 0)
        })
    except Exception as e:
        print(f"MQTT Error: {e}")

# --- UI SETUP ---
st.set_page_config(page_title="Precision Monitor", layout="wide")
st.title("🔬 Live Precision Measurement Dashboard")

chart_place = st.empty()
table_place = st.empty()

# --- MQTT CLIENT SETUP ---
if "mqtt_client" not in st.session_state:
    # Pass the queue into userdata so the callback can find it
    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2, userdata={'queue': st.session_state.data_queue})
    client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.tls_set()
    client.on_message = on_message
    
    try:
        client.connect(MQTT_BROKER, 8883)
        client.subscribe(TOPIC)
        client.loop_start()
        st.session_state.mqtt_client = client
        st.success("Successfully connected to HiveMQ Cloud! ✅")
    except Exception as e:
        st.error(f"Connection failed: {e}")

# --- REFRESH LOOP ---
while True:
    # 2. Pull all available data from the thread-safe queue into history
    new_data = False
    while not st.session_state.data_queue.empty():
        item = st.session_state.data_queue.get()
        st.session_state.history.append(item)
        if len(st.session_state.history) > 100: # Limit history
            st.session_state.history.pop(0)
        new_data = True

    # 3. Update the UI if we have data
    if st.session_state.history:
        df = pd.DataFrame(st.session_state.history)
        
        with chart_place.container():
            st.line_chart(df)
            
        with table_place.container():
            st.write("### Latest Measurements (µm)")
            st.table(df.tail(10)) # Matches your Excel table view

    time.sleep(1)
