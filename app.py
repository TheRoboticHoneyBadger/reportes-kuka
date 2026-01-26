import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta, time
import gspread
import plotly.express as px
import os

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Mantenimiento KUKA", page_icon="🤖", layout="wide")

# --- CSS DEFINITIVO PARA RELOJ HORIZONTAL ---
st.markdown("""
    <style>
    /* Mantiene las columnas del reloj unidas en una fila en móvil */
    [data-testid="column"] {
        width: fit-content !important;
        flex: unset !important;
        min-width: unset !important;
    }
    [data-testid="stHorizontalBlock"] {
        align-items: center !important;
        gap: 5px !important;
        display: flex !important;
        flex-direction: row !important;
    }
    /* Estiliza los cuadros numéricos para que parezcan reloj */
    .stNumberInput input {
        width: 65px !important;
        height: 45px !important;
        font-size: 20px !important;
        font-weight: bold !important;
        text-align: center !important;
        border-radius: 8px !important;
    }
    .reloj-sep {
        font-size: 28px;
        font-weight: bold;
        padding-bottom: 5px;
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
        df_tec.columns = df_tec.columns.str.strip().str.upper()
        return df_cat, df_tec
    except:
        return pd.DataFrame(), pd.DataFrame()

df_catalogo, df_tecnicos = cargar_datos()

# --- BARRA LATERAL ---
st.sidebar.title("🔧 Menú")
menu = st.sidebar.radio("Ir a:", ["📝 Nuevo Reporte", "📊 Estadísticas"])

if menu == "📝 Nuevo Reporte":
    # ENCABEZADO
    col_l, col_t = st.columns([1, 4])
    with col_l:
        if os.path.exists("logo.png"):
            st.image("logo.png", width=70)
        else:
            st.image("https://cdn-icons-png.flaticon.com/512/8636/8636080.png", width=50)
    with col_t:
        st.subheader("Reporte de fallas de mantenimiento")

    with st.form("form_reporte", clear_on_submit=False):
        st.markdown("### 1. Datos Generales")
        id_resp = st.text_input("No. Control Responsable", max_chars=5)
        
        col_nom = next((c for c in df_tecnicos.columns if "NOMBRE" in c), df_tecnicos.columns[1] if not df_tecnicos.empty else "NOMBRE")
        lista_tec = df_tecnicos[col_nom].unique().tolist() if not df_tecnicos.empty else []
        apoyo = st.multiselect("Personal de Apoyo", lista_tec)
        turno = st.selectbox("Turno", ["Mañana", "Tarde", "Noche"])

        st.markdown("### 2. Ubicación")
        c_u1, c_u2 = st.columns(2)
        celda = c_u1.text_input("Celda")
        robot = c_u2.text_input("Robot")
        
        st.markdown("### 3. Falla")
        col_a = next((c for c in df_catalogo.columns if "AREA" in c), "AREA")
        area_sel = st.selectbox("Área", df_catalogo[col_a].unique() if not df_catalogo.empty else [])
        
        col_t = next((c for c in df_catalogo.columns if "TIPO" in c), "TIPO")
        df_f = df_catalogo[df_catalogo[col_a] == area_sel] if not df_catalogo.empty else pd.DataFrame()
        tipo_sel = st.selectbox("Tipo de Falla", df_f[col_t].unique() if not df_f.empty else [])

        lista_f = ["Sin datos"]
        if not df_f.empty:
            df_final = df_f[df_f[col_t] == tipo_sel]
            c_cod = next((c for c in df_final.columns if "CODIGO" in c), df_final.columns[0])
            c_sub = next((c for c in df_final.columns if "SUB" in c or "MODO" in c), df_final.columns[-1])
            lista_f = df_final[c_cod] + " - " + df_final[c_sub]
        
        falla_sel = st.selectbox("Código Específico", lista_f)

        st.markdown("### 4. Ejecución")
        desc = st.text_area("Descripción (Síntoma)")
        acc = st.text_area("Acciones Correctivas")

        # --- SECCIÓN DE TIEMPOS (RELOJ DIGITAL) ---
        st.markdown("### 5. Tiempos (24h)")
        ahora = datetime.now()

        st.write("Hora Inicio:")
        c_hi, c_si, c_mi = st.columns([1, 1, 1])
        with c_hi:
            h_i = st.number_input("HI", 0, 23, ahora.hour, 1, format="%02d", label_visibility="collapsed")
        with c_si:
            st.markdown('<div class="reloj-sep">:</div>', unsafe_allow_html=True)
        with c_mi:
            m_i = st.number_input("MI", 0, 59, ahora.minute, 1, format="%02d", label_visibility="collapsed")

        st.write("Hora Fin:")
        c_hf, c_sf, c_mf = st.columns([1, 1, 1])
        with c_hf:
            h_f = st.number_input("HF", 0, 23, ahora.hour, 1, format="%02d", label_visibility="collapsed")
        with c_sf:
            st.markdown('<div class="reloj-sep">:</div>', unsafe_allow_html=True)
        with c_mf:
            m_f = st.number_input("MF", 0, 59, ahora.minute, 1, format="%02d", label_visibility="collapsed")

        enviar = st.form_submit_button("Guardar Reporte", type="primary", use_container_width=True)

    if enviar:
        # VALIDACIÓN DE TIEMPO
        t_ini = datetime.combine(date.today(), time(h_i, m_i))
        t_fin = datetime.combine(date.today(), time(h_f, m_f))
        
        # Si la hora de fin es menor a la de inicio, asumimos cambio de día (turno noche)
        if t_fin < t_ini:
            t_fin += timedelta(days=1)
        
        minutos = int((t_fin - t_ini).total_seconds() / 60)

        if not id_resp or not celda or not robot:
            st.error("⚠️ Datos incompletos: Asegúrate de llenar ID, Celda y Robot.")
        elif minutos == 0 and t_ini == t_fin:
            st.warning("⚠️ La hora de inicio y fin son iguales. ¿Es correcto?")
        else:
            fila = [date.today().isocalendar()[1], date.today().strftime("%Y-%m-%d"), turno, id_resp, 
                    ", ".join(apoyo), celda, robot, falla_sel, "", desc, acc, "", "", "", "", minutos, ""]
            
            h = conectar_google_sheet()
            if h:
                h.append_row(fila)
                st.balloons()
                st.success(f"✅ Reporte guardado con éxito. Tiempo total: {minutos} minutos.")

elif menu == "📊 Estadísticas":
    st.title("📊 Indicadores de Mantenimiento")
    # (El código de estadísticas se mantiene igual)
