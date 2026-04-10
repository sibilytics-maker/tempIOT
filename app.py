import streamlit as st
import paho.mqtt.client as mqtt
import json
import pandas as pd
import time
from queue import Queue
import plotly.express as px

# --- CONFIGURATION ---
MQTT_BROKER = "93be88c856bc40329b96e8fba46ac044.s1.eu.hivemq.cloud"
MQTT_USER = "kundan"
MQTT_PASS = "Kundan@1985"
TOPIC = "temperature/data"

if "data_queue" not in st.session_state:
    st.session_state.data_queue = Queue()

if "history" not in st.session_state:
    st.session_state.history = []

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        val = float(payload.get("temperature", 0.0))
        userdata['queue'].put({"Temperature": val})
    except Exception as e:
        print(f"MQTT Error: {e}")

st.set_page_config(page_title="Temperature Monitor", layout="wide")
st.title("🌡️ Live Temperature")

chart_place = st.empty()
table_place = st.empty()

# --- MQTT SETUP ---
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
    except Exception as e:
        st.error(f"Connection failed: {e}")

# --- REFRESH LOOP ---
while True:
    while not st.session_state.data_queue.empty():
        item = st.session_state.data_queue.get()
        st.session_state.history.append(item)
        if len(st.session_state.history) > 50:
            st.session_state.history.pop(0)

    if st.session_state.history:
        df = pd.DataFrame(st.session_state.history)
        
        # --- CUSTOM PLOTLY CHART ---
        fig = px.area(
            df, 
            y="Temperature", 
            line_shape='spline', # Makes the lines smooth
        )
        
        # Style: Transparent blue fill (0.2 opacity), visible markers
        fig.update_traces(
            fillcolor='rgba(0, 100, 250, 0.2)', # Blue with 20% opacity
            line=dict(color='rgba(0, 100, 250, 0.8)', width=3),
            marker=dict(size=8, symbol='circle') # Round markers on the tips
        )
        
        fig.update_layout(
            margin=dict(l=20, r=20, t=30, b=20),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            yaxis=dict(showgrid=True, gridcolor='lightgray')
        )

        with chart_place.container():
            st.plotly_chart(fig, use_container_width=True)
            
        with table_place.container():
            st.write("### Latest Measurements")
            st.table(df.tail(5))

    time.sleep(1)
