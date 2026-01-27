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
        df_c.columns = [str(c).strip().upper() for c in df_c.columns]
        df_t.columns = [str(c).strip().upper() for c in df_t.columns]
        return df_c, df_t
    except:
        return pd.DataFrame(), pd.DataFrame()

df_catalogo, df_tecnicos = cargar_datos_seguros()

# --- MENÚ LATERAL ---
st.sidebar.title("🔧 Menú")
menu = st.sidebar.radio("Ir a:", ["📝 Nuevo Reporte", "📊 Estadísticas"])

# ==========================================
# 📝 SECCIÓN: NUEVO REPORTE
# ==========================================
if menu == "📝 Nuevo Reporte":
    # Ajuste de columnas para logo más grande
    col_logo, col_tit = st.columns([1, 3])
    with col_logo:
        # Aumentamos el ancho a 120 para que destaque
        st.image("logo.png" if os.path.exists("logo.png") else "https://cdn-icons-png.flaticon.com/512/8636/8636080.png", width=120)
    with col_tit:
        st.title("Reporte de fallas de mantenimiento")

    st.markdown("---")

    if not df_catalogo.empty and not df_tecnicos.empty:
        with st.form("form_reporte"):
            c1, c2, c3 = st.columns([1, 2, 1])
            id_resp = c1.text_input("ID Responsable", max_chars=5)
            
            col_nom_tec = df_tecnicos.columns[1]
            nombres_lista = df_tecnicos[col_nom_tec].tolist()
            apoyo = c2.multiselect("Personal de Apoyo", nombres_lista)
            turno = c3.selectbox("Turno", ["Mañana", "Tarde", "Noche"])

            c4, c5 = st.columns(2)
            celda = c4.text_input("Celda")
            robot = c5.text_input("Robot")

            # SELECTORES DE FALLA
            c_area = df_catalogo.columns[0]
            c_tipo = df_catalogo.columns[1]
            c_cod  = df_catalogo.columns[2]
            c_sub  = df_catalogo.columns[3]

            area_sel = st.selectbox("Área", df_catalogo[c_area].unique())
            tipo_sel = st.selectbox("Tipo de Falla", df_catalogo[df_catalogo[c_area] == area_sel][c_tipo].unique())

            df_f = df_catalogo[(df_catalogo[c_area] == area_sel) & (df_catalogo[c_tipo] == tipo_sel)]
            opciones = (df_f[c_cod].astype(str) + " - " + df_f[c_sub].astype(str)).tolist()
            falla_sel = st.selectbox("Código de Falla", opciones)

            sintoma = st.text_area("Descripción del Síntoma", height=80)
            accion = st.text_area("Acción Realizada", height=80)

            st.write("**Tiempos (HHMM)**")
            t_c1, t_c2 = st.columns(2)
            ahora_num = int(datetime.now().strftime("%H%M"))
            num_ini = t_c1.number_input("Hora Inicio", value=ahora_num, step=1, format="%d")
            num_fin = t_c2.number_input("Hora Fin", value=ahora_num, step=1, format="%d")

            st.write(" ") 
            enviar = st.form_submit_button("GUARDAR REPORTE", type="primary", use_container_width=True)

        if enviar:
            if not id_resp or not celda:
                st.error("⚠️ ID y Celda obligatorios.")
            else:
                h_i, h_f = convertir_a_hora(num_ini), convertir_a_hora(num_fin)
                dt_i, dt_f = datetime.combine(date.today(), h_i), datetime.combine(date.today(), h_f)
                if dt_f < dt_i: dt_f += timedelta(days=1)
                minutos = int((dt_f - dt_i).total_seconds() / 60)

                col_id_tec = df_tecnicos.columns[0]
                match = df_tecnicos[df_tecnicos[col_id_tec] == id_resp]
                nombre_final = match[col_nom_tec].iloc[0] if not match.empty else id_resp

                fila = [
                    date.today().isocalendar()[1], date.today().strftime("%Y-%m-%d"), turno,
                    nombre_final, ", ".join(apoyo), celda, robot, falla_sel, "",
                    sintoma, accion, "", "", "", "", minutos, ""
                ]

                hoja = conectar_google_sheet()
                if hoja:
                    hoja.append_row(fila)
                    st.balloons()
                    st.success(f"✅ Guardado. Tiempo muerto: {minutos} min")

# ==========================================
# 📊 SECCIÓN: ESTADÍSTICAS
# ==========================================
elif menu == "📊 Estadísticas":
    st.title("📊 Indicadores de Mantenimiento")
    hoja = conectar_google_sheet()
    
    if hoja:
        data = hoja.get_all_records()
        if len(data) > 0:
            df = pd.DataFrame(data)
            df.columns = [str(c).strip().upper() for c in df.columns]
            
            col_tm = next((c for c in df.columns if "TIEMPO" in c or "MINUTOS" in c), df.columns[-2])
            df[col_tm] = pd.to_numeric(df[col_tm], errors='coerce').fillna(0)

            k1, k2 = st.columns(2)
            k1.metric("Total Reportes", len(df))
            k2.metric("Tiempo Muerto Total", f"{int(df[col_tm].sum())} min")
            
            tab1, tab2 = st.tabs(["📉 Tiempo por Robot", "🧩 Fallas Comunes"])
            
            with tab1:
                col_rob = next((c for c in df.columns if "ROBOT" in c), "ROBOT")
                fig1 = px.bar(df, x=col_rob, y=col_tm, title="Minutos por Robot")
                st.plotly_chart(fig1, use_container_width=True)
            
            with tab2:
                col_fal = next((c for c in df.columns if "FALLA" in c), "FALLA")
                fig2 = px.pie(df, names=col_fal, values=col_tm, title="Distribución de Fallas")
                st.plotly_chart(fig2, use_container_width=True)
