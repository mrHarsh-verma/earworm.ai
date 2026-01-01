import streamlit as st
import requests
import time
import base64
import hmac
import hashlib
import json
import os
import numpy as np
from scipy.io import wavfile
import noisereduce as nr
from st_audiorec import st_audiorec

# --- PAGE SETUP ---
st.set_page_config(page_title="Earworm AI", page_icon="🎵")

st.title("🎵 Earworm AI")
st.subheader("Can't remember the lyrics? Just hum the tune!")

# --- 1. INITIALIZE SESSION STATE ---
if 'hum_count' not in st.session_state:
    st.session_state['hum_count'] = 0

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Settings")
    st.write("This app uses ACRCloud technology.")
    
    frees_left = 3 - st.session_state['hum_count']
    if frees_left > 0:
        st.info(f"⚡ Free Hums left this session: **{frees_left}**")
    else:
        st.error("🚫 Free limit reached.")

    # KEYS (Keep your keys safe!)
    HOST = "identify-ap-southeast-1.acrcloud.com"
    ACCESS_KEY = "b556853ba8fdf4b285dc0432ee903bf9"
    ACCESS_SECRET = "pVSWuLTcGsF2x26HzBOahM0aUjHOxIONeVXI8Wa7"

# --- NEW FUNCTION: NOISE CANCELLATION 🔇 ---
def remove_noise(input_filename):
    # 1. Load the recorded file
    rate, data = wavfile.read(input_filename)
    
    # 2. Perform Noise Reduction (The "Nitrogen")
    # We assume the noise is stationary (like a fan or AC)
    reduced_noise = nr.reduce_noise(y=data, sr=rate, stationary=True, prop_decrease=0.8)
    
    # 3. Save the clean file
    clean_filename = "clean_recording.wav"
    wavfile.write(clean_filename, rate, reduced_noise)
    
    return clean_filename

# --- API FUNCTION ---
def identify_hum(filename):
    http_method = "POST"
    http_uri = "/v1/identify"
    data_type = "audio"
    signature_version = "1"
    timestamp = str(int(time.time()))
    
    string_to_sign = http_method + "\n" + http_uri + "\n" + ACCESS_KEY + "\n" + data_type + "\n" + signature_version + "\n" + timestamp
    sign = base64.b64encode(hmac.new(ACCESS_SECRET.encode('ascii'), string_to_sign.encode('ascii'), digestmod=hashlib.sha1).digest()).decode('ascii')

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

# --- MAIN APP ---
if st.session_state['hum_count'] < 3:
    st.info("👇 Press the microphone button to start recording. Hum for 10 seconds, then press it again to stop.")
    
    wav_audio_data = st_audiorec()

    if wav_audio_data is not None:
        if st.button("🚀 Analyze Hum"):
            st.session_state['hum_count'] += 1
            
            # Step 1: Save Raw File
            with open("temp_raw.wav", "wb") as f:
                f.write(wav_audio_data)
            
            # Step 2: Clean the Noise (The Magic Step)
            with st.spinner("🔇 Removing Background Noise..."):
                try:
                    clean_file = remove_noise("temp_raw.wav")
                except Exception as e:
                    st.warning(f"Noise cancellation failed, using raw audio. (Error: {e})")
                    clean_file = "temp_raw.wav"

            # Step 3: Send to AI
            with st.spinner("🎵 Asking the AI..."):
                result = identify_hum(clean_file)
            
            if result and result['status']['msg'] == 'Success':
                metadata = result['metadata']
                if 'humming' in metadata:
                    song = metadata['humming'][0]
                elif 'music' in metadata:
                    song = metadata['music'][0]
                else:
                    song = None
                    
                if song:
                    score = song['score']
                    if score >= 40:
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
                            st.metric("Confidence", f"{score}%")
                        
                        query = f"{song['title']} {song['artists'][0]['name']}"
                        st.markdown("---")
                        st.markdown(f"👉 **[Listen on YouTube](https://www.youtube.com/results?search_query={query.replace(' ', '+')})**")
                        st.markdown(f"👉 **[Listen on Spotify](https://open.spotify.com/search/{query.replace(' ', '%20')})**")
                    else:
                        st.warning(f"🤔 I heard a melody, but I'm not sure. (Confidence: {score}%)")
                        st.write("It sounded a little like **" + song['title'] + "**, but that might be wrong.")
                else:
                    st.warning("I heard you, but couldn't match the song.")
            else:
                st.error("❌ No match found. Try humming louder!")
else:
    st.error("🚫 **Daily Free Limit Reached**")
    st.markdown("You have used your 3 free hums for this session.")
    st.info("Tip: Refresh the page to reset (Development Mode).")