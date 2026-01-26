import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta, time
import gspread
import os

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Mantenimiento KUKA", page_icon="🤖", layout="centered")

# --- CONEXIÓN A GOOGLE SHEETS ---
def conectar_google_sheet():
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        gc = gspread.service_account_from_dict(creds_dict)
        return gc.open("Base_Datos_Mantenimiento").sheet1
    except:
        return None

# --- FUNCIÓN PARA CONVERTIR NÚMERO A HORA ---
def convertir_a_hora(valor):
    # Convierte un número como 1430 en un objeto de tiempo 14:30
    texto = str(int(valor)).zfill(4)
    try:
        h = int(texto[:2])
        m = int(texto[2:])
        if h > 23: h = 23
        if m > 59: m = 59
        return time(h, m)
    except:
        return time(0, 0)

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
    if os.path.exists("logo.png"):
        st.image("logo.png", width=80)
    else:
        st.image("https://cdn-icons-png.flaticon.com/512/8636/8636080.png", width=60)
with col_tit:
    st.title("Reporte de fallas de mantenimiento")

# --- FORMULARIO ---
with st.form("form_rapido"):
    st.markdown("### 👤 Datos del Técnico")
    id_resp = st.text_input("No. Control Responsable", max_chars=5)
    
    nombres_tec = df_tecnicos['NOMBRE'].tolist() if not df_tecnicos.empty else []
    apoyo = st.multiselect("Personal de Apoyo", nombres_tec)
    turno = st.selectbox("Turno", ["Mañana", "Tarde", "Noche"])

    st.markdown("### 📍 Ubicación")
    c1, c2 = st.columns(2)
    celda = c1.text_input("Celda")
    robot = c2.text_input("Robot")

    st.markdown("### 📋 Falla")
    col_a = next((c for c in df_catalogo.columns if "AREA" in c), "AREA")
    areas = df_catalogo[col_a].unique() if not df_catalogo.empty else []
    area_sel = st.selectbox("Área", areas)
    
    col_t = next((c for c in df_catalogo.columns if "TIPO" in c), "TIPO")
    tipos = df_catalogo[df_catalogo[col_a] == area_sel][col_t].unique() if not df_catalogo.empty else []
    tipo_sel = st.selectbox("Tipo de Falla", tipos)

    df_f = df_catalogo[(df_catalogo[col_a] == area_sel) & (df_catalogo[col_t] == tipo_sel)]
    col_c = next((c for c in df_f.columns if "CODIGO" in c), df_f.columns[0] if not df_f.empty else "")
    col_d = next((c for c in df_f.columns if "SUB" in c or "MODO" in c or "DESC" in c), df_f.columns[-1] if not df_f.empty else "")
    
    opciones = (df_f[col_c] + " - " + df_f[col_d]).tolist() if not df_f.empty else ["Sin datos"]
    falla_sel = st.selectbox("Código de Falla", opciones)

    st.markdown("### 🛠️ Ejecución")
    sintoma = st.text_area("Descripción del Síntoma")
    accion = st.text_area("Acción Realizada")

    # --- SECCIÓN DE TIEMPOS (4 DÍGITOS) ---
    st.markdown("### ⏱️ Tiempos (Formato 4 dígitos)")
    st.info("Escribe la hora seguida de los minutos (Ej: 0830 o 1415)")
    
    ahora_num = int(datetime.now().strftime("%H%M"))
    
    t_c1, t_c2 = st.columns(2)
    with t_c1:
        num_ini = st.number_input("Hora Inicio", value=ahora_num, step=1, format="%d")
        # Mostramos ayuda visual de lo que se interpretará
        h_i_obj = convertir_a_hora(num_ini)
        st.caption(f"Interpretado como: {h_i_obj.strftime('%H:%M')}")
        
    with t_c2:
        num_fin = st.number_input("Hora Fin", value=ahora_num, step=1, format="%d")
        h_f_obj = convertir_a_hora(num_fin)
        st.caption(f"Interpretado como: {h_f_obj.strftime('%H:%M')}")

    enviar = st.form_submit_button("GUARDAR REPORTE", type="primary", use_container_width=True)

# --- GUARDADO ---
if enviar:
    if not id_resp or not celda:
        st.error("⚠️ Falta ID o Celda")
    else:
        dt_i = datetime.combine(date.today(), convertir_a_hora(num_ini))
        dt_f = datetime.combine(date.today(), convertir_a_hora(num_fin))
        if dt_f < dt_i: dt_f += timedelta(days=1)
        duracion = int((dt_f - dt_i).total_seconds() / 60)

        nombre_tec = df_tecnicos[df_tecnicos['ID'] == id_resp]['NOMBRE'].iloc[0] if id_resp in df_tecnicos['ID'].values else id_resp

        fila = [
            date.today().isocalendar()[1], date.today().strftime("%Y-%m-%d"), turno,
            nombre_tec, ", ".join(apoyo), celda, robot, falla_sel, "",
            sintoma, accion, "", "", "", "", duracion, ""
        ]

        hoja = conectar_google_sheet()
        if hoja:
            hoja.append_row(fila)
            st.balloons()
            st.success(f"✅ Guardado. Tiempo muerto: {duracion} min")
