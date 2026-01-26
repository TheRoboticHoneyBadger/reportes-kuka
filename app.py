import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta, time
import gspread
import os

# --- CONFIGURACIÓN E INTERFAZ ---
st.set_page_config(page_title="KUKA Mantenimiento", page_icon="🤖", layout="centered")

# CSS PERSONALIZADO PARA FIJAR EL DISEÑO EN MÓVIL
st.markdown("""
    <style>
    /* Estilo para el contenedor del reloj digital */
    .reloj-container {
        display: flex;
        align-items: center;
        justify-content: flex-start;
        gap: 10px;
        margin-bottom: 20px;
    }
    .reloj-input {
        width: 80px !important;
    }
    .reloj-sep {
        font-size: 28px;
        font-weight: bold;
        padding-top: 5px;
    }
    /* Hacer el botón de guardar más grande para el pulgar */
    .stButton > button {
        width: 100%;
        height: 60px;
        font-size: 20px !important;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXIÓN A DATOS ---
def conectar_google_sheet():
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        gc = gspread.service_account_from_dict(creds_dict)
        return gc.open("Base_Datos_Mantenimiento").sheet1
    except:
        return None

@st.cache_data
def cargar_catalogos():
    try:
        df_cat = pd.read_csv('catalogo_fallas.csv')
        df_cat.columns = df_cat.columns.str.strip().str.upper()
        df_tec = pd.read_csv('tecnicos.csv', dtype={'ID': str})
        df_tec.columns = df_tec.columns.str.strip().str.upper()
        return df_cat, df_tec
    except:
        return pd.DataFrame(), pd.DataFrame()

df_catalogo, df_tecnicos = cargar_catalogos()

# --- LOGO Y TÍTULO ---
col_l, col_t = st.columns([1, 4])
with col_l:
    st.image("logo.png" if os.path.exists("logo.png") else "https://cdn-icons-png.flaticon.com/512/8636/8636080.png", width=70)
with col_t:
    st.subheader("Reporte de fallas de mantenimiento")

# --- FORMULARIO ---
with st.form("form_final"):
    # 1. PERSONAL
    st.info("👤 Personal")
    id_resp = st.text_input("No. Control Responsable", max_chars=5)
    
    nombres_tec = df_tecnicos['NOMBRE'].tolist() if not df_tecnicos.empty else []
    apoyo = st.multiselect("Personal de Apoyo", nombres_tec)
    turno = st.select_slider("Turno", options=["Mañana", "Tarde", "Noche"])

    # 2. UBICACIÓN
    st.info("📍 Ubicación")
    c1, c2 = st.columns(2)
    celda = c1.text_input("Celda")
    robot = c2.text_input("Robot")
    
    # 3. FALLA (FILTRADO INTELIGENTE)
    st.info("📋 Detalle de Falla")
    area_col = next((c for c in df_catalogo.columns if "AREA" in c), "AREA")
    tipo_col = next((c for c in df_catalogo.columns if "TIPO" in c), "TIPO")
    
    areas = df_catalogo[area_col].unique() if not df_catalogo.empty else []
    area_sel = st.selectbox("Área", areas)
    
    filtro_tipo = df_catalogo[df_catalogo[area_col] == area_sel][tipo_col].unique() if not df_catalogo.empty else []
    tipo_sel = st.selectbox("Tipo de Falla", filtro_tipo)

    # Selección de código final
    df_f = df_catalogo[(df_catalogo[area_col] == area_sel) & (df_catalogo[tipo_col] == tipo_sel)]
    cod_col = next((c for c in df_f.columns if "CODIGO" in c), df_f.columns[0] if not df_f.empty else "")
    desc_col = next((c for c in df_f.columns if "SUB" in c or "MODO" in c or "DESC" in c), df_f.columns[-1] if not df_f.empty else "")
    
    opciones = (df_f[cod_col] + " - " + df_f[desc_col]).tolist() if not df_f.empty else ["Sin datos"]
    falla_final = st.selectbox("Código Específico", opciones)

    # 4. TRABAJO
    st.info("🛠️ Ejecución")
    sintoma = st.text_area("Descripción / Síntoma")
    accion = st.text_area("Acción Correctiva")

    # 5. TIEMPOS (RELOJ DIGITAL COMPACTO)
    st.info("⏱️ Tiempos (Formato 24h)")
    ahora = datetime.now()

    # INICIO
    st.write("Hora Inicio:")
    c_h1, c_s1, c_m1, c_sp1 = st.columns([2, 1, 2, 5])
    with c_h1:
        h_i = st.number_input("HI", 0, 23, ahora.hour, key="hi", label_visibility="collapsed")
    with c_s1:
        st.markdown('<p class="reloj-sep">:</p>', unsafe_allow_html=True)
    with c_m1:
        m_i = st.number_input("MI", 0, 59, ahora.minute, key="mi", label_visibility="collapsed")

    # FIN
    st.write("Hora Fin:")
    c_h2, c_s2, c_m2, c_sp2 = st.columns([2, 1, 2, 5])
    with c_h2:
        h_f = st.number_input("HF", 0, 23, ahora.hour, key="hf", label_visibility="collapsed")
    with c_s2:
        st.markdown('<p class="reloj-sep">:</p>', unsafe_allow_html=True)
    with c_m2:
        m_f = st.number_input("MF", 0, 59, ahora.minute, key="mf", label_visibility="collapsed")

    # BOTÓN
    guardar = st.form_submit_button("GUARDAR REPORTE")

# --- LÓGICA DE GUARDADO ---
if guardar:
    if not id_resp or not celda or not robot:
        st.error("⚠️ Llena ID, Celda y Robot.")
    else:
        # Calcular tiempo muerto
        t_inicio = time(h_i, m_i)
        t_fin = time(h_f, m_f)
        dt_i = datetime.combine(date.today(), t_inicio)
        dt_f = datetime.combine(date.today(), t_fin)
        if dt_f < dt_i: dt_f += timedelta(days=1)
        minutos = int((dt_f - dt_i).total_seconds() / 60)

        # Buscar nombre del técnico para el reporte
        nombre_resp = df_tecnicos[df_tecnicos['ID'] == id_resp]['NOMBRE'].iloc[0] if id_resp in df_tecnicos['ID'].values else id_resp

        # Preparar fila
        fila = [
            date.today().isocalendar()[1], # Semana
            date.today().strftime("%Y-%m-%d"), # Fecha
            turno,
            nombre_resp,
            ", ".join(apoyo),
            celda,
            robot,
            falla_final,
            "", # Espacio para descripción extra si se requiere
            sintoma,
            accion,
            "", "", "", "", # Columnas vacías para compatibilidad
            minutos,
            ""
        ]

        hoja = conectar_google_sheet()
        if hoja:
            hoja.append_row(fila)
            st.balloons()
            st.success(f"✅ Reporte guardado. Tiempo Muerto: {minutos} min")
        else:
            st.error("❌ Error de conexión con Google Sheets")
