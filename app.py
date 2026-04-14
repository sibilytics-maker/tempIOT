import streamlit as st
import paho.mqtt.client as mqtt
import time
import json
import pandas as pd
import plotly.graph_objects as go
from queue import Queue

# --- CONFIG ---
MQTT_BROKER = "metro.proxy.rlwy.net"
MQTT_PORT = 55113

st.set_page_config(page_title="IoT Monitor Pro", layout="centered")

# --- PROFESSIONAL STYLING ---
st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    .stButton>button {
        width: 100%;
        border-radius: 10px;
        height: 3.5em;
        font-weight: bold;
        transition: 0.3s;
        border: none;
    }
    div[data-testid="stButton"] > button:contains("FORCE") { background-color: #ff4b4b; color: white; }
    div[data-testid="stButton"] > button:contains("RESUME") { background-color: #007BFF; color: white; }
    div[data-testid="stButton"] > button:contains("SET") { background-color: #343a40; color: white; }
    /* Style for the new Reset button */
    div[data-testid="stButton"] > button:contains("RESET") { background-color: #6c757d; color: white; }
    .wifi-status { font-size: 24px; float: right; }
    </style>
""", unsafe_allow_html=True)

# --- STATE MANAGEMENT ---
if "data_queue" not in st.session_state: st.session_state.data_queue = Queue()
if "history" not in st.session_state: st.session_state.history = []
if "last_seen" not in st.session_state: st.session_state.last_seen = time.time()

# --- MQTT LOGIC ---
def on_message(client, userdata, msg):
    try:
        st.session_state.last_seen = time.time()
        payload = json.loads(msg.payload.decode())
        if "temperature" in payload:
            userdata['queue'].put({"Temperature": float(payload["temperature"]), "Time": time.time()})
    except: pass

if "mqtt_client" not in st.session_state:
    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2, userdata={'queue': st.session_state.data_queue})
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT)
    client.subscribe("temperature/sibiot233")
    client.loop_start()
    st.session_state.mqtt_client = client

# --- 1. HEADER ---
col1, col2 = st.columns([4, 1])
with col1:
    st.title("🌡️ sibiot233 Monitoring")
with col2:
    time_diff = time.time() - st.session_state.last_seen
    if time_diff < 10: st.markdown("<div class='wifi-status'>📶</div>", unsafe_allow_html=True)
    else: st.markdown("<div class='wifi-status'>❌</div>", unsafe_allow_html=True)

# --- 2. LIVE DATA FRAGMENT ---
@st.fragment(run_every=2)
def live_dashboard():
    while not st.session_state.data_queue.empty():
        item = st.session_state.data_queue.get()
        st.session_state.history.append(item)
        if len(st.session_state.history) > 40: st.session_state.history.pop(0)

    if st.session_state.history:
        df = pd.DataFrame(st.session_state.history)
        current_temp = df["Temperature"].iloc[-1]
        st.metric("Live Temperature", f"{current_temp:.2f} °C")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=list(range(len(df))), y=df["Temperature"], mode='lines', line=dict(color='#007BFF', width=4, shape='spline'), fill='tozeroy', fillcolor='rgba(0, 123, 255, 0.1)'))
        y_min, y_max = df["Temperature"].min() - 2, df["Temperature"].max() + 2
        fig.update_layout(height=300, margin=dict(l=0, r=0, t=0, b=0), plot_bgcolor='white', xaxis=dict(showgrid=False, range=[max(0, len(df)-25), len(df)-1]), yaxis=dict(showgrid=True, gridcolor='#f0f0f0', range=[y_min, y_max]))
        st.plotly_chart(fig, use_container_width=True)

live_dashboard()

# --- 3. SYSTEM CONTROLS ---
st.subheader("⚙️ System Controls")
with st.form("control_form", clear_on_submit=False):
    threshold = st.number_input("Buzzer Threshold (°C)", value=60.0, step=0.5)
    submit = st.form_submit_button("UPDATE SETTINGS")
    if submit:
        st.session_state.mqtt_client.publish("temperature/setThreshold", str(threshold))
        st.toast("Settings Saved")

st.write("") 
col_stop, col_resume = st.columns(2)
with col_stop:
    if st.button("🛑 FORCE STOP", key="stop"):
        st.session_state.mqtt_client.publish("temperature/buzzerControl", "OFF")
        st.toast("Buzzer OFF Sent")
with col_resume:
    if st.button("🔄 RESUME AUTO", key="resume"):
        st.session_state.mqtt_client.publish("temperature/buzzerControl", "ON")
        st.toast("Auto Mode Sent")

# --- 4. ADVANCED SETTINGS (New Reset Option) ---
with st.expander("🛠️ Advanced Settings"):
    st.write("Warning: This will disconnect the device from current WiFi.")
    if st.button("🔧 RESET DEVICE WIFI", key="reset_wifi"):
        # This matches the "RESET_WIFI" check in your ESP32 code
        st.session_state.mqtt_client.publish("temperature/sibiot233/control", "RESET_WIFI")
        st.success("WiFi Reset command sent! ✅")
