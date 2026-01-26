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

# --- CARGA Y LIMPIEZA DE DATOS (SANEAMIENTO DE COLUMNAS) ---
@st.cache_data
def cargar_datos():
    try:
        # Cargamos catálogos y eliminamos espacios accidentales en los encabezados
        df_c = pd.read_csv('catalogo_fallas.csv')
        df_c.columns = df_c.columns.str.strip().str.upper()
        
        df_t = pd.read_csv('tecnicos.csv', dtype={'ID': str})
        df_t.columns = df_t.columns.str.strip().str.upper()
        return df_c, df_t
    except Exception as e:
        st.error(f"Error cargando archivos: Verifica que tecnicos.csv y catalogo_fallas.csv estén en GitHub")
        return pd.DataFrame(), pd.DataFrame()

df_catalogo, df_tecnicos = cargar_datos()

# --- ENCABEZADO ---
col_logo, col_tit = st.columns([1, 4])
with col_logo:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=70)
    else:
        st.image("https://cdn-icons-png.flaticon.com/512/8636/8636080.png", width=60)
with col_tit:
    st.subheader("Reporte de fallas de mantenimiento")

# --- FORMULARIO (TODO EL CONTENIDO DEBE ESTAR INDENTADO/DENTRO DEL WITH) ---
with st.form("form_mantenimiento"):
    st.markdown("### 👤 Personal")
    id_resp = st.text_input("No. Control Responsable", max_chars=5)
    
    # Buscamos la columna de nombre de forma flexible (Nombre, NOMBRE, etc)
    col_n = 'NOMBRE' if 'NOMBRE' in df_tecnicos.columns else df_tecnicos.columns[1] if not df_tecnicos.empty else ""
    nombres_tec = df_tecnicos[col_n].tolist() if col_n else []
    
    apoyo = st.multiselect("Personal de Apoyo", nombres_tec)
    turno = st.selectbox("Turno", ["Mañana", "Tarde", "Noche"])

    st.markdown("### 📍 Ubicación")
    c1, c2 = st.columns(2)
    celda = c1.text_input("Celda")
    robot = c2.text_input("Robot")

    st.markdown("### 📋 Detalle de Falla")
    # Filtros por Área y Tipo
    area_col = 'AREA' if 'AREA' in df_catalogo.columns else df_catalogo.columns[0]
    tipo_col = 'TIPO' if 'TIPO' in df_catalogo.columns else df_catalogo.columns[1]
    
    areas = df_catalogo[area_col].unique() if not df_catalogo.empty else []
    area_sel = st.selectbox("Área", areas)
    
    df_area = df_catalogo[df_catalogo[area_col] == area_sel]
    tipos = df_area[tipo_col].unique() if not df_area.empty else []
    tipo_sel = st.selectbox("Tipo de Falla", tipos)

    # Selección de código final (Concatenamos Código + Submodo)
    df_f = df_area[df_area[tipo_col] == tipo_sel]
    cod_col = 'CODIGO DE FALLO' if 'CODIGO DE FALLO' in df_f.columns else df_f.columns[2]
    sub_col = 'SUB MODO DE FALLA' if 'SUB MODO DE FALLA' in df_f.columns else df_f.columns[-1]
    
    opciones = (df_f[cod_col] + " - " + df_f[sub_col]).tolist() if not df_f.empty else ["Sin datos"]
    falla_sel = st.selectbox("Código Específico", opciones)

    st.markdown("### 🛠️ Ejecución")
    sintoma = st.text_area("Descripción (Síntoma)")
    accion = st.text_area("Acción Correctiva")

    st.markdown("### ⏱️ Tiempos (4 dígitos)")
    t_c1, t_c2 = st.columns(2)
    ahora_val = int(datetime.now().strftime("%H%M"))
    
    with t_c1:
        num_ini = st.number_input("Hora Inicio", value=ahora_val, step=1, format="%d")
    with t_c2:
        num_fin = st.number_input("Hora Fin", value=ahora_val, step=1, format="%d")

    # EL BOTÓN DEBE ESTAR DENTRO DEL BLOQUE 'WITH'
    enviar = st.form_submit_button("GUARDAR REPORTE", type="primary", use_container_width=True)

# --- LÓGICA DE GUARDADO (ESTO VA FUERA DEL FORMULARIO) ---
if enviar:
    if not id_resp or not celda:
        st.error("⚠️ Datos incompletos (ID o Celda)")
    else:
        # Calcular duración
        h_i, h_f = convertir_a_hora(num_ini), convertir_a_hora(num_fin)
        dt_i = datetime.combine(date.today(), h_i)
        dt_f = datetime.combine(date.today(), h_f)
        if dt_f < dt_i: dt_f += timedelta(days=1)
        minutos = int((dt_f - dt_i).total_seconds() / 60)

        # Nombre del responsable
        id_col = 'ID' if 'ID' in df_tecnicos.columns else df_tecnicos.columns[0]
        nombre_
