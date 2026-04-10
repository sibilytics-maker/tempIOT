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
        userdata['queue'].put({
            "Temperature": payload.get("temperature", 0.0)
        })
    except Exception as e:
        print(f"MQTT Error: {e}")

# --- UI SETUP ---
st.set_page_config(page_title="Temperature Monitor", layout="wide")
st.title("🌡️ Live Temperature Spikes")

chart_place = st.empty()
table_place = st.empty()

# --- MQTT CLIENT SETUP ---
if "mqtt_client" not in st.session_state:
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
    new_data = False
    while not st.session_state.data_queue.empty():
        item = st.session_state.data_queue.get()
        st.session_state.history.append(item)
        if len(st.session_state.history) > 100:
            st.session_state.history.pop(0)
        new_data = True

    if st.session_state.history:
        df = pd.DataFrame(st.session_state.history)
        
        with chart_place.container():
            # Using area_chart creates that filled-in, sharp "peak" look 
            # similar to your drawing
            st.area_chart(df)
            
        with table_place.container():
            st.write("### Latest Measurements (°C)")
            st.table(df.tail(10))

    time.sleep(1)
