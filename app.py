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

            # 2. UBICACIÓN
            c_t, c_c, c_r = st.columns(3)
            turno = c_t.selectbox("Turno:", ["Mañana", "Tarde", "Noche"])
            cc_cel, cc_rob = df_celdas_robots.columns[0], df_celdas_robots.columns[1]
            celda_sel = c_c.selectbox("Celda:", sorted(df_celdas_robots[cc_cel].unique()))
            lista_robots = sorted(df_celdas_robots[df_celdas_robots[cc_cel] == celda_sel][cc_rob].tolist())
            robot_sel = c_r.selectbox("Robot:", lista_robots)

            # --- NUEVA BARRA DE ESTATUS ---
            st.write("**Estatus de la Reparación**")
            estatus_label = st.select_slider(
                "Seleccione el avance:",
                options=["🛑 Sin Avance", "⏳ En Proceso", "✅ Cerrado"],
                value="✅ Cerrado" # Default en Cerrado
            )
            
            # Mapeo de Texto a Número para Excel
            mapa_estatus = {
                "🛑 Sin Avance": 0,
                "⏳ En Proceso": 1,
                "✅ Cerrado": 2
            }
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

            # 4. TIEMPOS
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
                    
                    # Separación de Código y Descripción
                    codigo_final = seleccion_completa
                    descripcion_final = "Descripción no disponible"
                    if " - " in seleccion_completa:
                        partes = seleccion_completa.split(" - ", 1)
                        codigo_final = partes[0]
                        descripcion_final = partes[1]

                    # --- FILA FINAL CON ESTATUS (VALOR NUMÉRICO) ---
                    fila = [
                        date.today().isocalendar()[1],      # 1. SEMANA
                        date.today().strftime("%Y-%m-%d"),  # 2. FECHA
                        turno,                              # 3. TURNO
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
                        estatus_valor,                      # 14. ESTATUS (0, 1, 2) - REEMPLAZA PRIORIDAD
                        evidencia,                          # 15. EVIDENCIA
                        minutos_calc                        # 16. TIEMPO MUERTO
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
            # MAPEO DE COLUMNAS ACTUALIZADO
            df = pd.DataFrame(filas[1:], columns=[
                "SEMANA", "FECHA", "TURNO", "RESPONSABLE", "APOYO", 
                "CELDA", "ROBOT", "CODIGO", "TIPO_FALLA", "DESCRIPCION", 
                "ACTIVIDAD", "SOLUCION", "ORDEN", "ESTATUS", "EVIDENCIA", "TIEMPO"
            ])
            
            df["TIEMPO"] = pd.to_numeric(df["TIEMPO"], errors='coerce').fillna(0)
            
            # KPI: Reportes Abiertos (Estatus 0 o 1)
            # Convertimos a string por si acaso viene como texto desde excel
            df["ESTATUS"] = df["ESTATUS"].astype(str)
            abiertos = len(df[df["ESTATUS"].isin(["0", "1"])])

            total_fallas = len(df)
            total_tiempo = int(df["TIEMPO"].sum())

            k1, k2, k3 = st.columns(3)
            k1.metric("Total Reportes", total_fallas)
            k2.metric("Tiempo Muerto Total", f"{total_tiempo} min")
            k3.metric("Reportes Abiertos / En Proceso", abiertos, delta_color="inverse")
            
            st.markdown("---")
            
            tab1, tab2, tab3 = st.tabs(["🤖 Por Robot", "📊 Por Estatus", "🧩 Top Fallas"])
            
            with tab1:
                df_robot = df.groupby("ROBOT")["TIEMPO"].sum().reset_index().sort_values("TIEMPO", ascending=False)
                fig1 = px.bar(df_robot, x="ROBOT", y="TIEMPO", title="Tiempo Muerto por Robot", color="TIEMPO", color_continuous_scale="Reds")
                st.plotly_chart(fig1, use_container_width=True)
            
            with tab2:
                # Mapeamos los números a texto para la gráfica
                df["ESTATUS_TXT"] = df["ESTATUS"].map({
                    "0": "🛑 Sin Avance", "1": "⏳ En Proceso", "2": "✅ Cerrado"
                }).fillna("Desconocido")
                
                df_est = df["ESTATUS_TXT"].value_counts().reset_index()
                df_est.columns = ["ESTATUS", "CANTIDAD"]
                fig2 = px.pie(df_est, names="ESTATUS", values="CANTIDAD", title="Estatus de Órdenes", hole=0.4, 
                              color="ESTATUS", color_discrete_map={
                                  "🛑 Sin Avance": "red", 
                                  "⏳ En Proceso": "orange", 
                                  "✅ Cerrado": "green"
                              })
                st.plotly_chart(fig2, use_container_width=True)
            
            with tab3:
                df["FALLA_TXT"] = df["CODIGO"] + " - " + df["DESCRIPCION"]
                top_fallas = df["FALLA_TXT"].value_counts().head(5).reset_index()
                top_fallas.columns = ["FALLA", "CANTIDAD"]
                fig3 = px.bar(top_fallas, x="CANTIDAD", y="FALLA", orientation='h', title="Top 5 Fallas Más Frecuentes")
                st.plotly_chart(fig3, use_container_width=True)
        else:
            st.info("📊 Esperando datos...")
