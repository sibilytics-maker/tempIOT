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

# --- DEVICE NAME LOGIC ---
params = st.query_params
device_id = params.get("device", "sibiot233") 

st.set_page_config(page_title=f"Monitor: {device_id}", layout="centered")
st.markdown("""
    <style>
    .block-container { padding-top: 1rem; }
    </style>
""", unsafe_allow_html=True)

# --- UI HEADER ---
# --- HEADER ---
st.title(f"🌡️ {device_id}")
st.markdown("---")

# --- MOBILE FRIENDLY CONTROLS (Main Page) ---
with st.container():
    st.subheader("🚨 Buzzer & Alarm Controls")
    
    # Use columns for threshold input and button
    col1, col2 = st.columns([2, 1])
    with col1:
        threshold_input = st.number_input("Set Threshold (°C)", min_value=0.0, max_value=100.0, value=45.0)
    with col2:
        st.write("##") # Spacing
        if st.button("Update"):
            st.session_state.mqtt_client.publish("temperature/setThreshold", str(threshold_input))
            st.toast("Updated!", icon="✅")

    # Force Stop and Resume Buttons side-by-side
    btn_col1, btn_col2 = st.columns(2)
    with btn_col1:
        if st.button("🛑 FORCE STOP", use_container_width=True):
            st.session_state.mqtt_client.publish("temperature/buzzerControl", "OFF")
    with btn_col2:
        if st.button("🔄 RESUME AUTO", use_container_width=True):
            st.session_state.mqtt_client.publish("temperature/buzzerControl", "ON")

st.markdown("---")


               

if "data_queue" not in st.session_state: st.session_state.data_queue = Queue()
if "history" not in st.session_state: st.session_state.history = []

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        # Matches your ESP32 payload key "temperature"
        val = float(payload.get("temperature", 0.0))
        userdata['queue'].put({"Temperature": val})
    except: pass

# --- MQTT SETUP ---
if "mqtt_client" not in st.session_state:
    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2, userdata={'queue': st.session_state.data_queue})
    client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.tls_set()
    client.on_message = on_message
    client.connect(MQTT_BROKER, 8883)
    client.subscribe(f"temperature/{device_id}")
    client.loop_start()
    st.session_state.mqtt_client = client

# --- METRIC CARD CONTAINER ---
metric_placeholder = st.empty()
chart_place = st.empty()
chart_count = 0

# --- MAIN LOOP ---
while True:
    while not st.session_state.data_queue.empty():
        item = st.session_state.data_queue.get()
        st.session_state.history.append(item)
        if len(st.session_state.history) > 50: st.session_state.history.pop(0)

    if st.session_state.history:
        df = pd.DataFrame(st.session_state.history)
        current_temp = df["Temperature"].iloc[-1]
        
        # --- DYNAMIC ADJUSTMENT ---
        min_temp = df["Temperature"].min()
        max_temp = df["Temperature"].max()
        buffer = 0.2 
        
        # --- SHOW METRIC ---
        with metric_placeholder.container():
            st.metric(label="Latest Reading", value=f"{current_temp:.2f} °C")
            
        # --- PROFESSIONAL CHART ---
          # --- HIGHLY PROFESSIONAL CHART ---
        fig = go.Figure()

        # 1. Add the Threshold Line (Visual Guide)
        fig.add_shape(
            type="line", line=dict(color="red", width=2, dash="dash"),
            x0=0, x1=len(df), y0=threshold_input, y1=threshold_input
        )

        # 2. Add the Temperature Trace with Spline Smoothing
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df["Temperature"],
            mode='lines',
            name="Temperature",
            line=dict(color='#007BFF', width=4, shape='spline'), # Spline makes it smooth
            fill='tozeroy',
            fillcolor='rgba(0, 123, 255, 0.1)' # Light blue modern fill
        ))

        # 3. Modern Industrial Layout
        fig.update_layout(
            hovermode="x unified",
            height=350,
            margin=dict(l=10, r=10, t=10, b=10),
            plot_bgcolor='rgba(0,0,0,0)', # Transparent background
            paper_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(
                showgrid=False, 
                zeroline=False,
                showline=True,
                linecolor='lightgray',
                title="Time (Last 50 Samples)"
            ),
            yaxis=dict(
                showgrid=True, 
                gridcolor='#f0f0f0', # Subtle grid lines
                zeroline=False,
                showline=True,
                linecolor='lightgray',
                title="Temp (°C)",
                range=[min_temp - 2, max_temp + 2] # Dynamic zoom
            ),
            showlegend=False
        )

        # 4. Add "Alert" annotation if above threshold
               # --- ALERT LOGIC (MATCH TO SIDEBAR) ---
        if current_temp >= threshold_input:
            # Show red alert if temp is actually above your sidebar setting
            fig.add_annotation(
                x=len(df)-1, y=current_temp,
                text="⚠️ HIGH TEMP",
                showarrow=True, arrowhead=1,
                bgcolor="red", font=dict(color="white")
            )
        else:
            # Show green normal if temp is below your sidebar setting
            fig.add_annotation(
                x=len(df)-1, y=current_temp,
                text="✅ NORMAL",
                showarrow=True, arrowhead=1,
                bgcolor="#28a745", font=dict(color="white")
            )

        # Add a dashed line on the chart to show exactly where the threshold is
        fig.add_hline(y=threshold_input, line_dash="dash", line_color="red", opacity=0.5)


        with chart_place.container():
            st.plotly_chart(fig, use_container_width=True, key=f"t_{chart_count}", config={'displayModeBar': False})
            chart_count += 1

            
    time.sleep(1)
