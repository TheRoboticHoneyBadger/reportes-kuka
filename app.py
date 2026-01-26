import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta, time
import gspread
import os

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="KUKA Mantenimiento", page_icon="🤖", layout="centered")

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
    texto = str(int(valor)).zfill(4)
    try:
        h, m = int(texto[:2]), int(texto[2:])
        return time(min(h, 23), min(m, 59))
    except:
        return time(0, 0)

# --- CARGA Y LIMPIEZA DE DATOS ---
@st.cache_data
def cargar_datos():
    try:
        # Cargamos catálogos y limpiamos nombres de columnas (QUITAR ESPACIOS Y MAYÚSCULAS)
        df_c = pd.read_csv('catalogo_fallas.csv')
        df_c.columns = df_c.columns.str.strip().str.upper()
        
        df_t = pd.read_csv('tecnicos.csv', dtype={'ID': str})
        df_t.columns = df_t.columns.str.strip().str.upper()
        return df_c, df_t
    except Exception as e:
        st.error(f"Error cargando archivos: {e}")
        return pd.DataFrame(), pd.DataFrame()

df_catalogo, df_tecnicos = cargar_datos()

# --- ENCABEZADO ---
col_logo, col_tit = st.columns([1, 4])
with col_logo:
    st.image("logo.png" if os.path.exists("logo.png") else "https://cdn-icons-png.flaticon.com/512/8636/8636080.png", width=70)
with col_tit:
    st.title("Reporte de fallas de mantenimiento")

# --- FORMULARIO (TODO DEBE IR DENTRO DEL 'WITH') ---
with st.form("form_mantenimiento"):
    st.markdown("### 👤 Personal")
    id_resp = st.text_input("No. Control Responsable", max_chars=5)
    
    # Buscamos la columna de nombre de forma flexible
    col_nombre_tec = 'NOMBRE' if 'NOMBRE' in df_tecnicos.columns else df_tecnicos.columns[1] if not df_tecnicos.empty else ""
    nombres_tec = df_tecnicos[col_nombre_tec].tolist() if col_nombre_tec else []
    
    apoyo = st.multiselect("Personal de Apoyo", nombres_tec)
    turno = st.selectbox("Turno", ["Mañana", "Tarde", "Noche"])

    st.markdown("### 📍 Ubicación")
    c1, c2 = st.columns(2)
    celda = c1.text_input("Celda")
    robot = c2.text_input("Robot")

    st.markdown("### 📋 Falla")
    # Filtros inteligentes
    areas = df_catalogo['AREA'].unique() if 'AREA' in df_catalogo.columns else []
    area_sel = st.selectbox("Área", areas)
    
    tipos = df_catalogo[df_catalogo['AREA'] == area_sel]['TIPO'].unique() if not df_catalogo.empty else []
    tipo_sel = st.selectbox("Tipo de Falla", tipos)

    df_f = df_catalogo[(df_catalogo['AREA'] == area_sel) & (df_catalogo['TIPO'] == tipo_sel)]
    opciones = (df_f['CODIGO DE FALLO'] + " - " + df_f['SUB MODO DE FALLA']).tolist() if not df_f.empty else ["Sin datos"]
    falla_sel = st.selectbox("Código de Falla", opciones)

    st.markdown("### 🛠️ Ejecución")
    sintoma = st.text_area("Descripción del Síntoma")
    accion = st.text_area("Acción Realizada")

    st.markdown("### ⏱️ Tiempos (4 dígitos)")
    t_c1, t_c2 = st.columns(2)
    ahora_n = int(datetime.now().strftime("%H%M"))
    
    with t_c1:
        num_ini = st.number_input("Hora Inicio", value=ahora_n, step=1, format="%d")
    with t_c2:
        num_fin = st.number_input("Hora Fin", value=ahora_n, step=1, format="%d")

    # EL BOTÓN AHORA SÍ ESTÁ DENTRO DEL FORMULARIO
    enviar = st.form_submit_button("GUARDAR REPORTE", type="primary", use_container_width=True)

# --- LÓGICA DE GUARDADO (FUERA DEL FORMULARIO) ---
if enviar:
    if not id_resp or not celda:
        st.error("⚠️ Falta ID o Celda")
    else:
        h_i, h_f = convertir_a_hora(num_ini), convertir_a_hora(num_fin)
        dt_i, dt_f = datetime.combine(date.today(), h_i), datetime.combine(date.today(), h_f)
        if dt_f < dt_i: dt_f += timedelta(days=1)
        minutos = int((dt_f - dt_i).total_seconds() / 60)

        # Buscar nombre del responsable
        id_col = 'ID' if 'ID' in df_tecnicos.columns else df_tecnicos.columns[0]
        nombre_resp = df_tecnicos[df_tecnicos[id_col] == id_resp][col_nombre_tec].iloc[0] if id_resp in df_tecnicos[id_col].values else id_resp

        fila = [
            date.today().isocalendar()[1], date.today().strftime("%Y-%m-%d"), turno,
            nombre_resp, ", ".join(apoyo), celda, robot, falla_sel, "",
            sintoma, accion, "", "", "", "", minutos, ""
        ]

        hoja = conectar_google_sheet()
        if hoja:
            hoja.append_row(fila)
            st.balloons()
            st.success(f"✅ Guardado en Google Sheets. Tiempo: {minutos} min")
