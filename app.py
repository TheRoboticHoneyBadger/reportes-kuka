import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta, time
import gspread
import os

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Mantenimiento Magna", page_icon="🏭", layout="wide")

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
        
        # Limpieza básica
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

# --- CONFIGURACIÓN INTELIGENTE DE COLUMNAS ---
if not df_catalogo.empty:
    cols = df_catalogo.columns.tolist()
    
    # Detección automática
    idx_area = next((i for i, c in enumerate(cols) if any(x in c for x in ['AREA', 'UBICACION'])), 0)
    idx_tipo = next((i for i, c in enumerate(cols) if any(x in c for x in ['TIPO', 'CAT']) and i != idx_area), 1)
    idx_cod = next((i for i, c in enumerate(cols) if any(x in c for x in ['COD', 'ID', 'NUM'])), 2)
    idx_desc = next((i for i, c in enumerate(cols) if any(x in c for x in ['SUB', 'MODO', 'DESC', 'SINTOMA', 'DETALLE'])), len(cols)-1)

    with st.sidebar.expander("⚙️ Ajustar Columnas (Si los textos salen mal)", expanded=False):
        c_area = st.selectbox("Columna ÁREA", cols, index=idx_area)
        c_tipo = st.selectbox("Columna TIPO", cols, index=idx_tipo)
        c_cod = st.selectbox("Columna CÓDIGO", cols, index=idx_cod)
        c_desc = st.selectbox("Columna DESCRIPCIÓN", cols, index=idx_desc)
else:
    c_area, c_tipo, c_cod, c_desc = "", "", "", ""


if menu == "📝 Nuevo Reporte":
    st.image("logo.png" if os.path.exists("logo.png") else "https://cdn-icons-png.flaticon.com/512/8636/8636080.png", width=300)
    st.title("Reporte de fallas de mantenimiento")
    st.markdown("---")

    if not df_catalogo.empty and not df_tecnicos.empty and not df_celdas_robots.empty:
        
        # === ZONA INTERACTIVA (FUERA DEL FORMULARIO) ===
        
        # 1. IDENTIFICACIÓN
        c1, c2 = st.columns(2)
        with c1:
            id_resp = st.text_input("Número de control responsable:", max_chars=5)
            col_id_t, col_nom_t = df_tecnicos.columns[0], df_tecnicos.columns[1]
            nom_resp = ""
            if id_resp:
                m = df_tecnicos[df_tecnicos[col_id_t] == id_resp]
                if not m.empty:
                    nom_resp = m[col_nom_t].iloc[0]
                    st.success(f"👤 Técnico: {nom_resp}")
                else:
                    st.warning("⚠️ ID no encontrado")

        with c2:
            apoyo = st.multiselect("Personal de Apoyo:", sorted(df_tecnicos[col_nom_t].tolist()))

        # 2. UBICACIÓN
        c3, c4, c5 = st.columns(3)
        turno = c3.selectbox("Turno:", ["Mañana", "Tarde", "Noche"])
        
        cc_cel, cc_rob = df_celdas_robots.columns[0], df_celdas_robots.columns[1]
        
        celda_sel = c4.selectbox("Celda:", sorted(df_celdas_robots[cc_cel].unique()))
        
        lista_robots = sorted(df_celdas_robots[df_celdas_robots[cc_cel] == celda_sel][cc_rob].tolist())
        robot_sel = c5.selectbox("Robot:", lista_robots)

        st.write("**Prioridad de la Falla**")
        prioridad = st.select_slider("Gravedad:", options=["🟢 Baja", "🟡 Media", "🔴 Alta / Crítica"], value="🟡 Media")

        st.markdown("---")
        st.subheader("🛠️ Detalles de la Falla")

        # 3. FALLA CON DEFAULT "MANTENIMIENTO"
        areas_disp = sorted(df_catalogo[c_area].unique())
        
        # --- LÓGICA DE DEFAULT ---
        # Buscamos el índice de "MANTENIMIENTO" en la lista
        index_default = 0
        try:
            # Busca cualquier coincidencia que contenga "MANTENIMIENTO" (mayus/minus)
            index_default = next(i for i, x in enumerate(areas_disp) if "MANTENIMIENTO" in str(x).upper())
        except StopIteration:
            index_default = 0 # Si no existe, usa el primero
            
        area_sel = st.selectbox("Área:", areas_disp, index=index_default)
        # -------------------------
        
        tipos_disp = sorted(df_catalogo[df_catalogo[c_area] == area_sel][c_tipo].unique())
        tipo_sel = st.selectbox("Tipo de Falla:", tipos_disp)
        
        df_f = df_catalogo[(df_catalogo[c_area] == area_sel) & (df_catalogo[c_tipo] == tipo_sel)]
        
        opciones_falla = []
        if not df_f.empty:
            opciones_falla = (df_f[c_cod].astype(str) + " - " + df_f[c_desc].astype(str)).tolist()
        else:
            opciones_falla = ["No hay códigos para esta selección"]
            
        seleccion_completa = st.selectbox("Código y Descripción de Falla:", opciones_falla)


        # === ZONA DE CAPTURA (DENTRO DEL FORMULARIO) ===
        with st.form("form_final"):
            sintoma = st.text_area("Notas Adicionales del Técnico (Opcional):", height=80)
            accion = st.text_area("Acción Correctiva:", height=80)

            st.write("**Tiempos (HHMM)**")
            t1, t2 = st.columns(2)
            ahora = int(datetime.now().strftime("%H%M"))
            num_ini = t1.number_input("Hora Inicio:", value=ahora, step=1)
            num_fin = t2.number_input("Hora Fin:", value=ahora, step=1)

            st.markdown("---")
            foto = st.camera_input("📸 Evidencia (Opcional)")

            enviar = st.form_submit_button("GUARDAR REPORTE", type="primary", use_container_width=True)

        if enviar:
            if not id_resp:
                st.error("⚠️ Falta número de control.")
            else:
                h_i, h_f = convertir_a_hora(num_ini), convertir_a_hora(num_fin)
                dt_i, dt_f = datetime.combine(date.today(), h_i), datetime.combine(date.today(), h_f)
                if dt_f < dt_i: dt_f += timedelta(days=1)
                minutos = int((dt_f - dt_i).total_seconds() / 60)
                
                evidencia = "SÍ" if foto is not None else "NO"
                nombre_final = nom_resp if nom_resp else id_resp

                fila = [
                    date.today().isocalendar()[1], date.today().strftime("%Y-%m-%d"), turno,
                    nombre_final, ", ".join(apoyo), celda_sel, robot_sel, 
                    seleccion_completa,
                    prioridad,
                    sintoma,
                    accion, "", "", "", evidencia, minutos, ""
                ]

                hoja = conectar_google_sheet()
                if hoja:
                    hoja.append_row(fila)
                    st.balloons()
                    st.success(f"✅ Guardado. T.Muerto: {minutos} min")

    else:
        st.error("⚠️ Error: Faltan archivos CSV en GitHub.")

elif menu == "📊 Estadísticas":
    st.title("📊 Indicadores")
    # Estadísticas se mantienen igual
