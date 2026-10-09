import streamlit as st
import time
from supabase import create_client, Client

# Configuración inicial
st.set_page_config(page_title="Creator CRM | Catalina", layout="wide", page_icon="🎬")

# Conexión a Supabase usando los secretos de Streamlit
@st.cache_resource
def init_connection() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

# Función para traer los videos de la base de datos
def cargar_videos():
    response = supabase.table("videos").select("*").order("id").execute()
    return response.data

# Estilos visuales
st.markdown("""
    <style>
    .stSelectbox label { display: none; }
    div[data-testid="stExpander"] {
        border-left: 4px solid #6366f1;
        border-radius: 8px;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
    }
    </style>
""", unsafe_allow_html=True)

st.title("🎬 Studio CRM - Catalina & Equipo")
st.markdown("Panel de control sincronizado en tiempo real.")

# Cargar datos desde Supabase
videos_db = cargar_videos()

estados = ["Ideación", "Guionización", "Cola de Render", "Revisión (QA)", "⚠️ Ajustes", "✅ Publicado"]
formatos = ["YouTube Shorts", "Reel / TikTok", "Video Largo (16:9)", "Carrusel"]

# Métricas rápidas
col_m1, col_m2, col_m3 = st.columns(3)
col_m1.metric("En Producción", len([v for v in videos_db if v["estado"] not in ["✅ Publicado", "Ideación"]]))
col_m2.metric("Requieren Ajustes", len([v for v in videos_db if v["estado"] == "⚠️ Ajustes"]))
col_m3.metric("Publicados", len([v for v in videos_db if v["estado"] == "✅ Publicado"]))
st.divider()

# Sidebar para agregar nuevo contenido
with st.sidebar:
    st.header("⚡ Nuevo Contenido")
    with st.form("nuevo_video_form", clear_on_submit=True):
        nuevo_titulo = st.text_input("Título del Video")
        nuevo_formato = st.selectbox("Formato", formatos)
        submit_btn = st.form_submit_button("Añadir al flujo", type="primary")
        
        if submit_btn and nuevo_titulo:
            # Insertar directamente en Supabase
            supabase.table("videos").insert({
                "titulo": nuevo_titulo,
                "formato": nuevo_formato,
                "estado": "Ideación",
                "guion": "",
                "hashtags": ""
            }).execute()
            st.toast(f'¡"{nuevo_titulo}" guardado en la base de datos!', icon="✅")
            time.sleep(0.5)
            st.rerun()

# Layout Kanban en columnas
columnas = st.columns(len(estados))

for idx, estado in enumerate(estados):
    with columnas[idx]:
        st.markdown(f"**{estado}**")
        
        videos_columna = [v for v in videos_db if v["estado"] == estado]
        
        for video in videos_columna:
            with st.expander(f"📼 {video['titulo']}", expanded=False):
                st.caption(f"📱 {video['formato']}")
                
                # Campos editables en tiempo real
                nuevo_guion = st.text_input("Link al Guion / Docs", value=video["guion"] or "", key=f"guion_{video['id']}")
                
                # Botón de simulación IA
                if st.button("✨ Generar Hashtags con IA", key=f"ai_{video['id']}", use_container_width=True):
                    with st.spinner('Analizando guion...'):
                        time.sleep(1)
                        hashtags_nuevos = "#Tendencia #CreatorCRM #Viral"
                        supabase.table("videos").update({"hashtags": hashtags_nuevos}).eq("id", video["id"]).execute()
                        st.success("¡Hashtags guardados!")
                        st.rerun()
                
                if video["hashtags"]:
                    st.info(video["hashtags"])
                
                # Selector de cambio de estado
                nuevo_estado = st.selectbox(
                    "Cambiar estado:", 
                    estados, 
                    index=estados.index(estado), 
                    key=f"estado_{video['id']}"
                )
                
                # Si cambian el estado o el guion, actualizamos Supabase automáticamente
                if nuevo_estado != estado or nuevo_guion != (video["guion"] or ""):
                    supabase.table("videos").update({
                        "estado": nuevo_estado,
                        "guion": nuevo_guion
                    }).eq("id", video["id"]).execute()
                    st.rerun()
                    