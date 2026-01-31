import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta, time
import gspread
import plotly.express as px
import os

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Mantenimiento Magna", page_icon="🏭", layout="wide")

# --- CONTROL DE ESTADO ---
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

# --- DETECTOR DE TURNO AUTOMÁTICO ---
def obtener_turno_actual():
    hora = datetime.now().hour
    if 6 <= hora < 14:
        return "☀️ Mañana"
    elif 14 <= hora < 22:
        return "🌤️ Tarde"
    else:
        return "🌙 Noche"

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
# 📝 NUEVO REPORTE
# ==========================================
if menu == "📝 Nuevo Reporte":
    st.image("logo.png" if os.path.exists("logo.png") else "https://cdn-icons-png.flaticon.com/512/8636/8636080.png", width=300)
    st.title("Reporte de fallas de mantenimiento")
    st.markdown("---")

    if st.session_state['reporte_enviado']:
        st.success("✅ ¡Reporte guardado exitosamente!")
        st.balloons()
        if st.button("📝 INGRESAR OTRO REPORTE", type="primary", use_container_width=True):
            st.session_state['reporte_enviado'] = False
            st.rerun()

    else:
        if not df_catalogo.empty and not df_tecnicos.empty and not df_celdas_robots.empty:
            
            # 1. DATOS GENERALES
            c1, c2, c3 = st.columns(3)
            with c1:
                num_orden = st.text_input("Número de Orden:", max_chars=5)
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

            # 2. UBICACIÓN Y TURNO
            c_t, c_c, c_r = st.columns(3)
            
            # Turno Automático
            turno_sugerido = obtener_turno_actual()
            turno_label = c_t.select_slider("Turno:", options=["☀️ Mañana", "🌤️ Tarde", "🌙 Noche"], value=turno_sugerido)
            mapa_turno = {"☀️ Mañana": 1, "🌤️ Tarde": 2, "🌙 Noche": 3}
            turno_valor = mapa_turno[turno_label]

            cc_cel, cc_rob = df_celdas_robots.columns[0], df_celdas_robots.columns[1]
            celda_sel = c_c.selectbox("Celda:", sorted(df_celdas_robots[cc_cel].unique()))
            lista_robots = sorted(df_celdas_robots[df_celdas_robots[cc_cel] == celda_sel][cc_rob].tolist())
            robot_sel = c_r.selectbox("Robot:", lista_robots)

            # ESTATUS
            st.write("**Estatus de la Reparación**")
            estatus_label = st.select_slider("Avance:", options=["🛑 Sin Avance", "⏳ En Proceso", "✅ Cerrado"], value="✅ Cerrado")
            mapa_estatus = {"🛑 Sin Avance": 0, "⏳ En Proceso": 1, "✅ Cerrado": 2}
            estatus_valor = mapa_estatus[estatus_label]

            st.markdown("---")
            
            # 3. FALLA
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

            # 4. TIEMPOS (RELOJ 24H CORREGIDO)
            st.write("**Tiempos de Paro (24 Horas)**")
            t1, t2 = st.columns(2)
            
            # Hora actual limpia (sin segundos)
            now = datetime.now().replace(second=0, microsecond=0)
            hora_inicio_default = now.time()
            hora_fin_default = (now + timedelta(minutes=5)).time()
            
            # AGREGAMOS step=60 PARA PERMITIR SELECCIÓN MINUTO A MINUTO
            t_ini = t1.time_input("Hora Inicio:", value=hora_inicio_default, step=60)
            t_fin = t2.time_input("Hora Fin:", value=hora_fin_default, step=60)

            # Cálculo de diferencia
            dt_i_calc = datetime.combine(date.today(), t_ini)
            dt_f_calc = datetime.combine(date.today(), t_fin)
            
            # Si la hora fin es menor a inicio, asumimos que pasó la medianoche
            if dt_f_calc < dt_i_calc: 
                dt_f_calc += timedelta(days=1)
            
            minutos_calc = int((dt_f_calc - dt_i_calc).total_seconds() / 60)
            
            if minutos_calc > 0:
                st.info(f"⏱️ Tiempo de paro: **{minutos_calc} minutos**")
            elif minutos_calc == 0:
                st.warning("⚠️ 0 minutos (Hora inicio y fin son iguales)")
            else:
                st.error("⚠️ Error en cálculo de tiempo")

            # === ZONA DE CAPTURA ===
            with st.form("form_final"):
                sintoma = st.text_area("Actividad / Notas del Técnico (Manual):", height=80)
                accion = st.text_area("Solución / Acciones Correctivas (Manual):", height=80)
                st.markdown("---")
                foto = st.file_uploader("📂 Subir Evidencia (Foto de Galería)", type=["jpg", "png", "jpeg"])
                enviar = st.form_submit_button("GUARDAR REPORTE", type="primary", use_container_width=True)

            if enviar:
                if not id_resp or not num_orden:
                    st.error("⚠️ Faltan datos: Número de Orden o ID Responsable.")
                else:
                    evidencia = "SÍ" if foto is not None else "NO"
                    nombre_final = nom_resp if nom_resp else id_resp
                    
                    codigo_final = seleccion_completa
                    descripcion_final = "Descripción no disponible"
                    if " - " in seleccion_completa:
                        partes = seleccion_completa.split(" - ", 1)
                        codigo_final = partes[0]
                        descripcion_final = partes[1]

                    # --- FILA FINAL ---
                    fila = [
                        date.today().isocalendar()[1],      # 1. SEMANA
                        date.today().strftime("%Y-%m-%d"),  # 2. FECHA
                        turno_valor,                        # 3. TURNO
                        nombre_final,                       # 4. RESPONSABLE
                        ", ".join(apoyo),                   # 5. APOYO
                        celda_sel,                          # 6. CELDA
                        robot_sel,                          # 7. ROBOT
                        codigo_final,                       # 8. CÓDIGO
                        tipo_sel,                           # 9. TIPO
                        descripcion_final,                  # 10. DESCRIPCIÓN
                        sintoma,                            # 11. ACTIVIDAD
                        accion,                             # 12. SOLUCIÓN
                        num_orden,                          # 13. ORDEN
                        estatus_valor,                      # 14. ESTATUS
                        minutos_calc,                       # 15. TIEMPO
                        evidencia                           # 16. EVIDENCIA
                    ]

                    hoja = conectar_google_sheet()
                    if hoja:
                        hoja.append_row(fila)
                        st.session_state['reporte_enviado'] = True
                        st.rerun()
        else:
            st.error("⚠️ Error: Faltan archivos CSV.")

# ==========================================
# 📊 ESTADÍSTICAS
# ==========================================
elif menu == "📊 Estadísticas":
    st.title("📊 Indicadores de Mantenimiento")
    hoja = conectar_google_sheet()
    
    if hoja:
        filas = hoja.get_all_values()
        if len(filas) > 1:
            df = pd.DataFrame(filas[1:], columns=[
                "SEMANA", "FECHA", "TURNO", "RESPONSABLE", "APOYO", 
                "CELDA", "ROBOT", "CODIGO", "TIPO_FALLA", "DESCRIPCION", 
                "ACTIVIDAD", "SOLUCION", "ORDEN", "ESTATUS", "TIEMPO", "EVIDENCIA"
            ])
            
            df["TIEMPO"] = pd.to_numeric(df["TIEMPO"], errors='coerce').fillna(0)
            df["ESTATUS"] = df["ESTATUS"].astype(str)
            abiertos = len(df[df["ESTATUS"].isin(["0", "1"])])

            total_fallas = len(df)
            total_tiempo = int(df["TIEMPO"].sum())

            k1, k2, k3 = st.columns(3)
            k1.metric("Total Reportes", total_fallas)
            k2.metric("Tiempo Muerto Total", f"{total_tiempo} min")
            k3.metric("Reportes Abiertos", abiertos, delta_color="inverse")
            
            st.markdown("---")
            
            tab1, tab2, tab3 = st.tabs(["🤖 Por Robot", "📊 Estatus y Turno", "🧩 Top Fallas"])
            
            with tab1:
                df_robot = df.groupby("ROBOT")["TIEMPO"].sum().reset_index().sort_values("TIEMPO", ascending=False)
                fig1 = px.bar(df_robot, x="ROBOT", y="TIEMPO", title="Tiempo Muerto por Robot", color="TIEMPO", color_continuous_scale="Reds")
                st.plotly_chart(fig1, use_container_width=True)
            
            with tab2:
                c_est, c_turn = st.columns(2)
                with c_est:
                    df["ESTATUS_TXT"] = df["ESTATUS"].map({
                        "0": "🛑 Sin Avance", "1": "⏳ En Proceso", "2": "✅ Cerrado"
                    }).fillna("Desconocido")
                    df_est = df["ESTATUS_TXT"].value_counts().reset_index()
                    df_est.columns = ["ESTATUS", "CANTIDAD"]
                    fig2 = px.pie(df_est, names="ESTATUS", values="CANTIDAD", title="Estatus", hole=0.4,
                                  color="ESTATUS", color_discrete_map={
                                      "🛑 Sin Avance": "red", "⏳ En Proceso": "orange", "✅ Cerrado": "green"
                                  })
                    st.plotly_chart(fig2, use_container_width=True)
                with c_turn:
                    df["TURNO_TXT"] = df["TURNO"].astype(str).map({
                        "1": "Mañana", "2": "Tarde", "3": "Noche"
                    }).fillna("Desconocido")
                    df_tur = df["TURNO_TXT"].value_counts().reset_index()
                    df_tur.columns = ["TURNO", "CANTIDAD"]
                    fig_tur = px.bar(df_tur, x="TURNO", y="CANTIDAD", title="Por Turno", color="TURNO")
                    st.plotly_chart(fig_tur, use_container_width=True)
            
            with tab3:
                df["FALLA_TXT"] = df["CODIGO"] + " - " + df["DESCRIPCION"]
                top_fallas = df["FALLA_TXT"].value_counts().head(5).reset_index()
                top_fallas.columns = ["FALLA", "CANTIDAD"]
                fig3 = px.bar(top_fallas, x="CANTIDAD", y="FALLA", orientation='h', title="Top 5 Fallas", color="CANTIDAD")
                st.plotly_chart(fig3, use_container_width=True)
        else:
            st.info("📊 Esperando datos...")
