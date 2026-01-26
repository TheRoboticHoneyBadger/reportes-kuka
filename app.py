import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
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
        # Intento 1: Lectura estándar
        df_cat = pd.read_csv('catalogo_fallas.csv')
        
        # TRUCO: Si detecta solo 1 columna, seguro es porque el separador es punto y coma (Excel latino)
        if len(df_cat.columns) < 2:
            df_cat = pd.read_csv('catalogo_fallas.csv', sep=';', encoding='latin-1')

        # Limpieza CRÍTICA: Quitamos espacios vacíos en los nombres de las columnas
        # Ejemplo: "AREA " se convierte en "AREA"
        df_cat.columns = df_cat.columns.str.strip()
        
        # Convertimos todo a texto para evitar errores de números
        df_cat = df_cat.astype(str)
        
        # Cargamos técnicos
        df_tec = pd.read_csv('tecnicos.csv', dtype={'ID': str})
        
        return df_cat, df_tec

    except Exception as e:
        # ESTO ES LO NUEVO: Si falla, te mostrará el error exacto en pantalla roja
        st.error(f"⚠️ Error cargando archivo: {e}")
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
        
        # Validación de Responsable (Sigue igual, por ID para seguridad)
        id_responsable = c1.text_input("No. Control Responsable", max_chars=5)
        responsable = ""
        if id_responsable and not df_tecnicos.empty:
            user = df_tecnicos[df_tecnicos['ID'] == id_responsable]
            if not user.empty:
                responsable = user.iloc[0]['Nombre']
                c1.success(f"👤 {responsable}")
            else:
                c1.error("❌ ID no encontrado")
        
        # CAMBIO AQUÍ: Personal de Apoyo ahora es una lista desplegable
        # 1. Obtenemos la lista de nombres del archivo tecnicos.csv
        lista_nombres = df_tecnicos['Nombre'].unique().tolist() if not df_tecnicos.empty else []
        
        # 2. Creamos un selector múltiple (puedes elegir uno o varios)
        apoyo_seleccionado = c2.multiselect("Personal de Apoyo", lista_nombres)
        
        # 3. Convertimos la lista de seleccionados a un texto simple (ej: "Juan, Pedro") para guardarlo
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

        # --- SECCIÓN 3: DETALLE DE LA FALLA (VISUALIZACIÓN LIMPIA) ---
        st.subheader("3. Detalle de la Falla")
        
        col_cat1, col_cat2 = st.columns(2)
        
        # 1. Filtro por AREA
        areas = df_catalogo['AREA'].unique() if not df_catalogo.empty else []
        area_sel = col_cat1.selectbox("Área", areas)
        
        # 2. Filtro por TIPO
        tipos = []
        if not df_catalogo.empty:
            df_filtrado_area = df_catalogo[df_catalogo['AREA'] == area_sel]
            tipos = df_filtrado_area['TIPO'].unique()
        tipo_sel = col_cat2.selectbox("Tipo de Falla", tipos)

        # 3. Selección Final (Solo CÓDIGO y DESCRIPCIÓN)
        lista_opciones = ["Sin datos"]
        if not df_catalogo.empty and len(tipos) > 0:
            df_final = df_filtrado_area[df_filtrado_area['TIPO'] == tipo_sel]
            
            # AQUI ESTÁ EL CAMBIO: Concatenamos solo "CODIGO - SUB MODO"
            # Asumiendo que 'SUB MODO DE FALLA' es la descripción específica que quieres ver
            lista_opciones = df_final['CODIGO DE FALLO'] + " - " + df_final['SUB MODO DE FALLA']
        
        seleccion_completa = st.selectbox("Seleccione el Código Específico", lista_opciones)
        
        # Lógica para separar y guardar (Actualizada para el nuevo formato con guión)
        codigo_guardar = ""
        falla_guardar = ""
        
        if " - " in seleccion_completa:
            # Separamos por el primer guión que encontremos
            partes = seleccion_completa.split(" - ", 1)
            codigo_guardar = partes[0]
            falla_guardar = partes[1] # Esto guardará la descripción específica
        else:
            codigo_guardar = seleccion_completa
            falla_guardar = seleccion_completa
            
        # --- SECCIÓN 4: TRABAJO REALIZADO ---
        st.subheader("4. Ejecución")
        desc_trabajo = st.text_area("Descripción del Trabajo (Síntoma)")
        acciones = st.text_area("Acciones Correctivas / Actividad")
        solucion = st.text_area("Solución Final")

        # --- SECCIÓN 5: TIEMPOS ---
        st.subheader("5. Tiempos")
        t1, t2 = st.columns(2)
        h_inicio = t1.time_input("Hora Inicio", datetime.now().time())
        h_fin = t2.time_input("Hora Fin", datetime.now().time())
        
        comentario = st.text_input("Comentario Adicional")

        enviar = st.form_submit_button("Guardar Reporte", type="primary")

    if enviar:
        if not responsable:
            st.error("⚠️ Falta validar al Responsable.")
        elif not celda or not robot:
            st.warning("⚠️ Indica Celda y Robot.")
        else:
            # Cálculos
            fecha_hoy = date.today()
            semana = fecha_hoy.isocalendar()[1]
            dt_ini = datetime.combine(fecha_hoy, h_inicio)
            dt_fin = datetime.combine(fecha_hoy, h_fin)
            if dt_fin < dt_ini: dt_fin += timedelta(days=1)
            tiempo_muerto = int((dt_fin - dt_ini).total_seconds() / 60)

            # Fila a guardar (17 Columnas)
            fila = [
                semana,
                fecha_hoy.strftime("%Y-%m-%d"),
                turno,
                responsable,
                apoyo,
                celda,
                robot,
                codigo_guardar,   # Columna H
                falla_guardar,    # Columna I
                desc_trabajo,
                acciones,
                solucion,
                no_orden,
                tipo_orden,
                status,
                tiempo_muerto,
                comentario
            ]

            hoja = conectar_google_sheet()
            if hoja:
                hoja.append_row(fila)
                st.balloons()
                st.success(f"✅ Reporte guardado. Semana: {semana} | Tiempo: {tiempo_muerto} min")

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
            
            # Convertir Tiempo Muerto a número (por si acaso viene como texto)
            if 'TIEMPO MUERTO' in df.columns:
                df['TIEMPO MUERTO'] = pd.to_numeric(df['TIEMPO MUERTO'], errors='coerce').fillna(0)
                total_tm = df['TIEMPO MUERTO'].sum()
            else:
                total_tm = 0

            k1, k2, k3 = st.columns(3)
            k1.metric("Total Reportes", len(df))
            k2.metric("Tiempo Muerto Total", f"{int(total_tm)} min")
            k3.metric("Semana", date.today().isocalendar()[1])
            
            # Gráficas
            tab1, tab2 = st.tabs(["Por Robot", "Por Tipo de Falla"])
            
            with tab1:
                if 'ROBOT' in df.columns:
                    fig = px.bar(df, x='ROBOT', y='TIEMPO MUERTO', color='CELDA', title="Tiempo Muerto por Robot")
                    st.plotly_chart(fig, use_container_width=True)
            
            with tab2:
                # Ahora usamos 'CODIGO DE FALLO' que es la columna H del Excel
                if 'CODIGO DE FALLO' in df.columns:
                    fig2 = px.pie(df, names='CODIGO DE FALLO', title="Frecuencia de Códigos")
                    st.plotly_chart(fig2, use_container_width=True)

            st.dataframe(df.tail(5))
        else:

            st.info("Sin datos.")


