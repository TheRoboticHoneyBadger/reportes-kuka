import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta, time
import gspread
import plotly.express as px
import os

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Mantenimiento KUKA", page_icon="🤖", layout="wide")

# --- CONEXIÓN A GOOGLE SHEETS ---
def conectar_google_sheet():
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        gc = gspread.service_account_from_dict(creds_dict)
        return gc.open("Base_Datos_Mantenimiento").sheet1
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None

# --- CARGA DE DATOS ---
@st.cache_data
def cargar_datos():
    try:
        df_cat = pd.read_csv('catalogo_fallas.csv')
        df_cat.columns = df_cat.columns.str.strip().str.upper()
        df_cat = df_cat.astype(str)
        df_tec = pd.read_csv('tecnicos.csv', dtype={'ID': str})
        return df_cat, df_tec
    except:
        return pd.DataFrame(), pd.DataFrame()

df_catalogo, df_tecnicos = cargar_datos()

# --- BARRA LATERAL ---
st.sidebar.title("🔧 Menú")
menu = st.sidebar.radio("Ir a:", ["📝 Nuevo Reporte", "📊 Estadísticas"])

if menu == "📝 Nuevo Reporte":
    # ENCABEZADO
    col_logo, col_titulo = st.columns([1, 5])
    with col_logo:
        if os.path.exists("logo.png"):
            st.image("logo.png", width=100)
        else:
            st.image("https://cdn-icons-png.flaticon.com/512/8636/8636080.png", width=80)
    
    with col_titulo:
        st.title("Reporte de fallas de mantenimiento")

    st.markdown("---")

    with st.form("form_reporte"):
        
        # --- 1. DATOS GENERALES ---
        st.subheader("1. Datos Generales")
        c1, c2, c3 = st.columns(3)
        id_responsable = c1.text_input("No. Control Responsable", max_chars=5)
        responsable = ""
        if id_responsable and not df_tecnicos.empty:
            user = df_tecnicos[df_tecnicos['ID'] == id_responsable]
            if not user.empty:
                responsable = user.iloc[0]['Nombre']
                c1.success(f"👤 {responsable}")
        
        lista_nombres = df_tecnicos['Nombre'].unique().tolist() if not df_tecnicos.empty else []
        apoyo_seleccionado = c2.multiselect("Personal de Apoyo", lista_nombres)
        turno = c3.selectbox("Turno", ["Mañana", "Tarde", "Noche"])

        # --- 2. UBICACIÓN Y ORDEN ---
        st.subheader("2. Ubicación y Orden")
        u1, u2, u3, u4, u5 = st.columns(5)
        celda = u1.text_input("Celda")
        robot = u2.text_input("Robot")
        no_orden = u3.text_input("No. de Orden")
        tipo_orden = u4.selectbox("Tipo de Orden", ["Correctivo", "Preventivo", "Mejora", "Falla Menor"])
        status = u5.selectbox("Status", ["Cerrada", "Abierta", "Pendiente de Refacción"])

        # --- 3. DETALLE DE LA FALLA ---
        st.subheader("3. Detalle de la Falla")
        col_cat1, col_cat2 = st.columns(2)
        
        col_area = next((c for c in df_catalogo.columns if "AREA" in c), "AREA")
        areas = df_catalogo[col_area].unique() if not df_catalogo.empty else []
        area_sel = col_cat1.selectbox("Área", areas)
        
        col_tipo = next((c for c in df_catalogo.columns if "TIPO" in c), "TIPO")
        tipos = df_catalogo[df_catalogo[col_area] == area_sel][col_tipo].unique() if not df_catalogo.empty else []
        tipo_sel = col_cat2.selectbox("Tipo de Falla", tipos)

        lista_opciones = ["Sin datos"]
        if not df_catalogo.empty:
            df_final = df_catalogo[(df_catalogo[col_area] == area_sel) & (df_catalogo[col_tipo] == tipo_sel)]
            col_codigo = next((c for c in df_final.columns if "CODIGO" in c), df_final.columns[0])
            col_submodo = next((c for c in df_final.columns if "SUB" in c or "MODO" in c or "DESC" in c), df_final.columns[-1])
            lista_opciones = df_final[col_codigo] + " - " + df_final[col_submodo]
        
        seleccion_completa = st.selectbox("Código Específico", lista_opciones)

        # --- 4. EJECUCIÓN ---
        st.subheader("4. Ejecución")
        desc_trabajo = st.text_area("Descripción del Trabajo (Síntoma)")
        acciones = st.text_area("Acciones Correctivas / Actividad")
        solucion = st.text_area("Solución Final")

        # --- 5. TIEMPOS (ALINEACIÓN HORIZONTAL ESTRICTA) ---
        st.subheader("5. Tiempos (Formato 24h)")
        ahora = datetime.now()

        # Fila para Hora de Inicio
        st.write("**Hora Inicio:**")
        hi1, hi2, hi3, hi_spacer = st.columns([0.5, 0.1, 0.5, 3])
        with hi1:
            h_ini = st.number_input("H_I", 0, 23, ahora.hour, 1, format="%02d", label_visibility="collapsed")
        with hi2:
            st.markdown("<h3 style='text-align: center; margin-top: -5px;'>:</h3>", unsafe_allow_html=True)
        with hi3:
            m_ini = st.number_input("M_I", 0, 59, ahora.minute, 1, format="%02d", label_visibility="collapsed")

        # Fila para Hora de Fin
        st.write("**Hora Fin:**")
        hf1, hf2, hf3, hf_spacer = st.columns([0.5, 0.1, 0.5, 3])
        with hf1:
            h_fin = st.number_input("H_F", 0, 23, ahora.hour, 1, format="%02d", label_visibility="collapsed")
        with hf2:
            st.markdown("<h3 style='text-align: center; margin-top: -5px;'>:</h3>", unsafe_allow_html=True)
        with hf3:
            m_fin = st.number_input("M_F", 0, 59, ahora.minute, 1, format="%02d", label_visibility="collapsed")

        comentario = st.text_input("Comentario Adicional")
        enviar = st.form_submit_button("Guardar Reporte", type="primary")

    if enviar:
        if not id_responsable or not celda:
            st.error("⚠️ Datos incompletos.")
        else:
            # Lógica de guardado...
            hora_inicio = time(h_ini, m_ini)
            hora_fin = time(h_fin, m_fin)
            dt_ini = datetime.combine(date.today(), hora_inicio)
            dt_fin = datetime.combine(date.today(), hora_fin)
            if dt_fin < dt_ini: dt_fin += timedelta(days=1)
            tiempo_muerto = int((dt_fin - dt_ini).total_seconds() / 60)
            
            fila = [date.today().isocalendar()[1], date.today().strftime("%Y-%m-%d"), turno, id_responsable, 
                    ", ".join(apoyo_seleccionado), celda, robot, seleccion_completa, "", desc_trabajo, 
                    acciones, solucion, no_orden, tipo_orden, status, tiempo_muerto, comentario]
            
            hoja = conectar_google_sheet()
            if hoja:
                hoja.append_row(fila)
                st.balloons()
                st.success(f"✅ Guardado. Tiempo muerto: {tiempo_muerto} min")

elif menu == "📊 Estadísticas":
    st.title("📊 Indicadores")
    # (Resto del código de estadísticas igual...)
