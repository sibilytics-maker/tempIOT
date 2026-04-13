import streamlit as st
import paho.mqtt.client as mqtt
import json
import pandas as pd
import time
from queue import Queue
import plotly.graph_objects as go

# --- CONFIGURATION ---
MQTT_BROKER = "3303e98efb894e9aae37b18b94dfca8a.s1.eu.hivemq.cloud"
MQTT_USER = "kundaniot"
MQTT_PASS = "Kundan@1985"

params = st.query_params
device_id = params.get("device", "sibiot233") 

st.set_page_config(page_title=f"Monitor: {device_id}", layout="centered")

# --- CUSTOM PROFESSIONAL STYLING ---
st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        height: 3em;
        font-weight: bold;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    /* Force Stop Button Styling */
    div[data-testid="stButton"] > button:first-child:active, 
    div[data-testid="stButton"] > button:focus:not(:active) {
        border-color: #ff4b4b;
        color: #ff4b4b;
    }
    </style>
""", unsafe_allow_html=True)

# --- MQTT SETUP ---
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

# --- 1. LIVE HEADER (TOP) ---
st.title(f"🌡️ {device_id} Monitoring")
metric_placeholder = st.empty()
chart_placeholder = st.empty()

st.markdown("---")

# --- 2. CONTROLS (BOTTOM) ---
with st.container():
    st.subheader("⚙️ System Controls")
    
    # Threshold Row
    col_input, col_btn = st.columns([3, 1])
    with col_input:
        threshold_input = st.number_input("Buzzer Threshold (°C)", value=60.0, step=0.5)
    with col_btn:
        st.write("##") # Spacing
        if st.button("SET", type="primary"):
            st.session_state.mqtt_client.publish("temperature/setThreshold", str(threshold_input))
            st.toast("Threshold Updated", icon="✅")

    # Override Row
    btn_stop, btn_resume = st.columns(2)
    with btn_stop:
        if st.button("🛑 FORCE STOP", help="Cuts power to buzzer immediately"):
            st.session_state.mqtt_client.publish("temperature/buzzerControl", "OFF")
            st.toast("Buzzer Force-Stopped", icon="🔕")
    with btn_resume:
        if st.button("🔄 RESUME AUTO", help="Returns to temperature-based logic"):
            st.session_state.mqtt_client.publish("temperature/buzzerControl", "ON")
            st.toast("Auto-Mode Active", icon="🔄")

# --- 3. MAIN LOOP ---
chart_count = 0
while True:
    while not st.session_state.data_queue.empty():
        item = st.session_state.data_queue.get()
        st.session_state.history.append(item)
        if len(st.session_state.history) > 50: st.session_state.history.pop(0)

    if st.session_state.history:
        df = pd.DataFrame(st.session_state.history)
        current_temp = df["Temperature"].iloc[-1]
        
        # Metric
        metric_placeholder.metric(label="Live Temperature", value=f"{current_temp:.2f} °C")
            
        # Professional Chart
        fig = go.Figure()
        
        # Smooth Spline Line
        fig.add_trace(go.Scatter(
            x=df.index, y=df["Temperature"],
            mode='lines', line=dict(color='#007BFF', width=4, shape='spline'),
            fill='tozeroy', fillcolor='rgba(0, 123, 255, 0.05)',
            name="Temperature"
        ))
        
        # --- LOGIC FIX: Correct Alert Label ---
        # Checks against your 'threshold_input' variable
        if current_temp >= threshold_input:
            label_text = "⚠️ HIGH TEMP"
            label_color = "Red"
        else:
            label_text = "✅ NORMAL"
            label_color = "#28a745" # Professional Green

        fig.add_annotation(
            x=len(df)-1, y=current_temp, text=label_text,
            showarrow=True, arrowhead=1, bgcolor=label_color,
            font=dict(color="white", size=12), ax=-40, ay=-40
        )

        # Labeling and Axis Styling
        fig.update_layout(
            height=350, margin=dict(l=10, r=10, t=10, b=10),
            plot_bgcolor='white',
            hovermode="x unified",
            xaxis=dict(
                title="Time (Last 50 Samples)", 
                showgrid=False, 
                linecolor='lightgray',
                range=[len(df)-25, len(df)]
            ),
            yaxis=dict(
                title="Temperature (°C)", 
                showgrid=True, 
                gridcolor='#f0f0f0',
                range=[df["Temperature"].min()-1.5, df["Temperature"].max()+1.5]
            )
        )

        with chart_placeholder.container():
            st.plotly_chart(fig, use_container_width=True, key=f"t_{chart_count}")
            chart_count += 1
            
    time.sleep(1)
