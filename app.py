import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta, time
import gspread
import os

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="KUKA Mantenimiento", page_icon="🤖", layout="centered")

# CSS PARA FORZAR ALINEACIÓN HORIZONTAL Y ESTILO PROFESIONAL
st.markdown("""
    <style>
    /* Forzar que las columnas de la hora no se apilen en el celular */
    [data-testid="column"] {
        width: fit-content !important;
        flex: unset !important;
        min-width: 0px !important;
    }
    [data-testid="stHorizontalBlock"] {
        align-items: center !important;
        justify-content: flex-start !important;
        gap: 8px !important;
        display: flex !important;
        flex-direction: row !important;
    }
    /* Quitar margen superior de las etiquetas ocultas */
    .stNumberInput div {
        margin-top: 0px !important;
    }
    /* Estilo para los dos puntos */
    .puntos-separador {
        font-size: 24px;
        font-weight: bold;
        margin-bottom: 5px;
        color: #31333F;
    }
    .titulo-form {
        color: #1E3A8A;
        font-weight: bold;
        margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXIÓN A GOOGLE SHEETS ---
def conectar_google_sheet():
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        gc = gspread.service_account_from_dict(creds_dict)
        return gc.open("Base_Datos_Mantenimiento").sheet1
    except:
        return None

# --- CARGA DE DATOS ---
@st.cache_data
def cargar_datos():
    try:
        df_cat = pd.read_csv('catalogo_fallas.csv')
        df_cat.columns = df_cat.columns.str.strip().str.upper()
        df_tec = pd.read_csv('tecnicos.csv', dtype={'ID': str})
        df_tec.columns = df_tec.columns.str.strip().str.upper()
        return df_cat, df_tec
    except:
        return pd.DataFrame(), pd.DataFrame()

df_catalogo, df_tecnicos = cargar_datos()

# --- ENCABEZADO ---
col_logo, col_tit = st.columns([1, 4])
with col_logo:
    st.image("logo.png" if os.path.exists("logo.png") else "https://cdn-icons-png.flaticon.com/512/8636/8636080.png", width=70)
with col_tit:
    st.markdown("<h2 class='titulo-form'>Reporte de fallas de mantenimiento</h2>", unsafe_allow_html=True)

# --- FORMULARIO PRINCIPAL ---
with st.form("form_mantenimiento"):
    
    # 1. IDENTIFICACIÓN
    st.markdown("#### 👤 Responsable")
    id_resp = st.text_input("No. Control Responsable", max_chars=5)
    
    nombres_tec = df_tecnicos['NOMBRE'].tolist() if not df_tecnicos.empty else []
    apoyo = st.multiselect("Personal de Apoyo", nombres_tec)
    turno = st.selectbox("Turno", ["Mañana", "Tarde", "Noche"])

    # 2. LOCALIZACIÓN
    st.markdown("#### 📍 Ubicación")
    c_loc1, c_loc2 = st.columns(2)
    celda = c_loc1.text_input("Celda")
    robot = c_loc2.text_input("Robot")
    
    # 3. FALLA
    st.markdown("#### 📋 Detalle de la Falla")
    col_a = next((c for c in df_catalogo.columns if "AREA" in c), "AREA")
    col_t = next((c for c in df_catalogo.columns if "TIPO" in c), "TIPO")
    
    areas = df_catalogo[col_a].unique() if not df_catalogo.empty else []
    area_sel = st.selectbox("Área", areas)
    
    tipos = df_catalogo[df_catalogo[col_a] == area_sel][col_t].unique() if not df_catalogo.empty else []
    tipo_sel = st.selectbox("Tipo de Falla", tipos)

    df_f = df_catalogo[(df_catalogo[col_a] == area_sel) & (df_catalogo[col_t] == tipo_sel)]
    col_c = next((c for c in df_f.columns if "CODIGO" in c), df_f.columns[0])
    col_d = next((c for c in df_f.columns if "SUB" in c or "MODO" in c or "DESC" in c), df_f.columns[-1])
    
    opciones_falla = (df_f[col_c] + " - " + df_f[col_d]).tolist() if not df_f.empty else ["Sin datos"]
    seleccion_falla = st.selectbox("Código Específico", opciones_falla)

    # 4. EJECUCIÓN
    st.markdown("#### 🛠️ Trabajo Realizado")
    sintoma = st.text_area("Descripción / Síntoma")
    accion = st.text_area("Acción Correctiva")

    # 5. TIEMPOS (RELOJ DIGITAL HORIZONTAL PROTEGIDO)
    st.markdown("#### ⏱️ Tiempos (24h)")
    ahora = datetime.now()

    # BLOQUE INICIO
    st.write("**Hora Inicio:**")
    c_h1, c_sep1, c_m1, c_sp1 = st.columns([1, 0.2, 1, 3])
    with c_h1:
        h_ini = st.number_input("HI", 0, 23, ahora.hour, key="hi", label_visibility="collapsed", format="%02d")
    with c_sep1:
        st.markdown('<p class="puntos-separador">:</p>', unsafe_allow_html=True)
    with c_m1:
        m_ini = st.number_input("MI", 0, 59, ahora.minute, key="mi", label_visibility="collapsed", format="%02d")

    # BLOQUE FIN
    st.write("**Hora Fin:**")
    c_h2, c_sep2, c_m2, c_sp2 = st.columns([1, 0.2, 1, 3])
    with c_h2:
        h_fin = st.number_input("HF", 0, 23, ahora.hour, key="hf", label_visibility="collapsed", format="%02d")
    with c_sep2:
        st.markdown('<p class="puntos-separador">:</p>', unsafe_allow_html=True)
    with c_m2:
        m_fin = st.number_input("MF", 0, 59, ahora.minute, key="mf", label_visibility="collapsed", format="%02d")

    st.markdown("---")
    enviar = st.form_submit_button("💾 GUARDAR REPORTE", type="primary", use_container_width=True)

# --- LÓGICA DE GUARDADO ---
if enviar:
    if not id_resp or not celda:
        st.error("⚠️ Datos obligatorios faltantes")
    else:
        dt_i = datetime.combine(date.today(), time(h_ini, m_ini))
        dt_f = datetime.combine(date.today(), time(h_fin, m_fin))
        if dt_f < dt_i: dt_f += timedelta(days=1)
        duracion = int((dt_f - dt_i).total_seconds() / 60)

        nombre_tec = df_tecnicos[df_tecnicos['ID'] == id_resp]['NOMBRE'].iloc[0] if id_resp in df_tecnicos['ID'].values else id_resp

        fila = [
            date.today().isocalendar()[1], date.today().strftime("%Y-%m-%d"), turno,
            nombre_tec, ", ".join(apoyo), celda, robot, seleccion_falla, "",
            sintoma, accion, "", "", "", "", duracion, ""
        ]

        hoja = conectar_google_sheet()
        if hoja:
            hoja.append_row(fila)
            st.balloons()
            st.success(f"✅ Guardado. Tiempo muerto: {duracion} min")
