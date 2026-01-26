import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta, time
import gspread
import os

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="KUKA Mantenimiento", page_icon="🤖", layout="centered")

# --- CSS AVANZADO PARA FIJAR EL RELOJ ---
st.markdown("""
    <style>
    /* Estilo para el contenedor del reloj */
    .reloj-inline {
        display: flex;
        align-items: center;
        gap: 8px;
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 10px;
        width: fit-content;
    }
    .separador {
        font-size: 24px;
        font-weight: bold;
        color: #31333F;
        line-height: 1;
    }
    /* Quitar etiquetas extra de los number inputs dentro del reloj */
    div[data-testid="stNumberInput"] label {
        display: none !important;
    }
    div[data-testid="stNumberInput"] {
        width: 70px !important;
    }
    .titulo-principal {
        font-family: 'sans-serif';
        color: #0E1117;
        font-weight: 700;
        font-size: 24px;
        margin-bottom: 20px;
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

# --- ENCABEZADO ---
col_logo, col_tit = st.columns([1, 4])
with col_logo:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=80)
    else:
        st.image("https://cdn-icons-png.flaticon.com/512/8636/8636080.png", width=60)
with col_tit:
    st.markdown('<p class="titulo-principal">Reporte de fallas de mantenimiento</p>', unsafe_allow_html=True)

# --- FORMULARIO ---
with st.form("form_mantenimiento"):
    
    # 1. PERSONAL
    st.markdown("### 👤 Personal")
    id_resp = st.text_input("No. Control Responsable", max_chars=5)
    
    nombres_tec = df_tecnicos['NOMBRE'].tolist() if not df_tecnicos.empty else []
    apoyo = st.multiselect("Personal de Apoyo", nombres_tec)
    turno = st.selectbox("Turno", ["Mañana", "Tarde", "Noche"])

    # 2. UBICACIÓN
    st.markdown("### 📍 Ubicación")
    c_loc1, c_loc2 = st.columns(2)
    celda = c_loc1.text_input("Celda")
    robot = c_loc2.text_input("Robot")
    
    # 3. FALLA
    st.markdown("### 📋 Falla")
    col_a = next((c for c in df_catalogo.columns if "AREA" in c), "AREA")
    areas = df_catalogo[col_a].unique() if not df_catalogo.empty else []
    area_sel = st.selectbox("Área", areas)
    
    col_t = next((c for c in df_catalogo.columns if "TIPO" in c), "TIPO")
    tipos = df_catalogo[df_catalogo[col_a] == area_sel][col_t].unique() if not df_catalogo.empty else []
    tipo_sel = st.selectbox("Tipo de Falla", tipos)

    df_f = df_catalogo[(df_catalogo[col_a] == area_sel) & (df_catalogo[col_t] == tipo_sel)]
    col_c = next((c for c in df_f.columns if "CODIGO" in c), df_f.columns[0])
    col_d = next((c for c in df_f.columns if "SUB" in c or "MODO" in c or "DESC" in c), df_f.columns[-1])
    
    opciones_falla = (df_f[col_c] + " - " + df_f[col_d]).tolist() if not df_f.empty else ["Sin datos"]
    seleccion_falla = st.selectbox("Código Específico", opciones_falla)

    # 4. EJECUCIÓN
    st.markdown("### 🛠️ Trabajo")
    sintoma = st.text_area("Descripción / Síntoma")
    accion = st.text_area("Acción Correctiva")

    # 5. TIEMPOS (RELOJ BLINDADO HORIZONTAL)
    st.markdown("### ⏱️ Tiempos (24h)")
    ahora = datetime.now()

    # BLOQUE INICIO
    st.write("Hora Inicio:")
    c_ini_h, c_sep1, c_ini_m, c_sp1 = st.columns([1, 0.2, 1, 3])
    with c_ini_h:
        h_ini = st.number_input("H_I", 0, 23, ahora.hour, key="hi", format="%02d")
    with c_sep1:
        st.markdown('<p class="separador">:</p>', unsafe_allow_html=True)
    with c_ini_m:
        m_ini = st.number_input("M_I", 0, 59, ahora.minute, key="mi", format="%02d")

    # BLOQUE FIN
    st.write("Hora Fin:")
    c_fin_h, c_sep2, c_fin_m, c_sp2 = st.columns([1, 0.2, 1, 3])
    with c_fin_h:
        h_fin = st.number_input("H_F", 0, 23, ahora.hour, key="hf", format="%02d")
    with c_sep2:
        st.markdown('<p class="separador">:</p>', unsafe_allow_html=True)
    with c_fin_m:
        m_fin = st.number_input("M_F", 0, 59, ahora.minute, key="mf", format="%02d")

    st.markdown("---")
    enviar = st.form_submit_button("GUARDAR REPORTE", type="primary", use_container_width=True)

# --- LÓGICA DE GUARDADO ---
if enviar:
    if not id_resp or not celda:
        st.error("⚠️ Falta información necesaria.")
    else:
        # Cálculo de tiempo
        dt_i = datetime.combine(date.today(), time(h_ini, m_ini))
        dt_f = datetime.combine(date.today(), time(h_fin, m_fin))
        if dt_f < dt_i: dt_f += timedelta(days=1)
        duracion = int((dt_f - dt_i).total_seconds() / 60)

        # Nombre del técnico
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
