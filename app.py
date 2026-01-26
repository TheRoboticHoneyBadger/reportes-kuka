import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta, time
import gspread
import plotly.express as px

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

# --- CARGA DE DATOS LOCALES ---
@st.cache_data
def cargar_datos():
    try:
        df_cat = pd.read_csv('catalogo_fallas.csv')
        # LIMPIEZA AUTOMÁTICA DE COLUMNAS (Para evitar el KeyError)
        # Quita espacios al inicio/final y convierte a mayúsculas
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

# ==========================================
# 📝 SECCIÓN: REPORTE DE FALLAS
# ==========================================
if menu == "📝 Nuevo Reporte":
    st.title("📝 Reporte de Mantenimiento")
    st.markdown("---")

    with st.form("form_reporte"):
        
        # --- SECCIÓN 1: DATOS GENERALES ---
        st.subheader("1. Datos Generales")
        c1, c2, c3 = st.columns(3)
        
        id_responsable = c1.text_input("No. Control Responsable", max_chars=5)
        responsable = ""
        if id_responsable and not df_tecnicos.empty:
            user = df_tecnicos[df_tecnicos['ID'] == id_responsable]
            if not user.empty:
                responsable = user.iloc[0]['Nombre']
                c1.success(f"👤 {responsable}")
            else:
                c1.error("❌ ID no encontrado")
        
        lista_nombres = df_tecnicos['Nombre'].unique().tolist() if not df_tecnicos.empty else []
        apoyo_seleccionado = c2.multiselect("Personal de Apoyo", lista_nombres)
        apoyo = ", ".join(apoyo_seleccionado)
        
        turno = c3.selectbox("Turno", ["Mañana", "Tarde", "Noche"])

        # --- SECCIÓN 2: UBICACIÓN Y ORDEN ---
        st.subheader("2. Ubicación y Orden")
        u1, u2, u3, u4, u5 = st.columns(5)
        
        celda = u1.text_input("Celda")
        robot = u2.text_input("Robot")
        no_orden = u3.text_input("No. de Orden")
        tipo_orden = u4.selectbox("Tipo de Orden", ["Correctivo", "Preventivo", "Mejora", "Falla Menor"])
        status = u5.selectbox("Status", ["Cerrada", "Abierta", "Pendiente de Refacción"])

        # --- SECCIÓN 3: DETALLE DE LA FALLA ---
        st.subheader("3. Detalle de la Falla")
        
        col_cat1, col_cat2 = st.columns(2)
        
        # Usamos .get para evitar error si la columna no existe
        col_area = 'AREA' if 'AREA' in df_catalogo.columns else df_catalogo.columns[0]
        areas = df_catalogo[col_area].unique() if not df_catalogo.empty else []
        area_sel = col_cat1.selectbox("Área", areas)
        
        tipos = []
        col_tipo = 'TIPO' if 'TIPO' in df_catalogo.columns else df_catalogo.columns[1]
        
        if not df_catalogo.empty:
            df_filtrado_area = df_catalogo[df_catalogo[col_area] == area_sel]
            tipos = df_filtrado_area[col_tipo].unique()
        tipo_sel = col_cat2.selectbox("Tipo de Falla", tipos)

        lista_opciones = ["Sin datos"]
        if not df_catalogo.empty and len(tipos) > 0:
            df_final = df_filtrado_area[df_filtrado_area[col_tipo] == tipo_sel]
            
            # Buscamos las columnas correctas aunque tengan nombres raros
            col_codigo = 'CODIGO DE FALLO' if 'CODIGO DE FALLO' in df_final.columns else df_final.columns[2]
            # Buscamos algo que se parezca a SUB MODO
            cols_posibles = [c for c in df_final.columns if "SUB" in c or "MODO" in c]
            col_submodo = cols_posibles[0] if cols_posibles else df_final.columns[-2] # Fallback
            
            lista_opciones = df_final[col_codigo] + " - " + df_final[col_submodo]
        
        seleccion_completa = st.selectbox("Seleccione el Código Específico", lista_opciones)
        
        codigo_guardar = ""
        falla_guardar = ""
        if " - " in seleccion_completa:
            partes = seleccion_completa.split(" - ", 1)
            codigo_guardar = partes[0]
            falla_guardar = partes[1]
        else:
            codigo_guardar = seleccion_completa
            falla_guardar = seleccion_completa

        # --- SECCIÓN 4: TRABAJO REALIZADO ---
        st.subheader("4. Ejecución")
        desc_trabajo = st.text_area("Descripción del Trabajo (Síntoma)")
        acciones = st.text_area("Acciones Correctivas / Actividad")
        solucion = st.text_area("Solución Final")

        # --- SECCIÓN 5: TIEMPOS (NUEVO FORMATO: RODILLOS) ---
        st.subheader("5. Tiempos")
        st.caption("Selecciona Hora y Minutos por separado")
        
        # Fila para HORA INICIO
        col_h1, col_m1, col_sep, col_h2, col_m2 = st.columns([1, 1, 0.5, 1, 1])
        
        with col_h1:
            st.markdown("**Inicio:**")
            h_ini_val = st.selectbox("Hora (Ini)", range(24), key="h_i")
        with col_m1:
            st.markdown("&nbsp;") # Espacio vacío para alinear
            m_ini_val = st.selectbox("Min (Ini)", range(60), key="m_i")
            
        # Fila para HORA FIN
        with col_h2:
            st.markdown("**Fin:**")
            h_fin_val = st.selectbox("Hora (Fin)", range(24), key="h_f", index=min(h_ini_val, 23))
        with col_m2:
            st.markdown("&nbsp;")
            m_fin_val = st.selectbox("Min (Fin)", range(60), key="m_f")

        # Construimos los objetos de tiempo reales
        h_inicio = time(h_ini_val, m_ini_val)
        h_fin = time(h_fin_val, m_fin_val)
        
        comentario = st.text_input("Comentario Adicional")

        enviar = st.form_submit_button("Guardar Reporte", type="primary")

    if enviar:
        if not responsable:
            st.error("⚠️ Falta validar al Responsable.")
        elif not celda or not robot:
            st.warning("⚠️ Indica Celda y Robot.")
        else:
            fecha_hoy = date.today()
            semana = fecha_hoy.isocalendar()[1]
            dt_ini = datetime.combine(fecha_hoy, h_inicio)
            dt_fin = datetime.combine(fecha_hoy, h_fin)
            if dt_fin < dt_ini: dt_fin += timedelta(days=1)
            tiempo_muerto = int((dt_fin - dt_ini).total_seconds() / 60)

            fila = [
                semana, fecha_hoy.strftime("%Y-%m-%d"), turno, responsable, apoyo,
                celda, robot, codigo_guardar, falla_guardar, desc_trabajo,
                acciones, solucion, no_orden, tipo_orden, status, tiempo_muerto, comentario
            ]

            hoja = conectar_google_sheet()
            if hoja:
                hoja.append_row(fila)
                st.balloons()
                st.success(f"✅ Guardado. Tiempo: {tiempo_muerto} min")

# ==========================================
# 📊 SECCIÓN: ESTADÍSTICAS
# ==========================================
elif menu == "📊 Estadísticas":
    st.title("📊 Indicadores")
    hoja = conectar_google_sheet()
    
    if hoja:
        data = hoja.get_all_records()
        if len(data) > 0:
            df = pd.DataFrame(data)
            
            if 'TIEMPO MUERTO' in df.columns:
                df['TIEMPO MUERTO'] = pd.to_numeric(df['TIEMPO MUERTO'], errors='coerce').fillna(0)
                total_tm = df['TIEMPO MUERTO'].sum()
            else:
                total_tm = 0

            k1, k2 = st.columns(2)
            k1.metric("Reportes", len(df))
            k2.metric("Tiempo Muerto", f"{int(total_tm)} min")
            
            tab1, tab2 = st.tabs(["Por Robot", "Por Falla"])
            with tab1:
                if 'ROBOT' in df.columns:
                    st.plotly_chart(px.bar(df, x='ROBOT', y='TIEMPO MUERTO', color='CELDA'), use_container_width=True)
            with tab2:
                # Buscamos columna de Código
                col_code = 'CODIGO DE FALLO' if 'CODIGO DE FALLO' in df.columns else df.columns[7]
                if col_code in df.columns:
                    st.plotly_chart(px.pie(df, names=col_code), use_container_width=True)

            st.dataframe(df.tail(5))
        else:
            st.info("Sin datos.")
