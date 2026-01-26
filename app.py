import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta, time
import gspread
import plotly.express as px
import os

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Mantenimiento KUKA", page_icon="🤖", layout="wide")

# --- CSS AVANZADO PARA RELOJ HORIZONTAL EN MÓVIL ---
st.markdown("""
    <style>
    /* Evita que las columnas se amontonen en móviles */
    [data-testid="column"] {
        width: fit-content !important;
        flex: unset !important;
        min-width: unset !important;
    }
    /* Alinea el contenido de la fila de forma horizontal siempre */
    [data-testid="stHorizontalBlock"] {
        align-items: center !important;
        gap: 0px !important;
    }
    /* Ajuste para los inputs numéricos pequeños */
    .stNumberInput input {
        width: 70px !important;
        font-size: 18px !important;
        text-align: center !important;
    }
    /* Estilo de los dos puntos */
    .reloj-sep {
        padding: 0 10px;
        font-size: 24px;
        font-weight: bold;
        line-height: 1;
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

    with st.form("form_reporte"):
        st.markdown("### 1. Datos Generales")
        id_resp = st.text_input("No. Control Responsable", max_chars=5)
        
        # Corrección de nombre de columna basada en tu KeyError
        col_nom = 'NOMBRE' if 'NOMBRE' in df_tecnicos.columns else df_tecnicos.columns[1]
        lista_tec = df_tecnicos[col_nom].unique().tolist() if not df_tecnicos.empty else []
        apoyo = st.multiselect("Personal de Apoyo", lista_tec)
        turno = st.selectbox("Turno", ["Mañana", "Tarde", "Noche"])

        st.markdown("### 2. Ubicación")
        c_u1, c_u2 = st.columns(2)
        celda = c_u1.text_input("Celda")
        robot = c_u2.text_input("Robot")
        
        st.markdown("### 3. Falla")
        # Lógica de catálogo dinámica
        col_a = next((c for c in df_catalogo.columns if "AREA" in c), "AREA")
        area_sel = st.selectbox("Área", df_catalogo[col_a].unique() if not df_catalogo.empty else [])
        
        col_t = next((c for c in df_catalogo.columns if "TIPO" in c), "TIPO")
        df_f = df_catalogo[df_catalogo[col_a] == area_sel] if not df_catalogo.empty else pd.DataFrame()
        tipo_sel = st.selectbox("Tipo de Falla", df_f[col_t].unique() if not df_f.empty else [])

        # Selección de código
        lista_f = ["Sin datos"]
        if not df_f.empty:
            df_final = df_f[df_f[col_t] == tipo_sel]
            c_cod = next((c for c in df_final.columns if "CODIGO" in c), df_final.columns[0])
            c_sub = next((c for c in df_final.columns if "SUB" in c or "MODO" in c), df_final.columns[-1])
            lista_f = df_final[c_cod] + " - " + df_final[c_sub]
        
        falla_sel = st.selectbox("Código Específico", lista_f)

        st.markdown("### 4. Ejecución")
        desc = st.text_area("Descripción")
        acc = st.text_area("Acciones")

        # --- SECCIÓN DE TIEMPOS MEJORADA ---
        st.markdown("### 5. Tiempos (24h)")
        ahora = datetime.now()

        # INICIO
        st.write("Hora Inicio:")
        c_hi, c_si, c_mi = st.columns([2, 1, 2])
        with c_hi:
            h_i = st.number_input("HI", 0, 23, ahora.hour, 1, format="%02d", label_visibility="collapsed")
        with c_si:
            st.markdown('<div class="reloj-sep">:</div>', unsafe_allow_html=True)
        with c_mi:
            m_i = st.number_input("MI", 0, 59, ahora.minute, 1, format="%02d", label_visibility="collapsed")

        # FIN
        st.write("Hora Fin:")
        c_hf, c_sf, c_mf = st.columns([2, 1, 2])
        with c_hf:
            h_f = st.number_input("HF", 0, 23, ahora.hour, 1, format="%02d", label_visibility="collapsed")
        with c_sf:
            st.markdown('<div class="reloj-sep">:</div>', unsafe_allow_html=True)
        with c_mf:
            m_f = st.number_input("MF", 0, 59, ahora.minute, 1, format="%02d", label_visibility="collapsed")

        enviar = st.form_submit_button("Guardar Reporte", type="primary", use_container_width=True)

    if enviar:
        if not id_resp or not celda:
            st.error("⚠️ Datos incompletos")
        else:
            t_ini = datetime.combine(date.today(), time(h_i, m_i))
            t_fin = datetime.combine(date.today(), time(h_f, m_f))
            if t_fin < t_ini: t_fin += timedelta(days=1)
            minutos = int((t_fin - t_ini).total_seconds() / 60)
            
            fila = [date.today().isocalendar()[1], date.today().strftime("%Y-%m-%d"), turno, id_resp, 
                    ", ".join(apoyo), celda, robot, falla_sel, "", desc, acc, "", "", "", "", minutos, ""]
            
            h = conectar_google_sheet()
            if h:
                h.append_row(fila)
                st.balloons()
                st.success(f"✅ Guardado: {minutos} min")

elif menu == "📊 Estadísticas":
    st.title("📊 Indicadores")
