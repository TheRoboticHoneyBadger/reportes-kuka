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

# --- FUNCIÓN INTELIGENTE PARA LEER NÚMEROS COMO HORA ---
def interpretar_numero(numero_input):
    """Convierte un número entero (ej: 2145) en una hora (21:45)."""
    if numero_input is None:
        return datetime.now().time()
    
    # Convertimos el número a texto (ej: 2145 -> "2145")
    texto = str(int(numero_input)).zfill(4) # Rellena con ceros si es necesario (ej: 900 -> 0900)
    
    try:
        # Tomamos los primeros 2 dígitos como Hora y los últimos 2 como Minutos
        horas = int(texto[:2])
        minutos = int(texto[2:])
        
        # Validaciones básicas
        if horas > 23: horas = 23
        if minutos > 59: minutos = 59
            
        return time(horas, minutos)
    except:
        return datetime.now().time()

# --- CARGA DE DATOS LOCALES ---
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
        
        col_area = next((c for c in df_catalogo.columns if "AREA" in c), df_catalogo.columns[0] if not df_catalogo.empty else "None")
        areas = df_catalogo[col_area].unique() if not df_catalogo.empty else []
        area_sel = col_cat1.selectbox("Área", areas)
        
        tipos = []
        col_tipo = next((c for c in df_catalogo.columns if "TIPO" in c), df_catalogo.columns[1] if not df_catalogo.empty else "None")
        
        if not df_catalogo.empty:
            df_filtrado_area = df_catalogo[df_catalogo[col_area] == area_sel]
            tipos = df_filtrado_area[col_tipo].unique()
        tipo_sel = col_cat2.selectbox("Tipo de Falla", tipos)

        lista_opciones = ["Sin datos"]
        col_codigo = "None"
        col_submodo = "None"

        if not df_catalogo.empty and len(tipos) > 0:
            df_final = df_filtrado_area[df_filtrado_area[col_tipo] == tipo_sel]
            col_codigo = next((c for c in df_final.columns if "CODIGO" in c), df_final.columns[2])
            col_submodo = next((c for c in df_final.columns if "SUB" in c or "MODO" in c or "DESC" in c), df_final.columns[-1])
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

        # --- SECCIÓN 5: TIEMPOS (TECLADO NUMÉRICO) ---
        st.subheader("5. Tiempos")
        st.caption("Escribe la hora en formato 24h sin dos puntos (Ej: escribe 1430 para las 14:30)")
        
        t1, t2 = st.columns(2)
        
        # Obtenemos hora actual como número (ej: 1430)
        ahora = datetime.now()
        valor_defecto = int(ahora.strftime("%H%M"))
        
        with t1:
            # step=1 y format="%d" fuerzan el teclado numérico
            num_ini = st.number_input("Hora Inicio", value=valor_defecto, step=1, min_value=0, max_value=2359, format="%d")
        with t2:
            num_fin = st.number_input("Hora Fin", value=valor_defecto, step=1, min_value=0, max_value=2359, format="%d")
            
        # Convertimos esos números a objetos de tiempo reales para el cálculo
        h_inicio = interpretar_numero(num_ini)
        h_fin = interpretar_numero(num_fin)
        
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
            df.columns = df.columns.str.strip().str.upper()
            
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
                col_code = next((c for c in df.columns if "CODIGO" in c), None)
                if col_code:
                    st.plotly_chart(px.pie(df, names=col_code), use_container_width=True)

            st.dataframe(df.tail(5))
        else:
            st.info("Sin datos.")
