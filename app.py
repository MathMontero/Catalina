import streamlit as st
import time
from datetime import date
from supabase import create_client, Client

# Configuración inicial
st.set_page_config(page_title="Creator CRM | Studio Team", layout="wide", page_icon="🎬")

# Conexión a Supabase usando los secretos de Streamlit
@st.cache_resource
def init_connection() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

# Miembros del equipo
EQUIPO = ["Cata", "Paco", "Jero", "Mati", "Kenia"]

# Funciones de carga de datos
def cargar_videos():
    try:
        response = supabase.table("videos").select("*").order("id").execute()
        return response.data
    except Exception as e:
        return []

def cargar_cursos():
    try:
        response = supabase.table("cursos").select("*").order("id").execute()
        return response.data
    except Exception as e:
        return []

# Estilos visuales en Modo Oscuro con tarjetas limpias
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    div[data-testid="stExpander"] {
        border: 1px solid #262730;
        border-left: 4px solid #6366f1;
        border-radius: 8px;
        background-color: #161b22;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.2);
    }
    </style>
""", unsafe_allow_html=True)

st.title("🎬 Studio CRM & Academy - Catalina & Equipo")
st.markdown("Gestión integral de contenidos y desarrollo de cursos internos en tiempo real.")

# Pestañas principales de navegación
tab_kanban, tab_cursos = st.tabs(["🚀 Flujo de Contenido (Kanban)", "📚 Cursos & Capacitaciones"])

videos_db = cargar_videos()
cursos_db = cargar_cursos()

estados = ["Ideación", "Borradores", "Guionización", "Cola de Render", "Revisión (QA)", "⚠️ Ajustes", "Programadas", "✅ Publicado"]
formatos = ["YouTube Shorts", "Reel / TikTok", "Video Largo (16:9)", "Carrusel"]

# ==========================================
# PESTAÑA 1: KANBAN DE CONTENIDO
# ==========================================
with tab_kanban:
    # Métricas rápidas
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    col_m1.metric("En Producción", len([v for v in videos_db if v.get("estado") not in ["✅ Publicado", "Ideación"]]))
    col_m2.metric("Programadas", len([v for v in videos_db if v.get("estado") == "Programadas"]))
    col_m3.metric("Requieren Ajustes", len([v for v in videos_db if v.get("estado") == "⚠️ Ajustes"]))
    col_m4.metric("Publicados", len([v for v in videos_db if v.get("estado") == "✅ Publicado"]))
    st.divider()

    # Sidebar para añadir nuevo contenido adaptado al prompt
    with st.sidebar:
        st.header("⚡ Nueva Idea / Publicación")
        with st.form("nuevo_video_form", clear_on_submit=True):
            nuevo_titulo = st.text_input("Título / Idea Principal")
            nuevo_formato = st.selectbox("Tipo de Publicación", formatos)
            nuevo_subtitulo = st.text_area("Subtítulos / Ganchos")
            nueva_fecha = st.date_input("Fecha Programada", value=date.today())
            responsable_asignado = st.selectbox("Asignar Responsable", EQUIPO)
            
            submit_btn = st.form_submit_button("Añadir al flujo", type="primary")
            
            if submit_btn and nuevo_titulo:
                try:
                    supabase.table("videos").insert({
                        "titulo": nuevo_titulo,
                        "formato": nuevo_formato,
                        "estado": "Ideación",
                        "subtitulos": nuevo_subtitulo,
                        "fecha_programada": str(nueva_fecha),
                        "responsable": responsable_asignado,
                        "vistos_por": ""
                    }).execute()
                    st.toast(f'¡"{nuevo_titulo}" guardado con éxito!', icon="✅")
                    time.sleep(0.5)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al guardar: {e}")

    # Layout Kanban en columnas dinámicas
    columnas = st.columns(len(estados))

    for idx, estado in enumerate(estados):
        with columnas[idx]:
            st.markdown(f"**{estado}**")
            
            videos_columna = [v for v in videos_db if v.get("estado") == estado]
            
            for video in videos_columna:
                video_id = video.get("id")
                video_titulo = video.get("titulo", "Sin título")
                video_formato = video.get("formato", "General")
                video_guion = video.get("guion") or ""
                video_hashtags = video.get("hashtags") or ""
                video_subt = video.get("subtitulos") or ""
                video_fecha = video.get("fecha_programada") or ""
                responsable_actual = video.get("responsable") or "Cata"
                vistos_actuales = video.get("vistos_por") or ""
                
                with st.expander(f"📌 {video_titulo}", expanded=False):
                    st.caption(f"📱 {video_formato} | 📅 {video_fecha}")
                    if video_subt:
                        st.markdown(f"*Subtítulo:* {video_subt}")
                    
                    # Responsable y control de equipo
                    resp_idx = EQUIPO.index(responsable_actual) if responsable_actual in EQUIPO else 0
                    nuevo_resp = st.selectbox("Responsable", EQUIPO, index=resp_idx, key=f"resp_{video_id}")
                    
                    # Control de quiénes vieron / revisaron la tarea
                    vistos_lista = [m.strip() for m in vistos_actuales.split(",") if m.strip()]
                    nuevos_vistos = st.multiselect("Visto / Revisado por:", EQUIPO, default=[m for m in vistos_lista if m in EQUIPO], key=f"vistos_{video_id}")
                    
                    # Campos editables
                    nuevo_guion = st.text_input("Link Guion / Doc", value=video_guion, key=f"guion_{video_id}")
                    
                    # Simulación IA para Hashtags
                    if st.button("✨ Generar Hashtags IA", key=f"ai_{video_id}", use_container_width=True):
                        with st.spinner('Analizando...'):
                            time.sleep(1)
                            hashtags_nuevos = "#CreatorCRM #InstagramGrowth #Viral"
                            supabase.table("videos").update({"hashtags": hashtags_nuevos}).eq("id", video_id).execute()
                            st.success("¡Actualizado!")
                            st.rerun()
                    
                    if video_hashtags:
                        st.info(video_hashtags)
                    
                    # Selector de estado
                    nuevo_estado = st.selectbox(
                        "Estado:", 
                        estados, 
                        index=estados.index(estado) if estado in estados else 0, 
                        key=f"estado_{video_id}"
                    )
                    
                    # Botón eliminar
                    if st.button("🗑️ Eliminar", key=f"del_{video_id}", use_container_width=True):
                        try:
                            supabase.table("videos").delete().eq("id", video_id).execute()
                            st.toast("Eliminado", icon="⚠️")
                            time.sleep(0.5)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
                    
                    # Guardar cambios si hubo modificaciones en tiempo real
                    vistos_str = ",".join(nuevos_vistos)
                    if (nuevo_estado != estado or 
                        nuevo_guion != video_guion or 
                        nuevo_resp != responsable_actual or 
                        vistos_str != vistos_actuales):
                        
                        supabase.table("videos").update({
                            "estado": nuevo_estado,
                            "guion": nuevo_guion,
                            "responsable": nuevo_resp,
                            "vistos_por": vistos_str
                        }).eq("id", video_id).execute()
                        st.rerun()

# ==========================================
# PESTAÑA 2: CURSOS Y CAPACITACIONES
# ==========================================
with tab_cursos:
    st.header("📚 Academia Interna - Cursos del Equipo")
    st.markdown("Control de creación, lectura y progreso de los cursos formativos entre Catalina y el equipo.")
    
    col_c1, col_c2 = st.columns([1, 2])
    
    with col_c1:
        st.subheader("➕ Crear Nuevo Curso")
        with st.form("nuevo_curso_form", clear_on_submit=True):
            curso_titulo = st.text_input("Título del Curso / Módulo")
            curso_estado = st.selectbox("Estado del Curso", ["Borrador", "En Edición", "Publicado y Disponible"])
            btn_curso = st.form_submit_button("Crear Curso", type="primary")
            
            if btn_curso and curso_titulo:
                try:
                    supabase.table("cursos").insert({
                        "titulo": curso_titulo,
                        "estado": curso_estado,
                        "progreso": 0,
                        "leido_por": ""
                    }).execute()
                    st.toast("¡Curso creado con éxito!", icon="🎓")
                    time.sleep(0.5)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
                    
    with col_c2:
        st.subheader("📋 Progreso de Cursos Activos")
        if not cursos_db:
            st.info("A todavía no hay cursos creados. ¡Agregá el primero desde el panel izquierdo!")
        else:
            for curso in cursos_db:
                c_id = curso.get("id")
                c_titulo = curso.get("titulo")
                c_estado = curso.get("estado")
                c_progreso = curso.get("progreso", 0)
                c_leido = curso.get("leido_por") or ""
                
                with st.expander(f"📖 {c_titulo} ({c_estado})", expanded=True):
                    # Barra de progreso interactiva
                    nuevo_progreso = st.slider("Porcentaje de Avance General", 0, 100, c_progreso, key=f"prog_{c_id}")
                    
                    # Control de quiénes ya lo leyeron
                    leidos_lista = [m.strip() for m in c_leido.split(",") if m.strip()]
                    equipo_leido = st.multiselect("Leído / Completado por:", EQUIPO, default=[m for m in leidos_lista if m in EQUIPO], key=f"leido_por_{c_id}")
                    
                    # Botón eliminar curso
                    if st.button("🗑️ Borrar Curso", key=f"del_c_{c_id}"):
                        try:
                            supabase.table("cursos").delete().eq("id", c_id).execute()
                            st.toast("Curso eliminado", icon="⚠️")
                            time.sleep(0.5)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
                            
                    # Actualizar cambios del curso
                    leidos_str = ",".join(equipo_leido)
                    if nuevo_progreso != c_progreso or leidos_str != c_leido:
                        supabase.table("cursos").update({
                            "progreso": nuevo_progreso,
                            "leido_por": leidos_str
                        }).eq("id", c_id).execute()
                        st.rerun()
