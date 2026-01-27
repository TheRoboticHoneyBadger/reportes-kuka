import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta, time
import gspread
import plotly.express as px
import os

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Mantenimiento Magna", page_icon="🤖", layout="wide")

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

# --- CARGA DE DATOS ---
@st.cache_data
def cargar_datos_seguros():
    try:
        df_c = pd.read_csv('catalogo_fallas.csv')
        df_t = pd.read_csv('tecnicos.csv', dtype=str)
        df_cr = pd.read_csv('celdas_robots.csv', dtype=str)
        
        df_c.columns = [str(c).strip().upper() for c in df_c.columns]
        df_t.columns = [str(c).strip().upper() for c in df_t.columns]
        df_cr.columns = [str(c).strip().upper() for c in df_cr.columns]
        
        return df_c, df_t, df_cr
    except:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

df_catalogo, df_tecnicos, df_celdas_robots = cargar_datos_seguros()

# --- MENÚ LATERAL ---
st.sidebar.title("🔧 Menú")
menu = st.sidebar.radio("Ir a:", ["📝 Nuevo Reporte", "📊 Estadísticas"])

if menu == "📝 Nuevo Reporte":
    st.image("logo.png" if os.path.exists("logo.png") else "https://cdn-icons-png.flaticon.com/512/8636/8636080.png", width=300)
    st.title("Reporte de fallas de mantenimiento")
    st.markdown("---")

    if not df_catalogo.empty and not df_tecnicos.empty and not df_celdas_robots.empty:
        col_id_tec = df_tecnicos.columns[0]
        col_nom_tec = df_tecnicos.columns[1]
        nombres_lista = sorted(df_tecnicos[col_nom_tec].tolist())

        with st.form("form_reporte"):
            # IDENTIFICACIÓN
            c1, c2 = st.columns([1, 1])
            with c1:
                id_resp = st.text_input("Número de control responsable:", max_chars=5)
                nombre_tecnico_detectado = ""
                if id_resp:
                    match = df_tecnicos[df_tecnicos[col_id_tec] == id_resp]
                    if not match.empty:
                        nombre_tecnico_detectado = match[col_nom_tec].iloc[0]
                        st.markdown(f"**👤 Técnico:** `{nombre_tecnico_detectado}`")
            with c2:
                apoyo = st.multiselect("Personal de Apoyo (Busca por nombre):", options=nombres_lista)

            # UBICACIÓN DINÁMICA
            c3, c4, c5 = st.columns(3)
            turno = c3.selectbox("Turno:", ["Mañana", "Tarde", "Noche"])
            col_celda = df_celdas_robots.columns[0]
            col_robot = df_celdas_robots.columns[1]
            celda_sel = c4.selectbox("Celda:", sorted(df_celdas_robots[col_celda].unique()))
            robots_filtrados = df_celdas_robots[df_celdas_robots[col_celda] == celda_sel][col_robot].tolist()
            robot_sel = c5.selectbox("Robot:", sorted(robots_filtrados))

            # SELECTORES DE FALLA
            area_sel = st.selectbox("Área:", df_catalogo['AREA'].unique())
            tipo_sel = st.selectbox("Tipo de Falla:", df_catalogo[df_catalogo['AREA'] == area_sel]['TIPO'].unique())
            df_f = df_catalogo[(df_catalogo['AREA'] == area_sel) & (df_catalogo['TIPO'] == tipo_sel)]
            opciones_falla = (df_f['CODIGO DE FALLO'] + " - " + df_f['SUB MODO DE FALLA']).tolist()
            falla_sel = st.selectbox("Código de Falla:", opciones_falla)

            sintoma = st.text_area("Descripción / Síntoma:", height=80)
            accion = st.text_area("Acción Correctiva:", height=80)

            # TIEMPOS
            st.write("**Tiempos (Formato 4 dígitos: HHMM)**")
            t_c1, t_c2 = st.columns(2)
            ahora_num = int(datetime.now().strftime("%H%M"))
            num_ini = t_c1.number_input("Hora Inicio:", value=ahora_num, step=1, format="%d")
            num_fin = t_c2.number_input("Hora Fin:", value=ahora_num, step=1, format="%d")

            # --- NUEVO: CÁMARA DE EVIDENCIA ---
            st.write("---")
            st.write("**📸 Evidencia Fotográfica**")
            foto = st.camera_input("Tomar foto de la falla (Opcional)")

            enviar = st.form_submit_button("GUARDAR REPORTE", type="primary", use_container_width=True)

        if enviar:
            if not id_resp:
                st.error("⚠️ El número de control es obligatorio.")
            else:
                h_i, h_f = convertir_a_hora(num_ini), convertir_a_hora(num_fin)
                dt_i, dt_f = datetime.combine(date.today(), h_i), datetime.combine(date.today(), h_f)
                if dt_f < dt_i: dt_f += timedelta(days=1)
                minutos = int((dt_f - dt_i).total_seconds() / 60)

                nombre_final = nombre_tecnico_detectado if nombre_tecnico_detectado else id_resp
                
                # Nota: Guardar fotos en Google Sheets directamente es complejo, 
                # por ahora registraremos si se tomó o no evidencia.
                tiene_foto = "SÍ" if foto is not None else "NO"

                fila = [
                    date.today().isocalendar()[1], date.today().strftime("%Y-%m-%d"), turno,
                    nombre_final, ", ".join(apoyo), celda_sel, robot_sel, falla_sel, "",
                    sintoma, accion, "", "", "", tiene_foto, minutos, ""
                ]

                hoja = conectar_google_sheet()
                if hoja:
                    hoja.append_row(fila)
                    st.balloons()
                    st.success(f"✅ Guardado. Tiempo muerto: {minutos} min. Evidencia: {tiene_foto}")

elif menu == "📊 Estadísticas":
    st.title("📊 Indicadores de Mantenimiento")
    # ... (Aquí va el código de gráficas que ya tenemos)
