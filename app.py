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

# --- FUNCIÓN DE CONVERSIÓN DE HORA ---
def convertir_a_hora(valor):
    try:
        texto = str(int(valor)).zfill(4)
        h, m = int(texto[:2]), int(texto[2:])
        return time(min(h, 23), min(m, 59))
    except:
        return time(0, 0)

# --- CARGA DE DATOS SIN ERRORES (BUSQUEDA POR POSICIÓN) ---
@st.cache_data
def cargar_datos_seguros():
    try:
        # Cargamos catálogos
        df_c = pd.read_csv('catalogo_fallas.csv')
        df_t = pd.read_csv('tecnicos.csv', dtype=str)
        
        # Limpieza extrema: quitamos espacios y ponemos todo en mayúsculas
        df_c.columns = [str(c).strip().upper() for c in df_c.columns]
        df_t.columns = [str(c).strip().upper() for c in df_t.columns]
        
        return df_c, df_t
    except Exception as e:
        st.error(f"Faltan archivos: tecnicos.csv o catalogo_fallas.csv en GitHub")
        return pd.DataFrame(), pd.DataFrame()

df_catalogo, df_tecnicos = cargar_datos_seguros()

# --- ENCABEZADO ---
col_logo, col_tit = st.columns([1, 4])
with col_logo:
    st.image("logo.png" if os.path.exists("logo.png") else "https://cdn-icons-png.flaticon.com/512/8636/8636080.png", width=70)
with col_tit:
    st.title("Reporte de fallas de mantenimiento")

# --- PROCESO PRINCIPAL ---
if not df_catalogo.empty and not df_tecnicos.empty:
    with st.form("formulario_principal"):
        st.markdown("### 👤 Personal")
        
        # ID de Responsable (Usamos la primera columna del CSV de técnicos como ID)
        col_id_tec = df_tecnicos.columns[0]
        col_nom_tec = df_tecnicos.columns[1]
        
        id_resp = st.text_input("No. Control Responsable", max_chars=5)
        
        nombres_lista = df_tecnicos[col_nom_tec].tolist()
        apoyo = st.multiselect("Personal de Apoyo", nombres_lista)
        turno = st.selectbox("Turno", ["Mañana", "Tarde", "Noche"])

        st.markdown("### 📍 Ubicación")
        c1, c2 = st.columns(2)
        celda = c1.text_input("Celda")
        robot = c2.text_input("Robot")

        st.markdown("### 📋 Falla")
        # Columnas del catálogo por posición: 0:AREA, 1:TIPO, 2:CODIGO, 3:SUBMODO
        c_area = df_catalogo.columns[0]
        c_tipo = df_catalogo.columns[1]
        c_cod  = df_catalogo.columns[2]
        c_sub  = df_catalogo.columns[3]

        areas = df_catalogo[c_area].unique()
        area_sel = st.selectbox("Área", areas)
        
        tipos = df_catalogo[df_catalogo[c_area] == area_sel][c_tipo].unique()
        tipo_sel = st.selectbox("Tipo de Falla", tipos)

        df_f = df_catalogo[(df_catalogo[c_area] == area_sel) & (df_catalogo[c_tipo] == tipo_sel)]
        opciones = (df_f[c_cod].astype(str) + " - " + df_f[c_sub].astype(str)).tolist()
        falla_sel = st.selectbox("Código Específico", opciones)

        st.markdown("### 🛠️ Ejecución")
        sintoma = st.text_area("Descripción (Síntoma)")
        accion = st.text_area("Acción Correctiva")

        st.markdown("### ⏱️ Tiempos (4 dígitos)")
        t_c1, t_c2 = st.columns(2)
        ahora_num = int(datetime.now().strftime("%H%M"))
        
        with t_c1:
            num_ini = st.number_input("Hora Inicio (Ej: 0830)", value=ahora_num, step=1, format="%d")
        with t_c2:
            num_fin = st.number_input("Hora Fin (Ej: 0915)", value=ahora_num, step=1, format="%d")

        # BOTÓN DENTRO DEL FORMULARIO
        enviar = st.form_submit_button("GUARDAR REPORTE", type="primary", use_container_width=True)

    # --- LÓGICA DE ENVÍO ---
    if enviar:
        if not id_resp or not celda:
            st.error("⚠️ Error: El ID y la Celda son obligatorios.")
        else:
            # Calcular tiempo muerto
            h_i, h_f = convertir_a_hora(num_ini), convertir_a_hora(num_fin)
            dt_i, dt_f = datetime.combine(date.today(), h_i), datetime.combine(date.today(), h_f)
            if dt_f < dt_i: dt_f += timedelta(days=1)
            minutos = int((dt_f - dt_i).total_seconds() / 60)

            # Buscar nombre del responsable
            match = df_tecnicos[df_tecnicos[col_id_tec] == id_resp]
            nombre_final = match[col_nom_tec].iloc[0] if not match.empty else id_resp

            # Fila para Google Sheets
            fila = [
                date.today().isocalendar()[1], date.today().strftime("%Y-%m-%d"), turno,
                nombre_final, ", ".join(apoyo), celda, robot, falla_sel, "",
                sintoma, accion, "", "", "", "", minutos, ""
            ]

            hoja = conectar_google_sheet()
            if hoja:
                hoja.append_row(fila)
                st.balloons()
                st.success(f"✅ Reporte guardado con éxito. ({minutos} min)")
            else:
                st.error("❌ Error de conexión con Google Sheets.")
else:
    st.warning("⚠️ Los archivos CSV no se cargaron correctamente. Revisa GitHub.")
