import streamlit as st
import paho.mqtt.client as mqtt
import time
import json
import pandas as pd
import plotly.graph_objects as go
from queue import Queue
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

# --- CONFIG ---
MQTT_BROKER = "metro.proxy.rlwy.net"
MQTT_PORT = 55113
# Streamlit logic often requires these defined
MQTT_USER = os.getenv("MQTT_USER", "kundan")
MQTT_PASS = os.getenv("MQTT_PASS", "Kundan@1985")

# --- FASTAPI BACKEND ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT)
    mqtt_client.loop_start()
    yield
    mqtt_client.loop_stop()

api = FastAPI(lifespan=lifespan)
api.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

mqtt_client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)

@api.post("/control")
def control_device(data: dict):
    topic = f"{data.get('device_id', 'smartplug')}/control"
    mqtt_client.publish(topic, data.get("action"))
    return {"status": "sent"}

# --- STREAMLIT FRONTEND ---
params = st.query_params
device_id = params.get("device", "sibiot233") 

st.set_page_config(page_title=f"Monitor: {device_id}", layout="centered")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 8px; height: 3em; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

if "data_queue" not in st.session_state: st.session_state.data_queue = Queue()
if "history" not in st.session_state: st.session_state.history = []

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        val = float(payload.get("temperature", 0.0))
        st.session_state.data_queue.put({"Temperature": val})
    except: pass

if "mqtt_client" not in st.session_state:
    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT)
    client.subscribe(f"temperature/{device_id}")
    client.loop_start()
    st.session_state.mqtt_client = client

st.title(f"🌡️ {device_id} Monitoring")
metric_placeholder = st.empty()
chart_placeholder = st.empty()

st.markdown("---")

with st.container():
    st.subheader("⚙️ System Controls")
    col_input, col_btn = st.columns([3, 1])
    with col_input:
        threshold_input = st.number_input("Buzzer Threshold (°C)", value=60.0, step=0.5)
    with col_btn:
        st.write("##")
        if st.button("SET", type="primary"):
            st.session_state.mqtt_client.publish("temperature/setThreshold", str(threshold_input))
            st.toast("Threshold Updated", icon="✅")

# --- MAIN REAL-TIME LOOP ---
while True:
    while not st.session_state.data_queue.empty():
        item = st.session_state.data_queue.get()
        st.session_state.history.append(item)
        if len(st.session_state.history) > 50: st.session_state.history.pop(0)

    if st.session_state.history:
        df = pd.DataFrame(st.session_state.history)
        current_temp = df["Temperature"].iloc[-1]
        metric_placeholder.metric(label="Live Temperature", value=f"{current_temp:.2f} °C")
            
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df.index, y=df["Temperature"], mode='lines', 
                                 line=dict(color='#007BFF', width=4, shape='spline'),
                                 fill='tozeroy', name="Temp"))

        label_text, label_color = ("⚠️ HIGH", "Red") if current_temp >= threshold_input else ("✅ NORMAL", "Green")
        fig.add_annotation(x=len(df)-1, y=current_temp, text=label_text, bgcolor=label_color, font=dict(color="white"))
        
        fig.update_layout(height=350, plot_bgcolor='white', margin=dict(l=0,r=0,t=0,b=0))
        chart_placeholder.plotly_chart(fig, use_container_width=True)
            
    time.sleep(1)
