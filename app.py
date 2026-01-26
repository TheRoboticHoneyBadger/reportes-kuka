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
    texto = str(int(valor)).zfill(4)
    try:
        h, m = int(texto[:2]), int(texto[2:])
        return time(min(h, 23), min(m, 59))
    except:
        return time(0, 0)

# --- CARGA Y LIMPIEZA AUTOMÁTICA DE DATOS ---
@st.cache_data
def cargar_datos():
    try:
        # Cargamos y limpiamos encabezados (quita espacios y pone en mayúsculas)
        df_c = pd.read_csv('catalogo_fallas.csv')
        df_c.columns = df_c.columns.str.strip().str.upper()
        
        df_t = pd.read_csv('tecnicos.csv', dtype={'ID': str})
        df_t.columns = df_t.columns.str.strip().str.upper()
        return df_c, df_t
    except Exception as e:
        st.error(f"⚠️ Error crítico: Asegúrate que 'tecnicos.csv' y 'catalogo_fallas.csv' estén en GitHub.")
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

# --- FORMULARIO (BLOQUE PROTEGIDO) ---
if not df_catalogo.empty and not df_tecnicos.empty:
    with st.form("form_final"):
        st.markdown("### 👤 Personal")
        id_resp = st.text_input("No. Control Responsable", max_chars=5)
        
        # Selección flexible de columna de nombre
        col_n = 'NOMBRE' if 'NOMBRE' in df_tecnicos.columns else df_tecnicos.columns[1]
        nombres_tec = df_tecnicos[col_n].tolist()
        
        apoyo = st.multiselect("Personal de Apoyo", nombres_tec)
        turno = st.selectbox("Turno", ["Mañana", "Tarde", "Noche"])

        st.markdown("### 📍 Ubicación")
        c1, c2 = st.columns(2)
        celda = c1.text_input("Celda")
        robot = c2.text_input("Robot")

        st.markdown("### 📋 Detalle de Falla")
        area_sel = st.selectbox("Área", df_catalogo['AREA'].unique())
        
        df_area = df_catalogo[df_catalogo['AREA'] == area_sel]
        tipo_sel = st.selectbox("Tipo de Falla", df_area['TIPO'].unique())

        df_f = df_area[df_area['TIPO'] == tipo_sel]
        # Concatenamos Código + Submodo (usando nombres limpios)
        opciones = (df_f['CODIGO DE FALLO'] + " - " + df_f['SUB MODO DE FALLA']).tolist()
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

        # EL BOTÓN ESTÁ DENTRO DEL FORMULARIO (SÍ O SÍ)
        enviar = st.form_submit_button("GUARDAR REPORTE", type="primary", use_container_width=True)

    # --- LÓGICA DE GUARDADO ---
    if enviar:
        if not id_resp or not celda:
            st.error("⚠️ Falta ID o Celda.")
        else:
            h_i, h_f = convertir_a_hora(num_ini), convertir_a_hora(num_fin)
            dt_i = datetime.combine(date.today(), h_i)
            dt_f = datetime.combine(date.today(), h_f)
            if dt_f < dt_i: dt_f += timedelta(days=1)
            minutos = int((dt_f - dt_i).total_seconds() / 60)

            # Buscar nombre del técnico responsable
            nombre_resp = df_tecnicos[df_tecnicos['ID'] == id_resp][col_n].iloc[0] if id_resp in df_tecnicos['ID'].values else id_resp

            fila = [
                date.today().isocalendar()[1], date.today().strftime("%Y-%m-%d"), turno,
                nombre_resp, ", ".join(apoyo), celda, robot, falla_sel, "",
                sintoma, accion, "", "", "", "", minutos, ""
            ]

            hoja = conectar_google_sheet()
            if hoja:
                hoja.append_row(fila)
                st.balloons()
                st.success(f"✅ Guardado. Tiempo muerto: {minutos} min")
else:
    st.warning("⚠️ Esperando archivos de configuración...")
