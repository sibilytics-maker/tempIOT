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

params = st.query_params
device_id = params.get("device", "sibiot233") 

st.set_page_config(page_title=f"Railway Monitor: {device_id}", layout="centered")

# --- MQTT SETUP (Keep this at the top so it starts first) ---
if "data_queue" not in st.session_state: st.session_state.data_queue = Queue()
if "history" not in st.session_state: st.session_state.history = []

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        val = float(payload.get("temperature", 0.0))
        userdata['queue'].put({"Temperature": val})
    except: pass

if "mqtt_client" not in st.session_state:
    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2, userdata={'queue': st.session_state.data_queue})
    client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.tls_set()
    client.on_message = on_message
    client.connect(MQTT_BROKER, 8883)
    client.subscribe(f"temperature/{device_id}")
    client.loop_start()
    st.session_state.mqtt_client = client

# --- 1. LIVE DATA HEADER (TOP OF MOBILE SCREEN) ---
st.title(f"🌡️ {device_id}")
metric_placeholder = st.empty()
chart_placeholder = st.empty()

st.markdown("---")

# --- 2. BUZZER CONTROLS (BOTTOM OF MOBILE SCREEN) ---
st.subheader("🚨 Alarm Controls")
with st.container():
    col1, col2 = st.columns([2, 1])
    with col1:
        threshold_input = st.number_input("Set Alert Threshold (°C)", value=45.0, step=0.5)
    with col2:
        st.write("##")
        if st.button("Update", use_container_width=True):
            st.session_state.mqtt_client.publish("temperature/setThreshold", str(threshold_input))
            st.toast("Threshold Updated!")

    btn_col1, btn_col2 = st.columns(2)
    with btn_col1:
        if st.button("🛑 FORCE STOP", use_container_width=True):
            st.session_state.mqtt_client.publish("temperature/buzzerControl", "OFF")
            st.toast("Buzzer Stopped")
    with btn_col2:
        if st.button("🔄 RESUME AUTO", use_container_width=True):
            st.session_state.mqtt_client.publish("temperature/buzzerControl", "ON")
            st.toast("Auto-Mode Resumed")

# --- 3. MAIN LOGIC LOOP ---
chart_count = 0
while True:
    while not st.session_state.data_queue.empty():
        item = st.session_state.data_queue.get()
        st.session_state.history.append(item)
        if len(st.session_state.history) > 50: st.session_state.history.pop(0)

    if st.session_state.history:
        df = pd.DataFrame(st.session_state.history)
        current_temp = df["Temperature"].iloc[-1]
        
        # Metric at the top
        metric_placeholder.metric(label="Current Temperature", value=f"{current_temp:.2f} °C")
            
        # Professional Chart
        fig = go.Figure()
        
        # Add smooth temperature line
        fig.add_trace(go.Scatter(
            x=df.index, y=df["Temperature"],
            mode='lines', line=dict(color='#007BFF', width=4, shape='spline'),
            fill='tozeroy', fillcolor='rgba(0, 123, 255, 0.1)'
        ))
        
        # --- FIX: Alert Logic based on SIDEBAR THRESHOLD ---
        if current_temp >= threshold_input:
            fig.add_annotation(
                x=len(df)-1, y=current_temp, text="⚠️ HIGH TEMP",
                bgcolor="red", font=dict(color="white"), showarrow=True
            )
        else:
            fig.add_annotation(
                x=len(df)-1, y=current_temp, text="✅ NORMAL",
                bgcolor="#28a745", font=dict(color="white"), showarrow=True
            )

        fig.update_layout(
            height=300, margin=dict(l=10, r=10, t=10, b=10),
            xaxis=dict(showgrid=False, range=[len(df)-20, len(df)]),
            yaxis=dict(showgrid=True, range=[df["Temperature"].min()-1, df["Temperature"].max()+1]),
            plot_bgcolor='white'
        )

        with chart_placeholder.container():
            st.plotly_chart(fig, use_container_width=True, key=f"t_{chart_count}")
            chart_count += 1
            
    time.sleep(1)
