# -*- coding: utf-8 -*-
import os
import time
import glob
import json
import streamlit as st
from bokeh.models.widgets import Button
from bokeh.models import CustomJS
from streamlit_bokeh_events import streamlit_bokeh_events
from PIL import Image
from gtts import gTTS
from googletrans import Translator

# =============================
# Configuración de página
# =============================
st.set_page_config(
    page_title="🎧 Traductor por Voz · Tech Mode",
    page_icon="🎤",
    layout="centered",
    initial_sidebar_state="expanded"
)

# =============================
# Estilos (dark + neón)
# =============================
st.markdown("""
<style>
  :root{
    --bg:#0b1220; --panel:#0f182b; --text:#e6f7ff; --muted:#9fb3c8;
    --accent:#00e5ff; --accent2:#00ffa3; --danger:#ff4d4f;
  }
  html, body, .stApp{
    background: radial-gradient(1000px 600px at 10% 0%, #0f1a30 0%, var(--bg) 60%);
    color: var(--text) !important;
  }
  [data-testid="stSidebar"]{
    background: linear-gradient(180deg,#0e1628 0%,#091021 100%) !important;
    border-right: 1px solid rgba(0,229,255,.15);
  }
  h1,h2,h3,h4,h5,h6{
    color: var(--accent);
    font-family:"JetBrains Mono", monospace;
    letter-spacing:.4px;
  }
  p, label, span, .stMarkdown{
    color: var(--text) !important;
    font-family:"Inter", system-ui, -apple-system, "Segoe UI", Roboto, Arial, sans-serif;
  }
  .card{
    background: var(--panel);
    border:1px solid rgba(0,229,255,.12);
    border-radius:14px; padding:16px 18px;
    box-shadow:0 0 24px rgba(0,0,0,.25);
  }
  .stButton>button{
    width:100%;
    background: linear-gradient(90deg, var(--accent) 0%, var(--accent2) 100%) !important;
    color:#00121a !important; border:none !important; border-radius:12px !important;
    font-weight:700 !important; box-shadow:0 0 14px rgba(0,229,255,.35);
    transition: transform .08s ease-in-out, box-shadow .2s ease-in-out;
  }
  .stButton>button:hover{ transform: translateY(-1px); box-shadow:0 0 20px rgba(0,229,255,.55); }
  .pill { display:inline-block; padding:4px 10px; border-radius:999px; font-size:12px;
          border:1px solid rgba(0,229,255,.35); background:rgba(0,229,255,.12); color:var(--accent);}
  .pill.warn { background:rgba(255,77,79,.08); color:#ffb3b4; border-color:rgba(255,77,79,.35);}
</style>
""", unsafe_allow_html=True)

# =============================
# Estado
# =============================
if "transcript" not in st.session_state:
    st.session_state.transcript = ""
if "output_text" not in st.session_state:
    st.session_state.output_text = ""
if "audio_path" not in st.session_state:
    st.session_state.audio_path = ""

# =============================
# Utilidades
# =============================
def ensure_temp():
    try: os.makedirs("temp", exist_ok=True)
    except Exception as e: st.error(f"❌ No se pudo crear carpeta temporal: {e}")

def cleanup_old_mp3(days=7):
    now = time.time()
    for f in glob.glob("temp/*.mp3"):
        try:
            if os.stat(f).st_mtime < now - days*86400:
                os.remove(f)
        except Exception:
            pass

def language_code(name:str)->str:
    mapping = {
        "Español":"es", "Inglés":"en", "Bengalí":"bn", "Coreano":"ko",
        "Mandarín":"zh-cn", "Japonés":"ja", "Portugués":"pt", "Francés":"fr", "Alemán":"de", "Italiano":"it"
    }
    return mapping.get(name, "es")

def tld_from_accent(name:str)->str:
    mapping = {
        "Defecto":"com", "España":"es", "México":"com.mx", "Estados Unidos":"com",
        "Reino Unido":"co.uk", "Canadá":"ca", "Australia":"com.au", "Irlanda":"ie", "Sudáfrica":"co.za"
    }
    return mapping.get(name, "com")

# =============================
# Encabezado
# =============================
st.title("🎧 Traductor por Voz — Tech Mode")
st.caption("Habla → transcribe (Web Speech API) → traduce (Google) → habla (gTTS).")

# Imagen (opcional)
try:
    img = Image.open("OIG7.jpg")
    st.image(img, width=320)
except Exception as e:
    st.info("Sugerencia: coloca una imagen `OIG7.jpg` en el directorio para mostrarla aquí.")

# =============================
# Sidebar
# =============================
with st.sidebar:
    st.subheader("⚙️ Ajustes de traducción")
    in_lang_name = st.selectbox("Idioma de entrada", ["Español","Inglés","Bengalí","Coreano","Mandarín","Japonés","Portugués","Francés","Alemán","Italiano"], index=0)
    out_lang_name = st.selectbox("Idioma de salida", ["Inglés","Español","Bengalí","Coreano","Mandarín","Japonés","Portugués","Francés","Alemán","Italiano"], index=1)
    accent = st.selectbox("Acento de síntesis (gTTS)", ["Defecto","España","México","Estados Unidos","Reino Unido","Canadá","Australia","Irlanda","Sudáfrica"], index=0)
    st.markdown("<span class='pill'>Consejo:</span> Si no se reproduce audio, descarga el archivo y pruébalo localmente.", unsafe_allow_html=True)

# =============================
# Tarjeta de micrófono
# =============================
st.markdown("### 🎙️ Captura por voz")
st.write("Presiona el botón y **habla**. Requiere Chrome/Edge (Web Speech API).")

mic_col = st.container()
with mic_col:
    # Botón Bokeh que activa reconocimiento del navegador
    stt_button = Button(label="Escuchar  🎤", width=280, height=48)
    stt_button.js_on_event("button_click", CustomJS(code="""
        try{
          var Speech = window.SpeechRecognition || window.webkitSpeechRecognition;
          var recognition = new Speech();
          recognition.continuous = true;
          recognition.interimResults = true;
          recognition.lang = 'auto';
          recognition.onresult = function (e) {
              var value = "";
              for (var i = e.resultIndex; i < e.results.length; ++i) {
                  if (e.results[i].isFinal) { value += e.results[i][0].transcript; }
              }
              if (value !== "") {
                  document.dispatchEvent(new CustomEvent("GET_TEXT", {detail: value}));
              }
          };
          recognition.onerror = function(ev){ 
              document.dispatchEvent(new CustomEvent("GET_TEXT", {detail: "ERROR: " + ev.error}));
          };
          recognition.start();
        }catch(err){
          document.dispatchEvent(new CustomEvent("GET_TEXT", {detail: "ERROR: Web Speech API no disponible"}));
        }
    """))

    result = streamlit_bokeh_events(
        stt_button,
        events="GET_TEXT",
        key="listen",
        refresh_on_update=False,
        override_height=75,
        debounce_time=0
    )

# =============================
# Procesar transcripción
# =============================
if result and "GET_TEXT" in result:
    transcript = str(result.get("GET_TEXT", "")).strip()
    st.session_state.transcript = transcript
    if transcript.startswith("ERROR:"):
        st.markdown("<span class='pill warn'>No se pudo usar reconocimiento de voz en este navegador</span>", unsafe_allow_html=True)
    else:
        st.success("📝 Texto capturado con éxito")
        st.write(st.session_state.transcript)

# =============================
# Traducción + TTS
# =============================
if st.session_state.transcript:
    st.markdown("---")
    st.markdown("### 🔄 Traducir y convertir a audio")
    translator = Translator()
    ensure_temp()

    colA, colB = st.columns(2)
    with colA:
        show_text = st.checkbox("Mostrar texto de salida", value=True)
    with colB:
        slow_voice = st.checkbox("Voz lenta (gTTS)", value=False)

    if st.button("Convertir 🎧"):
        try:
            src = language_code(in_lang_name)
            dst = language_code(out_lang_name)
            tld = tld_from_accent(accent)

            # Traducción
            translation = translator.translate(st.session_state.transcript, src=src, dest=dst)
            out_text = translation.text
            st.session_state.output_text = out_text

            # TTS
            tts = gTTS(out_text, lang=dst, tld=tld, slow=slow_voice)
            # nombre seguro
            safe_name = (st.session_state.transcript[:20] or "audio").replace("/", "_").replace("\\", "_")
            audio_path = f"temp/{safe_name}.mp3"
            tts.save(audio_path)
            st.session_state.audio_path = audio_path

            st.success("✅ Conversión completada")
            # Mostrar audio
            with open(audio_path, "rb") as f:
                audio_bytes = f.read()
            st.audio(audio_bytes, format="audio/mp3")
            st.download_button("📥 Descargar audio", data=audio_bytes, file_name=os.path.basename(audio_path), mime="audio/mpeg")

            if show_text:
                st.markdown("**Texto traducido:**")
                st.code(out_text)

        except Exception as e:
            st.error(f"❌ Error durante la traducción o TTS: {e}")

# =============================
# Limpieza de temporales
# =============================
cleanup_old_mp3(days=7)

# =============================
# Info final
# =============================
with st.expander("ℹ️ Notas"):
    st.markdown("""
- **Web Speech API** depende del navegador (Chrome/Edge recomendado).  
- **googletrans** puede fallar esporádicamente por cambios del endpoint; vuelve a intentar si ocurre.  
- **gTTS** usa servicios de Google para la síntesis; selecciona un **tld** (acento) que te guste.  
- Los MP3 generados se guardan en `/temp` y se eliminan automáticamente tras 7 días.
""")
