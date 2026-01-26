import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta, time
import gspread
import plotly.express as px
import os

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Mantenimiento KUKA", page_icon="🤖", layout="wide")

# --- TRUCO CSS PARA ALINEACIÓN HORIZONTAL EN MÓVIL ---
st.markdown("""
    <style>
    /* Fuerza a las columnas a no romperse en móvil */
    [data-testid="column"] {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        min-width: 0px !important;
    }
    [data-testid="stHorizontalBlock"] {
        display: flex;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        align-items: center !important;
    }
    /* Estilo para los dos puntos */
    .sep-reloj {
        font-size: 24px;
        font-weight: bold;
        margin-top: 15px;
    }
    </style>
    """, unsafe_allow_html=True)

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
    col_logo, col_titulo = st.columns([1, 4])
    with col_logo:
        if os.path.exists("logo.png"):
            st.image("logo.png", width=80)
        else:
            st.image("https://cdn-icons-png.flaticon.com/512/8636/8636080.png", width=60)
    
    with col_titulo:
        st.subheader("Reporte de fallas de mantenimiento")

    with st.form("form_reporte", clear_on_submit=False):
        
        # --- 1. DATOS GENERALES ---
        st.markdown("### 1. Datos Generales")
        id_responsable = st.text_input("No. Control Responsable", max_chars=5)
        
        lista_nombres = df_tecnicos['NOMBRE'].unique().tolist() if not df_tecnicos.empty else []
        apoyo_seleccionado = st.multiselect("Personal de Apoyo", lista_nombres)
        turno = st.selectbox("Turno", ["Mañana", "Tarde", "Noche"])

        # --- 2. UBICACIÓN Y DETALLE ---
        st.markdown("### 2. Detalles")
        c_u1, c_u2 = st.columns(2)
        celda = c_u1.text_input("Celda")
        robot = c_u2.text_input("Robot")
        
        # --- 3. FALLA ---
        col_area = next((c for c in df_catalogo.columns if "AREA" in c), "AREA")
        areas = df_catalogo[col_area].unique() if not df_catalogo.empty else []
        area_sel = st.selectbox("Área", areas)
        
        col_tipo = next((c for c in df_catalogo.columns if "TIPO" in c), "TIPO")
        tipos = df_catalogo[df_catalogo[col_area] == area_sel][col_tipo].unique() if not df_catalogo.empty else []
        tipo_sel = st.selectbox("Tipo de Falla", tipos)

        lista_opciones = ["Sin datos"]
        if not df_catalogo.empty:
            df_final = df_catalogo[(df_catalogo[col_area] == area_sel) & (df_catalogo[col_tipo] == tipo_sel)]
            col_codigo = next((c for c in df_final.columns if "CODIGO" in c), df_final.columns[0])
            col_submodo = next((c for c in df_final.columns if "SUB" in c or "MODO" in c or "DESC" in c), df_final.columns[-1])
            lista_opciones = df_final[col_codigo] + " - " + df_final[col_submodo]
        
        seleccion_completa = st.selectbox("Código Específico", lista_opciones)

        # --- 4. EJECUCIÓN ---
        desc_trabajo = st.text_area("Descripción (Síntoma)")
        acciones = st.text_area("Acciones Correctivas")

        # --- 5. TIEMPOS (RELOJ COMPACTO HORIZONTAL) ---
        st.markdown("### 5. Tiempos (Formato 24h)")
        ahora = datetime.now()

        # BLOQUE INICIO
        st.write("Hora Inicio:")
        # Usamos columnas muy estrechas para que quepan en una fila de celular
        hi1, hi_sep, hi2, hi_space = st.columns([2, 1, 2, 5])
        with hi1:
            h_ini = st.number_input("H_I", 0, 23, ahora.hour, 1, format="%02d", label_visibility="collapsed")
        with hi_sep:
            st.markdown('<p class="sep-reloj">:</p>', unsafe_allow_html=True)
        with hi2:
            m_ini = st.number_input("M_I", 0, 59, ahora.minute, 1, format="%02d", label_visibility="collapsed")

        # BLOQUE FIN
        st.write("Hora Fin:")
        hf1, hf_sep, hf2, hf_space = st.columns([2, 1, 2, 5])
        with hf1:
            h_fin = st.number_input("H_F", 0, 23, ahora.hour, 1, format="%02d", label_visibility="collapsed")
        with hf_sep:
            st.markdown('<p class="sep-reloj">:</p>', unsafe_allow_html=True)
        with hf2:
            m_fin = st.number_input("M_F", 0, 59, ahora.minute, 1, format="%02d", label_visibility="collapsed")

        enviar = st.form_submit_button("Guardar Reporte", type="primary", use_container_width=True)

    if enviar:
        if not id_responsable or not celda:
            st.error("⚠️ Falta ID o Celda")
        else:
            hora_inicio = time(h_ini, m_ini)
            hora_fin = time(h_fin, m_fin)
            dt_ini = datetime.combine(date.today(), hora_inicio)
            dt_fin = datetime.combine(date.today(), hora_fin)
            if dt_fin < dt_ini: dt_fin += timedelta(days=1)
            tiempo_muerto = int((dt_fin - dt_ini).total_seconds() / 60)
            
            fila = [date.today().isocalendar()[1], date.today().strftime("%Y-%m-%d"), turno, id_responsable, 
                    ", ".join(apoyo_seleccionado), celda, robot, seleccion_completa, "", desc_trabajo, 
                    acciones, "", "", "", "", tiempo_muerto, ""]
            
            hoja = conectar_google_sheet()
            if hoja:
                hoja.append_row(fila)
                st.balloons()
                st.success(f"✅ Guardado: {tiempo_muerto} min")

elif menu == "📊 Estadísticas":
    st.title("📊 Indicadores")
    # ... resto del código ...
