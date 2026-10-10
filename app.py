import time
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import streamlit as st
from supabase import create_client, Client

# ==========================================
# CONFIGURACIÓN INICIAL
# ==========================================
st.set_page_config(page_title="Creator CRM | Studio Team", layout="wide", page_icon="🎬")


@st.cache_resource
def init_connection() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)


supabase = init_connection()

# ==========================================
# CONSTANTES
# ==========================================
EQUIPO = ["Cata", "Paco", "Jero", "Mati", "Kenia"]
SIN_USUARIO = "— elegí quién sos —"
MONEDA = "ARS"  # cambialo a "USD" si vendés en dólares
LIMITE_PUBLICADOS = 10  # cuántos publicados se ven en el tablero

ESTADOS = ["Ideación", "Borradores", "Guionización", "Cola de Render", "Revisión (QA)",
           "⚠️ Ajustes", "Programadas", "✅ Publicado"]
ESTADO_IDEACION = "Ideación"
ESTADO_AJUSTES = "⚠️ Ajustes"
ESTADO_PROGRAMADA = "Programadas"
ESTADO_PUBLICADO = "✅ Publicado"

FORMATOS = ["YouTube Shorts", "Reel / TikTok", "Video Largo (16:9)", "Carrusel"]
ETAPAS_EMBUDO = ["🎯 Atracción (Top)", "🧠 Nutrición (Middle)", "💰 Conversión/Venta (Bottom)"]
PRIORIDADES = ["Alta", "Media", "Baja"]
ICONO_PRIORIDAD = {"Alta": "🔥", "Media": "🟡", "Baja": "🟢"}
ESTADOS_CURSO = ["Borrador", "En Edición", "✅ Publicado y Disponible"]
ESTADO_CURSO_VENTA = "✅ Publicado y Disponible"

ETAPAS_LEAD = ["Nuevo", "Contactado", "Interesado", "Negociación", "✅ Venta cerrada", "❌ Perdido"]
ETAPAS_ABIERTAS = ETAPAS_LEAD[:4]
ETAPA_VENTA = "✅ Venta cerrada"
ETAPA_PERDIDO = "❌ Perdido"
ORIGENES = ["YouTube", "TikTok", "Instagram", "WhatsApp", "Referido", "Web", "Otro"]

ETIQUETAS = {
    "estado": "Estado", "etapa": "Etapa", "responsable": "Responsable", "prioridad": "Prioridad",
    "etapa_embudo": "Embudo", "fecha_limite": "Fecha límite", "fecha_programada": "Publicación",
    "vistos_por": "Revisado por", "vistas": "Vistas", "clics_cta": "Clics CTA",
    "proximo_seguimiento": "Próximo seguimiento", "valor": "Monto", "curso_id": "Curso",
    "progreso": "Avance", "precio": "Precio", "fecha_lanzamiento": "Lanzamiento",
    "leido_por": "Leído por", "contacto": "Contacto", "subtitulos": "Gancho", "cta": "CTA",
    "guion": "Link guion", "link_final": "Link video final",
    "comentarios_ajustes": "Comentario de ajustes", "notas": "Notas", "link_venta": "Link de venta",
}
CAMPOS_LARGOS = {"subtitulos", "cta", "guion", "link_final", "comentarios_ajustes", "notas", "link_venta"}
CAMPOS_NUM = {"vistas", "clics_cta", "valor", "progreso", "precio"}

# Se completa después de cargar los cursos (sirve para mostrar nombres en el historial)
NOMBRES_CURSO = {}

# ==========================================
# ESTILOS (modo oscuro, tarjetas limpias)
# ==========================================
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

# ==========================================
# UTILIDADES
# ==========================================
try:
    ZONA = ZoneInfo("America/Argentina/Cordoba")
except Exception:
    ZONA = None


def hoy() -> date:
    return datetime.now(ZONA).date() if ZONA else date.today()


def a_fecha(valor):
    if not valor:
        return None
    try:
        return date.fromisoformat(str(valor)[:10])
    except ValueError:
        return None


def fmt_ts(ts) -> str:
    try:
        dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        return dt.astimezone(ZONA).strftime("%d/%m %H:%M") if ZONA else dt.strftime("%d/%m %H:%M")
    except Exception:
        return str(ts)[:16].replace("T", " ")


def pesos(n) -> str:
    return f"{float(n or 0):,.0f}".replace(",", ".") + f" {MONEDA}"


def idx(opciones, valor) -> int:
    return opciones.index(valor) if valor in opciones else 0


def norm(x):
    return "" if x is None else x


def actual(reg, campo):
    v = reg.get(campo)
    if campo in CAMPOS_NUM:
        return float(v or 0)
    return norm(v)


def lista_csv(texto):
    return [m.strip() for m in (texto or "").split(",") if m.strip()]


def quien():
    u = st.session_state.get("usuario")
    return u if u in EQUIPO else None


def exigir_usuario() -> bool:
    if quien():
        return True
    st.error("👤 Elegí quién sos (arriba a la derecha) antes de guardar cambios.")
    return False


def recargar(mensaje, icono="✅"):
    st.toast(mensaje, icon=icono)
    time.sleep(0.6)
    st.rerun()


# ==========================================
# ACCESO A DATOS (los errores se muestran, no se esconden)
# ==========================================
def cargar(tabla, desc=False, limite=None):
    try:
        q = supabase.table(tabla).select("*").order("id", desc=desc)
        if limite:
            q = q.limit(limite)
        return q.execute().data or []
    except Exception as e:
        st.error(f"⚠️ No pude leer la tabla **{tabla}**: {e}\n\n"
                 "Si es la primera vez con esta versión, ¿ya corriste el SQL de cambios en Supabase?")
        return None


def insertar(tabla, datos):
    try:
        r = supabase.table(tabla).insert(datos).execute()
        return r.data[0] if r.data else {"id": None}
    except Exception as e:
        st.error(f"No se pudo crear en '{tabla}': {e}")
        return None


def actualizar(tabla, reg_id, datos) -> bool:
    try:
        supabase.table(tabla).update(datos).eq("id", reg_id).execute()
        return True
    except Exception as e:
        st.error(f"No se pudo guardar en '{tabla}': {e}")
        return False


def registrar(entidad, entidad_id, titulo, accion, detalle=""):
    """Anota quién hizo qué. Si falla, avisa pero no frena el trabajo."""
    try:
        supabase.table("historial").insert({
            "entidad": entidad,
            "entidad_id": entidad_id,
            "titulo": titulo,
            "accion": accion,
            "detalle": (detalle or "")[:500],
            "usuario": quien() or "—",
        }).execute()
    except Exception as e:
        st.toast(f"No se pudo registrar en el historial: {e}", icon="⚠️")


def describir(reg, cambios) -> str:
    partes = []
    for campo, nuevo in cambios.items():
        nombre = ETIQUETAS.get(campo, campo)
        if campo in CAMPOS_LARGOS:
            partes.append(f"{nombre} editado")
            continue
        viejo = actual(reg, campo)
        if campo == "curso_id":
            viejo = NOMBRES_CURSO.get(viejo, viejo)
            nuevo = NOMBRES_CURSO.get(nuevo, nuevo)
        partes.append(f"{nombre}: {viejo if viejo != '' else '—'} → {nuevo if norm(nuevo) != '' else '—'}")
    return " | ".join(partes)


def guardar_cambios(tabla, entidad, reg, nuevos, titulo):
    cambios = {k: v for k, v in nuevos.items() if actual(reg, k) != norm(v)}
    if not cambios:
        st.toast("No había cambios para guardar", icon="ℹ️")
        return
    if actualizar(tabla, reg["id"], cambios):
        campo_estado = "estado" if "estado" in cambios else ("etapa" if "etapa" in cambios else None)
        accion = f"movió a {cambios[campo_estado]}" if campo_estado else "editó"
        registrar(entidad, reg["id"], titulo, accion, describir(reg, cambios))
        recargar("Guardado", "💾")


def bloque_borrado(clave, tabla, entidad, reg_id, titulo, desvincular=None):
    """Pide confirmación antes de borrar. desvincular=(tabla, columna) limpia referencias."""
    if not st.session_state.get(f"confirmar_{clave}"):
        return
    st.warning(f"¿Seguro que querés eliminar **{titulo}**? No se puede deshacer.")
    c1, c2 = st.columns(2)
    if c1.button("Sí, eliminar", key=f"si_{clave}", type="primary"):
        if exigir_usuario():
            if desvincular:
                try:
                    supabase.table(desvincular[0]).update({desvincular[1]: None}).eq(desvincular[1], reg_id).execute()
                except Exception as e:
                    st.error(f"No se pudieron desvincular los leads: {e}")
            try:
                supabase.table(tabla).delete().eq("id", reg_id).execute()
            except Exception as e:
                st.error(f"No se pudo eliminar: {e}")
                return
            registrar(entidad, reg_id, titulo, "eliminó")
            st.session_state[f"confirmar_{clave}"] = False
            recargar("Eliminado", "🗑️")
    if c2.button("Cancelar", key=f"no_{clave}"):
        st.session_state[f"confirmar_{clave}"] = False
        st.rerun()


# ==========================================
# CARGA DE DATOS
# ==========================================
videos_db = cargar("videos")
cursos_db = cargar("cursos")
leads_db = cargar("leads")
historial_db = cargar("historial", desc=True, limite=300)

if any(d is None for d in (videos_db, cursos_db, leads_db, historial_db)):
    st.stop()

NOMBRES_CURSO.update({c["id"]: c.get("titulo") or "Sin título" for c in cursos_db})

OPC_VIDEO = {"— Sin video / otro —": None}
for _v in videos_db:
    OPC_VIDEO[f"{_v.get('titulo') or 'Sin título'} (#{_v['id']})"] = _v["id"]
OPC_CURSO = {"— Sin curso definido —": None}
for _c in cursos_db:
    OPC_CURSO[f"{_c.get('titulo') or 'Sin título'} (#{_c['id']})"] = _c["id"]
PRECIOS_CURSO = {c["id"]: float(c.get("precio") or 0) for c in cursos_db}


def etiqueta_de(opciones, valor_id):
    return next((k for k, v in opciones.items() if v == valor_id), next(iter(opciones)))


leads_por_video, leads_por_curso = {}, {}
for _l in leads_db:
    leads_por_video.setdefault(_l.get("video_id"), []).append(_l)
    leads_por_curso.setdefault(_l.get("curso_id"), []).append(_l)

historial_por_item = {}
for _h in historial_db:  # ya viene del más nuevo al más viejo
    historial_por_item.setdefault((_h.get("entidad"), _h.get("entidad_id")), []).append(_h)


def es_venta(lead) -> bool:
    return lead.get("etapa") == ETAPA_VENTA


def monto(lead) -> float:
    return float(lead.get("valor") or 0)


def stats_leads(lista):
    ventas = [l for l in lista if es_venta(l)]
    return {"leads": len(lista), "ventas": len(ventas), "ingresos": sum(monto(l) for l in ventas)}


def fecha_vencimiento(v):
    """Fecha en la que el contenido debería estar listo. None si no aplica."""
    estado = v.get("estado")
    if estado in (ESTADO_PUBLICADO, ESTADO_IDEACION):
        return None
    prog = a_fecha(v.get("fecha_programada"))
    if estado == ESTADO_PROGRAMADA:
        return prog
    fechas = [f for f in (a_fecha(v.get("fecha_limite")), prog) if f]
    return min(fechas) if fechas else None


def esta_atrasado(v) -> bool:
    venc = fecha_vencimiento(v)
    return bool(venc and venc < hoy())


# ==========================================
# ENCABEZADO
# ==========================================
col_titulo, col_usuario = st.columns([3, 1])
with col_titulo:
    st.title("🎬 Studio CRM & Academy - Catalina & Equipo")
    st.markdown("Contenido, embudos, leads y ventas del equipo en un solo lugar.")
with col_usuario:
    st.selectbox("👤 Estoy trabajando como", [SIN_USUARIO] + EQUIPO, key="usuario")
if not quien():
    st.info("Elegí quién sos arriba a la derecha: así queda registrado quién hizo cada cambio.")

tab_kanban, tab_leads, tab_cursos, tab_result, tab_hist = st.tabs([
    "🚀 Flujo de Contenido", "👥 Leads y Ventas", "📚 Cursos", "📊 Resultados", "📜 Historial"
])


# ==========================================
# PESTAÑA 1: FLUJO DE CONTENIDO
# ==========================================
def tarjeta_video(v, estado):
    vid = v["id"]
    titulo = v.get("titulo") or "Sin título"
    prioridad = v.get("prioridad") or "Media"
    clave = f"video_{vid}"
    venc = fecha_vencimiento(v)
    atrasado = bool(venc and venc < hoy())
    etiqueta = f"{'🔴 ' if atrasado else ''}{ICONO_PRIORIDAD.get(prioridad, '')} {titulo}"

    with st.expander(etiqueta, expanded=bool(st.session_state.get(f"confirmar_{clave}"))):
        st.caption(f"📱 {v.get('formato') or 'General'} · {v.get('etapa_embudo') or ETAPAS_EMBUDO[0]}")
        st.caption(f"👤 {v.get('responsable') or '—'} · 📅 Publica: {v.get('fecha_programada') or '—'} "
                   f"· ⏳ Límite: {v.get('fecha_limite') or '—'}")
        if atrasado:
            st.error(f"Atrasado {(hoy() - venc).days} día(s)")
        if estado == ESTADO_AJUSTES and v.get("comentarios_ajustes"):
            st.warning(f"**A corregir:** {v['comentarios_ajustes']}")
        if v.get("subtitulos"):
            st.markdown(f"*Gancho:* {v['subtitulos']}")
        if v.get("cta"):
            st.markdown(f"*CTA:* {v['cta']}")
        if v.get("link_final"):
            st.markdown(f"[▶️ Ver video final]({v['link_final']})")

        with st.form(f"form_{clave}"):
            nuevo_estado = st.selectbox("Estado", ESTADOS, index=idx(ESTADOS, estado), key=f"estado_{vid}")
            comentario = st.text_area("📝 Qué hay que ajustar (obligatorio al pasar a ⚠️ Ajustes)",
                                      value=v.get("comentarios_ajustes") or "", key=f"coment_{vid}")
            c1, c2 = st.columns(2)
            nuevo_resp = c1.selectbox("Responsable", EQUIPO, index=idx(EQUIPO, v.get("responsable")),
                                      key=f"resp_{vid}")
            nueva_prio = c2.selectbox("Prioridad", PRIORIDADES, index=idx(PRIORIDADES, prioridad),
                                      key=f"prio_{vid}")
            nuevo_embudo = st.selectbox("Objetivo en el embudo", ETAPAS_EMBUDO,
                                        index=idx(ETAPAS_EMBUDO, v.get("etapa_embudo")), key=f"embudo_{vid}")
            nuevo_hook = st.text_area("Gancho / subtítulos", value=v.get("subtitulos") or "", key=f"hook_{vid}")
            nuevo_cta = st.text_input("CTA / link de venta", value=v.get("cta") or "", key=f"cta_{vid}")
            nuevo_guion = st.text_input("Link guion / doc", value=v.get("guion") or "", key=f"guion_{vid}")
            nuevo_final = st.text_input("Link del video final", value=v.get("link_final") or "",
                                        key=f"final_{vid}")
            f1, f2 = st.columns(2)
            nueva_limite = f1.date_input(
                "Fecha límite de producción",
                value=a_fecha(v.get("fecha_limite")) or a_fecha(v.get("fecha_programada")) or hoy(),
                key=f"limite_{vid}")
            nueva_prog = f2.date_input("Fecha de publicación",
                                       value=a_fecha(v.get("fecha_programada")) or hoy(), key=f"prog_{vid}")
            nuevos_vistos = st.multiselect("Revisado por", EQUIPO,
                                           default=[m for m in lista_csv(v.get("vistos_por")) if m in EQUIPO],
                                           key=f"vistos_{vid}")
            st.caption("📈 Resultados (completar cuando se publique)")
            m1, m2 = st.columns(2)
            nuevas_vistas = m1.number_input("Vistas", min_value=0, value=int(v.get("vistas") or 0),
                                            step=100, key=f"vistas_{vid}")
            nuevos_clics = m2.number_input("Clics en el CTA", min_value=0, value=int(v.get("clics_cta") or 0),
                                           step=10, key=f"clics_{vid}")
            b1, b2 = st.columns(2)
            guardar = b1.form_submit_button("💾 Guardar", type="primary")
            eliminar = b2.form_submit_button("🗑️ Eliminar")

        if guardar and exigir_usuario():
            if nuevo_estado == ESTADO_AJUSTES and not comentario.strip():
                st.error("Para pasar a ⚠️ Ajustes escribí qué hay que corregir.")
            else:
                guardar_cambios("videos", "video", v, {
                    "estado": nuevo_estado,
                    "comentarios_ajustes": comentario.strip(),
                    "responsable": nuevo_resp,
                    "prioridad": nueva_prio,
                    "etapa_embudo": nuevo_embudo,
                    "subtitulos": nuevo_hook.strip(),
                    "cta": nuevo_cta.strip(),
                    "guion": nuevo_guion.strip(),
                    "link_final": nuevo_final.strip(),
                    "fecha_limite": str(nueva_limite),
                    "fecha_programada": str(nueva_prog),
                    "vistos_por": ",".join(nuevos_vistos),
                    "vistas": int(nuevas_vistas),
                    "clics_cta": int(nuevos_clics),
                }, titulo)

        if eliminar:
            st.session_state[f"confirmar_{clave}"] = True
        bloque_borrado(clave, "videos", "video", vid, titulo, desvincular=("leads", "video_id"))

        for h in historial_por_item.get(("video", vid), [])[:3]:
            st.caption(f"🕒 {fmt_ts(h.get('created_at'))} · {h.get('usuario')} · {h.get('accion')}")


with tab_kanban:
    f_resp, f_vista = st.columns(2)
    filtro_resp = f_resp.selectbox("Ver tareas de:", ["Todos"] + EQUIPO)
    vista = f_vista.radio("Vista", ["🧱 Tablero", "📋 Lista"], horizontal=True)

    videos_vista = [v for v in videos_db if filtro_resp == "Todos" or v.get("responsable") == filtro_resp]

    # Métricas rápidas
    mm1, mm2, mm3, mm4, mm5 = st.columns(5)
    mm1.metric("En producción", len([v for v in videos_vista
                                     if v.get("estado") not in (ESTADO_PUBLICADO, ESTADO_IDEACION)]))
    mm2.metric("Programadas", len([v for v in videos_vista if v.get("estado") == ESTADO_PROGRAMADA]))
    mm3.metric("Requieren ajustes", len([v for v in videos_vista if v.get("estado") == ESTADO_AJUSTES]))
    atrasados = [v for v in videos_vista if esta_atrasado(v)]
    mm4.metric("Atrasados", len(atrasados))
    mm5.metric("Publicados", len([v for v in videos_vista if v.get("estado") == ESTADO_PUBLICADO]))

    if atrasados:
        lineas = []
        for v in sorted(atrasados, key=lambda x: fecha_vencimiento(x))[:8]:
            dias = (hoy() - fecha_vencimiento(v)).days
            lineas.append(f"• **{v.get('titulo') or 'Sin título'}** — {v.get('responsable') or '—'} "
                          f"— {v.get('estado')} — {dias} día(s) de atraso")
        extra = f"\n\n…y {len(atrasados) - 8} más." if len(atrasados) > 8 else ""
        st.error("🔴 **Contenido atrasado**\n\n" + "\n\n".join(lineas) + extra)
    st.divider()

    # Formulario de nueva idea
    with st.expander("⚡ Nueva idea / publicación", expanded=False):
        with st.form("nuevo_video_form", clear_on_submit=True):
            nuevo_titulo = st.text_input("Título / Tema del Video")
            n1, n2 = st.columns(2)
            nuevo_formato = n1.selectbox("Tipo de publicación", FORMATOS)
            objetivo_embudo = n2.selectbox("Objetivo en el embudo", ETAPAS_EMBUDO)
            nuevo_hook_n = st.text_area("Gancho / subtítulos (hook)")
            cta_texto = st.text_input("Llamado a la acción (CTA) / link")
            n3, n4 = st.columns(2)
            limite_n = n3.date_input("Fecha límite de producción", value=hoy() + timedelta(days=3))
            prog_n = n4.date_input("Fecha de publicación", value=hoy() + timedelta(days=5))
            n5, n6 = st.columns(2)
            resp_n = n5.selectbox("Responsable", EQUIPO, index=idx(EQUIPO, quien()))
            prio_n = n6.selectbox("Prioridad", PRIORIDADES, index=1)
            enviar_idea = st.form_submit_button("Añadir al flujo", type="primary")

        if enviar_idea:
            if not nuevo_titulo.strip():
                st.error("Poné un título.")
            elif exigir_usuario():
                creado = insertar("videos", {
                    "titulo": nuevo_titulo.strip(),
                    "formato": nuevo_formato,
                    "estado": ESTADO_IDEACION,
                    "etapa_embudo": objetivo_embudo,
                    "subtitulos": nuevo_hook_n.strip(),
                    "cta": cta_texto.strip(),
                    "fecha_limite": str(limite_n),
                    "fecha_programada": str(prog_n),
                    "responsable": resp_n,
                    "prioridad": prio_n,
                    "vistos_por": "",
                    "guion": "",
                    "link_final": "",
                    "comentarios_ajustes": "",
                })
                if creado:
                    registrar("video", creado.get("id"), nuevo_titulo.strip(), "creó la idea")
                    recargar(f'"{nuevo_titulo.strip()}" guardado', "✅")


    def videos_de(estado):
        lista = [v for v in videos_vista if v.get("estado") == estado]
        if estado == ESTADO_PUBLICADO:
            lista.sort(key=lambda x: str(x.get("fecha_programada") or ""), reverse=True)
            return lista[:LIMITE_PUBLICADOS], len(lista)
        lista.sort(key=lambda x: (
            PRIORIDADES.index(x.get("prioridad")) if x.get("prioridad") in PRIORIDADES else 1,
            str(x.get("fecha_limite") or x.get("fecha_programada") or "9999")))
        return lista, len(lista)


    if vista == "🧱 Tablero":
        columnas = st.columns(len(ESTADOS))
        for col, estado in zip(columnas, ESTADOS):
            with col:
                mostrar, total = videos_de(estado)
                st.markdown(f"**{estado}** ({total})")
                for v in mostrar:
                    tarjeta_video(v, estado)
                if total > len(mostrar):
                    st.caption(f"+{total - len(mostrar)} publicados más (ver pestaña 📊 Resultados)")
    else:
        for estado in ESTADOS:
            mostrar, total = videos_de(estado)
            if not mostrar:
                continue
            st.subheader(f"{estado} ({total})")
            for v in mostrar:
                tarjeta_video(v, estado)
            if total > len(mostrar):
                st.caption(f"+{total - len(mostrar)} publicados más (ver pestaña 📊 Resultados)")


# ==========================================
# PESTAÑA 2: LEADS Y VENTAS
# ==========================================
def tarjeta_lead(l):
    lid = l["id"]
    nombre = l.get("nombre") or "Sin nombre"
    etapa = l.get("etapa") or ETAPAS_LEAD[0]
    clave = f"lead_{lid}"
    prox = a_fecha(l.get("proximo_seguimiento"))
    vence = etapa in ETAPAS_ABIERTAS and prox is not None and prox <= hoy()
    etiqueta = f"{'📞 ' if vence else ''}{nombre} — {etapa}"

    with st.expander(etiqueta, expanded=bool(st.session_state.get(f"confirmar_{clave}"))):
        video_txt = etiqueta_de(OPC_VIDEO, l.get("video_id"))
        st.caption(f"📲 {l.get('contacto') or 'Sin contacto'} · 📍 {l.get('origen') or '—'} · 🎬 {video_txt}")
        if es_venta(l):
            st.success(f"Venta cerrada: {pesos(monto(l))}")

        with st.form(f"form_{clave}"):
            g1, g2 = st.columns(2)
            nueva_etapa = g1.selectbox("Etapa", ETAPAS_LEAD, index=idx(ETAPAS_LEAD, etapa), key=f"letapa_{lid}")
            nuevo_resp = g2.selectbox("Responsable", EQUIPO, index=idx(EQUIPO, l.get("responsable")),
                                      key=f"lresp_{lid}")
            nueva_prox = st.date_input("Próximo seguimiento", value=prox or hoy() + timedelta(days=2),
                                       key=f"lprox_{lid}")
            curso_label = st.selectbox("Curso de interés", list(OPC_CURSO),
                                       index=idx(list(OPC_CURSO), etiqueta_de(OPC_CURSO, l.get("curso_id"))),
                                       key=f"lcurso_{lid}")
            nuevo_monto = st.number_input(f"Monto de la venta ({MONEDA})", min_value=0.0,
                                          value=float(l.get("valor") or 0), step=1000.0, format="%.0f",
                                          key=f"lmonto_{lid}")
            nuevo_contacto = st.text_input("Contacto", value=l.get("contacto") or "", key=f"lcont_{lid}")
            nuevas_notas = st.text_area("Notas", value=l.get("notas") or "", key=f"lnotas_{lid}")
            b1, b2 = st.columns(2)
            guardar = b1.form_submit_button("💾 Guardar", type="primary")
            eliminar = b2.form_submit_button("🗑️ Eliminar")

        if guardar and exigir_usuario():
            curso_id = OPC_CURSO[curso_label]
            monto_final = float(nuevo_monto)
            error = None
            if nueva_etapa == ETAPA_VENTA and monto_final <= 0:
                if PRECIOS_CURSO.get(curso_id, 0) > 0:
                    monto_final = PRECIOS_CURSO[curso_id]
                else:
                    error = "Para cerrar la venta poné el monto (o elegí un curso que tenga precio)."
            if error:
                st.error(error)
            else:
                guardar_cambios("leads", "lead", l, {
                    "etapa": nueva_etapa,
                    "responsable": nuevo_resp,
                    "proximo_seguimiento": str(nueva_prox),
                    "curso_id": curso_id,
                    "valor": monto_final,
                    "contacto": nuevo_contacto.strip(),
                    "notas": nuevas_notas.strip(),
                }, f"Lead: {nombre}")

        if eliminar:
            st.session_state[f"confirmar_{clave}"] = True
        bloque_borrado(clave, "leads", "lead", lid, f"Lead: {nombre}")

        for h in historial_por_item.get(("lead", lid), [])[:3]:
            st.caption(f"🕒 {fmt_ts(h.get('created_at'))} · {h.get('usuario')} · {h.get('accion')}")


with tab_leads:
    abiertos = [l for l in leads_db if l.get("etapa") in ETAPAS_ABIERTAS]
    ventas_l = [l for l in leads_db if es_venta(l)]
    ingresos_l = sum(monto(l) for l in ventas_l)
    conversion = (len(ventas_l) / len(leads_db) * 100) if leads_db else 0.0

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Leads totales", len(leads_db))
    k2.metric("En seguimiento", len(abiertos))
    k3.metric("Ventas cerradas", len(ventas_l))
    k4.metric("Ingresos", pesos(ingresos_l))
    k5.metric("Conversión", f"{conversion:.1f}%")

    pendientes = [l for l in abiertos
                  if a_fecha(l.get("proximo_seguimiento")) and a_fecha(l.get("proximo_seguimiento")) <= hoy()]
    if pendientes:
        nombres = ", ".join(f"**{l.get('nombre')}** ({l.get('responsable') or '—'})" for l in pendientes[:10])
        st.warning(f"📞 {len(pendientes)} seguimiento(s) para hoy o atrasados: {nombres}")
    st.divider()

    col_l1, col_l2 = st.columns([1, 2])

    with col_l1:
        st.subheader("➕ Nuevo lead")
        with st.form("nuevo_lead_form", clear_on_submit=True):
            lead_nombre = st.text_input("Nombre")
            lead_contacto = st.text_input("Contacto (WhatsApp / mail / @usuario)")
            lead_origen = st.selectbox("Canal de origen", ORIGENES)
            lead_video = st.selectbox("Video que lo trajo", list(OPC_VIDEO))
            lead_curso = st.selectbox("Curso de interés", list(OPC_CURSO))
            lead_resp = st.selectbox("Responsable", EQUIPO, index=idx(EQUIPO, quien()))
            lead_prox = st.date_input("Próximo seguimiento", value=hoy() + timedelta(days=2))
            lead_notas = st.text_area("Notas")
            enviar_lead = st.form_submit_button("Agregar lead", type="primary")

        if enviar_lead:
            if not lead_nombre.strip():
                st.error("Poné un nombre.")
            elif exigir_usuario():
                creado = insertar("leads", {
                    "nombre": lead_nombre.strip(),
                    "contacto": lead_contacto.strip(),
                    "origen": lead_origen,
                    "video_id": OPC_VIDEO[lead_video],
                    "curso_id": OPC_CURSO[lead_curso],
                    "etapa": ETAPAS_LEAD[0],
                    "valor": 0,
                    "proximo_seguimiento": str(lead_prox),
                    "notas": lead_notas.strip(),
                    "responsable": lead_resp,
                })
                if creado:
                    registrar("lead", creado.get("id"), f"Lead: {lead_nombre.strip()}", "creó el lead")
                    recargar("Lead agregado", "👥")

    with col_l2:
        st.subheader("📋 Pipeline de leads")
        fl1, fl2 = st.columns(2)
        etapas_sel = fl1.multiselect("Etapas", ETAPAS_LEAD, default=ETAPAS_ABIERTAS)
        resp_sel = fl2.selectbox("Responsable", ["Todos"] + EQUIPO, key="filtro_lead_resp")

        visibles = [l for l in leads_db
                    if (l.get("etapa") or ETAPAS_LEAD[0]) in etapas_sel
                    and (resp_sel == "Todos" or l.get("responsable") == resp_sel)]
        visibles.sort(key=lambda l: (l.get("etapa") in (ETAPA_VENTA, ETAPA_PERDIDO),
                                     a_fecha(l.get("proximo_seguimiento")) or date.max))
        if not leads_db:
            st.info("Todavía no hay leads. Cargá el primero desde el panel izquierdo.")
        elif not visibles:
            st.info("No hay leads con esos filtros.")
        for l in visibles:
            tarjeta_lead(l)


# ==========================================
# PESTAÑA 3: CURSOS
# ==========================================
def tarjeta_curso(c):
    cid = c["id"]
    titulo = c.get("titulo") or "Sin título"
    estado = c.get("estado") or ESTADOS_CURSO[0]
    clave = f"curso_{cid}"
    ls = leads_por_curso.get(cid, [])
    s = stats_leads(ls)
    interesados = len([l for l in ls if l.get("etapa") in ETAPAS_ABIERTAS])

    with st.expander(f"📖 {titulo}", expanded=bool(st.session_state.get(f"confirmar_{clave}"))
                     or len(cursos_db) <= 3):
        a1, a2, a3 = st.columns(3)
        a1.metric("Alumnos", s["ventas"])
        a2.metric("Ingresos", pesos(s["ingresos"]))
        a3.metric("Leads abiertos", interesados)

        with st.form(f"form_{clave}"):
            nuevo_estado = st.selectbox("Estado de lanzamiento", ESTADOS_CURSO,
                                        index=idx(ESTADOS_CURSO, estado), key=f"cestado_{cid}")
            nuevo_progreso = st.slider("Avance general (%)", 0, 100,
                                       min(100, max(0, int(c.get("progreso") or 0))), key=f"cprog_{cid}")
            p1, p2 = st.columns(2)
            nuevo_precio = p1.number_input(f"Precio ({MONEDA})", min_value=0.0,
                                           value=float(c.get("precio") or 0), step=1000.0, format="%.0f",
                                           key=f"cprecio_{cid}")
            nuevo_lanz = p2.date_input("Fecha de lanzamiento",
                                       value=a_fecha(c.get("fecha_lanzamiento")) or hoy(),
                                       key=f"clanz_{cid}")
            nuevo_link = st.text_input("Link de venta / checkout", value=c.get("link_venta") or "",
                                       key=f"clink_{cid}")
            equipo_leido = st.multiselect("Leído / estudiado por", EQUIPO,
                                          default=[m for m in lista_csv(c.get("leido_por")) if m in EQUIPO],
                                          key=f"cleido_{cid}")
            b1, b2 = st.columns(2)
            guardar = b1.form_submit_button("💾 Guardar", type="primary")
            eliminar = b2.form_submit_button("🗑️ Borrar curso")

        if guardar and exigir_usuario():
            guardar_cambios("cursos", "curso", c, {
                "estado": nuevo_estado,
                "progreso": int(nuevo_progreso),
                "precio": float(nuevo_precio),
                "fecha_lanzamiento": str(nuevo_lanz),
                "link_venta": nuevo_link.strip(),
                "leido_por": ",".join(equipo_leido),
            }, titulo)

        if eliminar:
            st.session_state[f"confirmar_{clave}"] = True
        bloque_borrado(clave, "cursos", "curso", cid, titulo, desvincular=("leads", "curso_id"))

        for h in historial_por_item.get(("curso", cid), [])[:3]:
            st.caption(f"🕒 {fmt_ts(h.get('created_at'))} · {h.get('usuario')} · {h.get('accion')}")


with tab_cursos:
    st.header("📚 Cursos & Productos Digitales")
    en_venta = [c for c in cursos_db if c.get("estado") == ESTADO_CURSO_VENTA]
    alumnos_tot = sum(stats_leads(leads_por_curso.get(c["id"], []))["ventas"] for c in cursos_db)
    ingresos_tot = sum(stats_leads(leads_por_curso.get(c["id"], []))["ingresos"] for c in cursos_db)
    z1, z2, z3, z4 = st.columns(4)
    z1.metric("Cursos", len(cursos_db))
    z2.metric("En venta", len(en_venta))
    z3.metric("Alumnos totales", alumnos_tot)
    z4.metric("Ingresos por cursos", pesos(ingresos_tot))
    st.divider()

    col_c1, col_c2 = st.columns([1, 2])

    with col_c1:
        st.subheader("➕ Crear nuevo curso")
        with st.form("nuevo_curso_form", clear_on_submit=True):
            curso_titulo = st.text_input("Título del curso / módulo")
            curso_estado_init = st.selectbox("Estado del curso", ESTADOS_CURSO)
            curso_precio = st.number_input(f"Precio ({MONEDA})", min_value=0.0, value=0.0, step=1000.0,
                                           format="%.0f")
            curso_lanz = st.date_input("Fecha de lanzamiento", value=hoy() + timedelta(days=30))
            btn_curso = st.form_submit_button("Crear curso", type="primary")

        if btn_curso:
            if not curso_titulo.strip():
                st.error("Poné un título.")
            elif exigir_usuario():
                creado = insertar("cursos", {
                    "titulo": curso_titulo.strip(),
                    "estado": curso_estado_init,
                    "progreso": 0,
                    "leido_por": "",
                    "precio": float(curso_precio),
                    "fecha_lanzamiento": str(curso_lanz),
                    "link_venta": "",
                })
                if creado:
                    registrar("curso", creado.get("id"), curso_titulo.strip(), "creó el curso")
                    recargar("Curso creado", "🎓")

    with col_c2:
        st.subheader("📋 Pipeline y ventas por curso")
        if not cursos_db:
            st.info("Todavía no hay cursos creados. Agregá el primero desde el panel izquierdo.")
        for c in cursos_db:
            tarjeta_curso(c)


# ==========================================
# PESTAÑA 4: RESULTADOS
# ==========================================
def resumen_por(videos, campo, valores):
    filas = []
    for valor in valores:
        grupo = [v for v in videos if (v.get(campo) or "") == valor]
        if not grupo:
            continue
        ls = [l for v in grupo for l in leads_por_video.get(v["id"], [])]
        s = stats_leads(ls)
        filas.append({
            "Grupo": valor,
            "Videos": len(grupo),
            "Vistas": sum(int(v.get("vistas") or 0) for v in grupo),
            "Leads": s["leads"],
            "Ventas": s["ventas"],
            "Ingresos": round(s["ingresos"]),
        })
    return filas


with tab_result:
    st.header("📊 Qué contenido trae plata")
    incluir_no_pub = st.checkbox("Incluir videos que todavía no se publicaron", value=False)
    base = [v for v in videos_db if incluir_no_pub or v.get("estado") == ESTADO_PUBLICADO]

    if not base:
        st.info("Todavía no hay videos publicados. Cuando publiques, cargá vistas y clics en cada tarjeta.")
    else:
        filas = []
        for v in base:
            s = stats_leads(leads_por_video.get(v["id"], []))
            vistas = int(v.get("vistas") or 0)
            clics = int(v.get("clics_cta") or 0)
            filas.append({
                "Video": v.get("titulo") or "Sin título",
                "Formato": v.get("formato") or "—",
                "Embudo": v.get("etapa_embudo") or "—",
                "Vistas": vistas,
                "Clics CTA": clics,
                "CTR %": round(clics / vistas * 100, 1) if vistas else 0.0,
                "Leads": s["leads"],
                "Ventas": s["ventas"],
                "Ingresos": round(s["ingresos"]),
            })
        filas.sort(key=lambda f: (f["Ingresos"], f["Ventas"], f["Leads"]), reverse=True)

        r1, r2, r3, r4, r5 = st.columns(5)
        r1.metric("Vistas", f"{sum(f['Vistas'] for f in filas):,}".replace(",", "."))
        r2.metric("Clics CTA", f"{sum(f['Clics CTA'] for f in filas):,}".replace(",", "."))
        r3.metric("Leads", sum(f["Leads"] for f in filas))
        r4.metric("Ventas", sum(f["Ventas"] for f in filas))
        r5.metric("Ingresos", pesos(sum(f["Ingresos"] for f in filas)))

        st.subheader("Ranking de videos")
        st.dataframe(filas, hide_index=True)

        st.subheader("Por etapa del embudo")
        st.dataframe(resumen_por(base, "etapa_embudo", ETAPAS_EMBUDO), hide_index=True)

        st.subheader("Por formato")
        st.dataframe(resumen_por(base, "formato", FORMATOS), hide_index=True)

    st.subheader("Por canal de origen del lead")
    canales = sorted({l.get("origen") or "Otro" for l in leads_db})
    if not canales:
        st.info("Todavía no hay leads cargados.")
    else:
        filas_canal = []
        for canal in canales:
            ls = [l for l in leads_db if (l.get("origen") or "Otro") == canal]
            s = stats_leads(ls)
            filas_canal.append({
                "Canal": canal,
                "Leads": s["leads"],
                "Ventas": s["ventas"],
                "Conversión %": round(s["ventas"] / s["leads"] * 100, 1) if s["leads"] else 0.0,
                "Ingresos": round(s["ingresos"]),
            })
        filas_canal.sort(key=lambda f: f["Ingresos"], reverse=True)
        st.dataframe(filas_canal, hide_index=True)


# ==========================================
# PESTAÑA 5: HISTORIAL
# ==========================================
with tab_hist:
    st.header("📜 Quién hizo qué")
    h1, h2 = st.columns(2)
    persona = h1.selectbox("Persona", ["Todos"] + EQUIPO, key="hist_persona")
    tipo = h2.selectbox("Tipo", ["Todos", "video", "lead", "curso"], key="hist_tipo")
    filas_h = [{
        "Cuándo": fmt_ts(h.get("created_at")),
        "Quién": h.get("usuario") or "—",
        "Tipo": h.get("entidad") or "—",
        "Elemento": h.get("titulo") or "—",
        "Acción": h.get("accion") or "—",
        "Detalle": h.get("detalle") or "",
    } for h in historial_db
        if (persona == "Todos" or h.get("usuario") == persona)
        and (tipo == "Todos" or h.get("entidad") == tipo)]
    if filas_h:
        st.dataframe(filas_h, hide_index=True)
        st.caption("Se muestran los últimos 300 movimientos.")
    else:
        st.info("Todavía no hay movimientos registrados.")
