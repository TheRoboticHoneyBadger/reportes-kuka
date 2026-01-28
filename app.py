import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta, time
import gspread
import plotly.express as px
import os

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Mantenimiento Magna", page_icon="🏭", layout="wide")

# --- CONTROL DE ESTADO (SESSION STATE) ---
# Esto evita duplicados. Si no existe la variable, la creamos.
if 'reporte_enviado' not in st.session_state:
    st.session_state['reporte_enviado'] = False

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

# --- CONFIGURACIÓN DE COLUMNAS ---
if not df_catalogo.empty:
    cols = df_catalogo.columns.tolist()
    idx_area = next((i for i, c in enumerate(cols) if any(x in c for x in ['AREA', 'UBICACION'])), 0)
    idx_tipo = next((i for i, c in enumerate(cols) if any(x in c for x in ['TIPO', 'CAT']) and i != idx_area), 1)
    idx_cod = next((i for i, c in enumerate(cols) if any(x in c for x in ['COD', 'ID', 'NUM'])), 2)
    idx_desc = next((i for i, c in enumerate(cols) if any(x in c for x in ['SUB', 'MODO', 'DESC', 'SINTOMA', 'DETALLE'])), len(cols)-1)

    with st.sidebar.expander("⚙️ Ajustar Columnas", expanded=False):
        c_area = st.selectbox("Columna ÁREA", cols, index=idx_area)
        c_tipo = st.selectbox("Columna TIPO", cols, index=idx_tipo)
        c_cod = st.selectbox("Columna CÓDIGO", cols, index=idx_cod)
        c_desc = st.selectbox("Columna DESCRIPCIÓN", cols, index=idx_desc)
else:
    c_area, c_tipo, c_cod, c_desc = "", "", "", ""


# ==========================================
# 📝 LÓGICA DE NUEVO REPORTE (CON ANTI-DUPLICADOS)
# ==========================================
if menu == "📝 Nuevo Reporte":
    st.image("logo.png" if os.path.exists("logo.png") else "https://cdn-icons-png.flaticon.com/512/8636/8636080.png", width=300)
    st.title("Reporte de fallas de mantenimiento")
    st.markdown("---")

    # --- PANTALLA DE ÉXITO (BLOQUEA EL FORMULARIO) ---
    if st.session_state['reporte_enviado']:
        st.success("✅ ¡Reporte enviado y guardado correctamente en la base de datos!")
        st.balloons()
        
        st.info("El formulario se ha bloqueado para evitar duplicados.")
        
        # Botón para reiniciar
        if st.button("📝 INGRESAR OTRO REPORTE", type="primary", use_container_width=True):
            st.session_state['reporte_enviado'] = False
            st.rerun() # Recarga la página limpia

    # --- FORMULARIO NORMAL (SOLO SI NO SE HA ENVIADO) ---
    else:
        if not df_catalogo.empty and not df_tecnicos.empty and not df_celdas_robots.empty:
            
            # === ZONA INTERACTIVA ===
            c1, c2, c3 = st.columns(3)
            with c1:
                num_orden = st.text_input("Número de Orden:", max_chars=5, help="5 dígitos obligatorios")
            with c2:
                id_resp = st.text_input("No. Control Responsable:", max_chars=5)
                col_id_t, col_nom_t = df_tecnicos.columns[0], df_tecnicos.columns[1]
                nom_resp = ""
                if id_resp:
                    m = df_tecnicos[df_tecnicos[col_id_t] == id_resp]
                    if not m.empty:
                        nom_resp = m[col_nom_t].iloc[0]
                        st.success(f"👤 {nom_resp}")
                    else:
                        st.warning("⚠️ ID no encontrado")
            with c3:
                apoyo = st.multiselect("Personal de Apoyo:", sorted(df_tecnicos[col_nom_t].tolist()))

            # UBICACIÓN
            c_t, c_c, c_r = st.columns(3)
            turno = c_t.selectbox("Turno:", ["Mañana", "Tarde", "Noche"])
            cc_cel, cc_rob = df_celdas_robots.columns[0], df_celdas_robots.columns[1]
            celda_sel = c_c.selectbox("Celda:", sorted(df_celdas_robots[cc_cel].unique()))
            lista_robots = sorted(df_celdas_robots[df_celdas_robots[cc_cel] == celda_sel][cc_rob].tolist())
            robot_sel = c_r.selectbox("Robot:", lista_robots)

            st.write("**Prioridad de la Falla**")
            prioridad = st.select_slider("Gravedad:", options=["🟢 Baja", "🟡 Media", "🔴 Alta / Crítica"], value="🟡 Media")

            st.markdown("---")
            
            # FALLA
            areas_disp = sorted(df_catalogo[c_area].unique())
            index_default = 0
            try:
                index_default = next(i for i, x in enumerate(areas_disp) if "MANTENIMIENTO" in str(x).upper())
            except StopIteration:
                index_default = 0
                
            area_sel = st.selectbox("Área:", areas_disp, index=index_default)
            tipos_disp = sorted(df_catalogo[df_catalogo[c_area] == area_sel][c_tipo].unique())
            tipo_sel = st.selectbox("Tipo de Falla:", tipos_disp)
            
            df_f = df_catalogo[(df_catalogo[c_area] == area_sel) & (df_catalogo[c_tipo] == tipo_sel)]
            opciones_falla = (df_f[c_cod].astype(str) + " - " + df_f[c_desc].astype(str)).tolist() if not df_f.empty else ["Sin datos"]
            seleccion_completa = st.selectbox("Código y Descripción de Falla:", opciones_falla)

            # TIEMPOS
            st.write("**Tiempos de Paro (HHMM)**")
            t1, t2 = st.columns(2)
            ahora_hhmm = int(datetime.now().strftime("%H%M"))
            num_ini = t1.number_input("Hora Inicio:", value=ahora_hhmm, step=1)
            num_fin = t2.number_input("Hora Fin:", value=ahora_hhmm, step=1)

            h_i_calc, h_f_calc = convertir_a_hora(num_ini), convertir_a_hora(num_fin)
            dt_i_calc = datetime.combine(date.today(), h_i_calc)
            dt_f_calc = datetime.combine(date.today(), h_f_calc)
            if dt_f_calc < dt_i_calc: dt_f_calc += timedelta(days=1)
            minutos_calc = int((dt_f_calc - dt_i_calc).total_seconds() / 60)
            
            if minutos_calc > 0:
                st.info(f"⏱️ Tiempo de paro: **{minutos_calc} minutos**")
            elif minutos_calc == 0:
                st.warning("⚠️ 0 min")
            else:
                st.error("⚠️ Error en tiempos")

            # === ZONA DE CAPTURA ===
            with st.form("form_final"):
                sintoma = st.text_area("Notas Adicionales del Técnico (Opcional):", height=80)
                accion = st.text_area("Acción Correctiva (Solución):", height=80)
                st.markdown("---")
                foto = st.file_uploader("📂 Subir Evidencia (Foto de Galería)", type=["jpg", "png", "jpeg"])
                enviar = st.form_submit_button("GUARDAR REPORTE", type="primary", use_container_width=True)

            if enviar:
                if not id_resp or not num_orden:
                    st.error("⚠️ Faltan datos obligatorios: Número de Orden o ID Responsable.")
                else:
                    evidencia = "SÍ" if foto is not None else "NO"
                    nombre_final = nom_resp if nom_resp else id_resp

                    fila = [
                        date.today().isocalendar()[1], date.today().strftime("%Y-%m-%d"), turno,
                        nombre_final, ", ".join(apoyo), celda_sel, robot_sel, 
                        seleccion_completa,
                        prioridad,
                        sintoma,
                        accion, 
                        "", # Columna L vacía
                        num_orden, # Columna M (Orden)
                        "", evidencia, minutos_calc, ""
                    ]

                    hoja = conectar_google_sheet()
                    if hoja:
                        hoja.append_row(fila)
                        # --- AQUÍ ACTIVAMOS EL ESTADO DE "ENVIADO" ---
                        st.session_state['reporte_enviado'] = True
                        st.rerun() # Recargamos para mostrar la pantalla de éxito
        else:
            st.error("⚠️ Error: Faltan archivos CSV en GitHub.")

# ==========================================
# 📊 SECCIÓN DE ESTADÍSTICAS
# ==========================================
elif menu == "📊 Estadísticas":
    st.title("📊 Indicadores de Mantenimiento")
    hoja = conectar_google_sheet()
    
    if hoja:
        filas = hoja.get_all_values()
        if len(filas) > 1:
            df = pd.DataFrame(filas[1:], columns=[
                "SEMANA", "FECHA", "TURNO", "TECNICO", "APOYO", 
                "CELDA", "ROBOT", "FALLA", "PRIORIDAD", "SINTOMA", 
                "ACCION", "VACIO", "ORDEN", "R3", "EVIDENCIA", "TIEMPO", "EXTRA"
            ])
            
            df["TIEMPO"] = pd.to_numeric(df["TIEMPO"], errors='coerce').fillna(0)

            total_fallas = len(df)
            total_tiempo = int(df["TIEMPO"].sum())
            if "PRIORIDAD" in df.columns:
                criticas = len(df[df["PRIORIDAD"].astype(str).str.contains("🔴", na=False)])
            else:
                criticas = 0

            k1, k2, k3 = st.columns(3)
            k1.metric("Total Reportes", total_fallas)
            k2.metric("Tiempo Muerto Total", f"{total_tiempo} min")
            k3.metric("Fallas Críticas", criticas)
            
            st.markdown("---")
            
            tab1, tab2, tab3 = st.tabs(["🤖 Por Robot", "🔥 Por Prioridad", "🧩 Top Fallas"])
            
            with tab1:
                df_robot = df.groupby("ROBOT")["TIEMPO"].sum().reset_index().sort_values("TIEMPO", ascending=False)
                fig1 = px.bar(df_robot, x="ROBOT", y="TIEMPO", title="Tiempo Muerto por Robot", color="TIEMPO", color_continuous_scale="Reds")
                st.plotly_chart(fig1, use_container_width=True)
            
            with tab2:
                if "PRIORIDAD" in df.columns:
                    df_prio = df["PRIORIDAD"].value_counts().reset_index()
                    df_prio.columns = ["PRIORIDAD", "CANTIDAD"]
                    fig2 = px.pie(df_prio, names="PRIORIDAD", values="CANTIDAD", title="Distribución de Gravedad", hole=0.4)
                    st.plotly_chart(fig2, use_container_width=True)
            
            with tab3:
                top_fallas = df["FALLA"].value_counts().head(5).reset_index()
                top_fallas.columns = ["FALLA", "CANTIDAD"]
                fig3 = px.bar(top_fallas, x="CANTIDAD", y="FALLA", orientation='h', title="Top 5 Fallas Más Frecuentes")
                st.plotly_chart(fig3, use_container_width=True)
        else:
            st.info("📊 Esperando datos...")
