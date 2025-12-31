import streamlit as st
import requests
import time
import base64
import hmac
import hashlib
import json
import os
from st_audiorec import st_audiorec

# --- PAGE SETUP ---
st.set_page_config(page_title="Earworm AI", page_icon="🎵")

st.title("🎵 Earworm AI")
st.subheader("Can't remember the lyrics? Just hum the tune!")

# --- 1. INITIALIZE SESSION STATE (The Counter) ---
if 'hum_count' not in st.session_state:
    st.session_state['hum_count'] = 0

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Settings")
    st.write("This app uses ACRCloud technology.")
    
    # Show usage to the user (Psychological Pressure)
    frees_left = 3 - st.session_state['hum_count']
    if frees_left > 0:
        st.info(f"⚡ Free Hums left this session: **{frees_left}**")
    else:
        st.error("🚫 Free limit reached.")

    HOST = "identify-ap-southeast-1.acrcloud.com"
    ACCESS_KEY = "b556853ba8fdf4b285dc0432ee903bf9"
    ACCESS_SECRET = "pVSWuLTcGsF2x26HzBOahM0aUjHOxIONeVXI8Wa7"

# --- FUNCTIONS ---
def identify_hum(audio_bytes):
    filename = "temp_recording.wav"
    with open(filename, "wb") as f:
        f.write(audio_bytes)

    http_method = "POST"
    http_uri = "/v1/identify"
    data_type = "audio"
    signature_version = "1"
    timestamp = str(int(time.time()))
    
    string_to_sign = http_method + "\n" + http_uri + "\n" + ACCESS_KEY + "\n" + data_type + "\n" + signature_version + "\n" + timestamp
    sign = base64.b64encode(hmac.new(ACCESS_SECRET.encode('ascii'), string_to_sign.encode('ascii'), digestmod=hashlib.sha1).digest()).decode('ascii')

    if not os.path.exists(filename):
        return None

    files = [('sample', (filename, open(filename, 'rb'), 'audio/wav'))]
    data = {'access_key': ACCESS_KEY, 'sample_bytes': os.path.getsize(filename), 'timestamp': timestamp, 'signature': sign, 'data_type': data_type, "signature_version": signature_version}
    
    req_url = "https://" + HOST + "/v1/identify"
    
    try:
        response = requests.post(req_url, files=files, data=data)
        result = json.loads(response.text)
        return result
    except Exception as e:
        st.error(f"Connection Error: {e}")
        return None

# --- MAIN APP LOGIC ---

# 2. CHECK LIMIT BEFORE SHOWING RECORDER
if st.session_state['hum_count'] < 3:
    st.info("👇 Press the microphone button to start recording. Hum for 10 seconds, then press it again to stop.")
    
    # The Recorder
    wav_audio_data = st_audiorec()

    if wav_audio_data is not None:
        # Note: We removed the extra 'st.audio' line here to fix the double player issue!
        
        if st.button("🚀 Analyze Hum"):
            # Increment the counter
            st.session_state['hum_count'] += 1
            
            with st.spinner("Asking the AI..."):
                result = identify_hum(wav_audio_data)
            
            if result and result['status']['msg'] == 'Success':
                metadata = result['metadata']
                if 'humming' in metadata:
                    song = metadata['humming'][0]
                elif 'music' in metadata:
                    song = metadata['music'][0]
                else:
                    song = None
                    
                if song:
                    st.balloons()
                    st.success("🎉 WE FOUND IT!")
                    st.markdown(f"### 🎵 **{song['title']}**")
                    
                    c1, c2 = st.columns(2)
                    with c1:
                        if 'artists' in song:
                            st.write(f"**👤 Artist:** {song['artists'][0]['name']}")
                        if 'album' in song:
                            st.write(f"**💿 Album:** {song['album']['name']}")
                    with c2:
                        st.metric("Confidence", f"{song['score']}%")
                    
                    query = f"{song['title']} {song['artists'][0]['name']}"
                    st.markdown("---")
                    st.markdown(f"👉 **[Listen on YouTube](https://www.youtube.com/results?search_query={query.replace(' ', '+')})**")
                    st.markdown(f"👉 **[Listen on Spotify](https://open.spotify.com/search/{query.replace(' ', '%20')})**")
                else:
                    st.warning("I heard you, but couldn't match the song.")
            else:
                st.error("❌ No match found. Try humming louder!")

else:
    # 3. SHOW THIS WHEN LIMIT IS REACHED
    st.error("🚫 **Daily Free Limit Reached**")
    st.markdown("You have used your 3 free hums for this session.")
    st.markdown("### 🔓 Want Unlimited Access?")
    st.write("To keep the server running, we offer a Premium Pass.")
    
    # Simple Contact / Payment Link (Since we don't have Stripe setup yet)
    st.link_button("Buy Premium Access (Coming Soon)", "https://www.paypal.com/") 
    st.info("Tip: For now, you can refresh the page to reset the counter (Shhh! 🤫)")