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
        
        # Limpieza: Mayúsculas y quitar espacios invisibles
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

# --- CONFIGURACIÓN DE COLUMNAS (LÓGICA MEJORADA) ---
if not df_catalogo.empty:
    cols = df_catalogo.columns.tolist()
    
    # 1. AREA: Busca 'AREA', 'UBICACION', 'MAQUINA'
    idx_area = next((i for i, c in enumerate(cols) if any(x in c for x in ['AREA', 'UBICACION'])), 0)
    
    # 2. TIPO: Busca 'TIPO', 'CATEGORIA' (evitando confundirse con area)
    idx_tipo = next((i for i, c in enumerate(cols) if any(x in c for x in ['TIPO', 'CAT']) and i != idx_area), 1)
    
    # 3. CÓDIGO: Busca 'COD', 'ID', 'NUM'
    idx_cod = next((i for i, c in enumerate(cols) if any(x in c for x in ['COD', 'ID', 'NUM'])), 2)
    
    # 4. DESCRIPCIÓN: Busca 'SUB', 'MODO', 'DESC', 'SINTOMA'. 
    # TRUCO: Si no encuentra, usa la ULTIMA columna, que suele ser la descripción.
    idx_desc = next((i for i, c in enumerate(cols) if any(x in c for x in ['SUB', 'MODO', 'DESC', 'SINTOMA', 'DETALLE'])), len(cols)-1)

    # Sidebar para corrección manual
    with st.sidebar.expander("⚙️ Configurar Columnas (Si sale mal)", expanded=True):
        st.caption("Si la descripción se repite, cambia la columna aquí:")
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

    # --- INSPECTOR DE DATOS (PARA QUE VEAS QUÉ ESTÁ LEYENDO) ---
    with st.expander("👀 Ver mis datos reales (Ayuda para depurar)"):
        if not df_catalogo.empty:
            st.write("Así está leyendo Python tu archivo Excel:")
            st.dataframe(df_catalogo.head(3))
            st.info(f"El programa cree que la descripción está en la columna: **{c_desc}**")
        else:
            st.error("No se cargó el archivo CSV.")

    if not df_catalogo.empty and not df_tecnicos.empty and not df_celdas_robots.empty:
        with st.form("form_reporte"):
            # 1. IDENTIFICACIÓN
            c1, c2 = st.columns(2)
            with c1:
                id_resp = st.text_input("Número de control responsable:", max_chars=5)
                ct_id, ct_nom = df_tecnicos.columns[0], df_tecnicos.columns[1]
                if id_resp:
                    m = df_tecnicos[df_tecnicos[ct_id] == id_resp]
                    if not m.empty:
                        st.success(f"👤 Técnico: {m[ct_nom].iloc[0]}")
                    else:
                        st.warning("⚠️ ID no encontrado")

            with c2:
                apoyo = st.multiselect("Personal de Apoyo:", sorted(df_tecnicos[ct_nom].tolist()))

            # 2. UBICACIÓN Y PRIORIDAD
            c3, c4, c5 = st.columns(3)
            turno = c3.selectbox("Turno:", ["Mañana", "Tarde", "Noche"])
            
            cc_cel, cc_rob = df_celdas_robots.columns[0], df_celdas_robots.columns[1]
            celda_sel = c4.selectbox("Celda:", sorted(df_celdas_robots[cc_cel].unique()))
            robots_filtrados = sorted(df_celdas_robots[df_celdas_robots[cc_cel] == celda_sel][cc_rob].tolist())
            robot_sel = c5.selectbox("Robot:", robots_filtrados)

            st.write("**Prioridad de la Falla**")
            prioridad = st.select_slider("Gravedad:", options=["🟢 Baja", "🟡 Media", "🔴 Alta / Crítica"], value="🟡 Media")

            # 3. FALLA (CORREGIDO)
            areas_disp = df_catalogo[c_area].unique()
            area_sel = st.selectbox("Área:", areas_disp)
            
            tipos_disp = df_catalogo[df_catalogo[c_area] == area_sel][c_tipo].unique()
            tipo_sel = st.selectbox("Tipo de Falla:", tipos_disp)
            
            # Filtro
            df_f = df_catalogo[(df_catalogo[c_area] == area_sel) & (df_catalogo[c_tipo] == tipo_sel)]
            
            # GENERACIÓN DE LISTA
            # Aquí forzamos que si falla la concatenación, muestre al menos algo útil
            opciones = []
            if not df_f.empty:
                try:
                    opciones = (df_f[c_cod].astype(str) + " - " + df_f[c_desc].astype(str)).tolist()
                except:
                    opciones = df_f[c_cod].astype(str).tolist()
            else:
                opciones = ["No hay fallas registradas para este tipo"]
            
            seleccion_completa = st.selectbox("Código y Descripción de Falla:", opciones)

            # 4. NOTAS
            sintoma = st.text_area("Notas Adicionales del Técnico (Opcional):", height=80)
            accion = st.text_area("Acción Correctiva:", height=80)

            # 5. TIEMPOS
            st.write("**Tiempos (HHMM)**")
            t1, t2 = st.columns(2)
            ahora = int(datetime.now().strftime("%H%M"))
            num_ini = t1.number_input("Hora Inicio:", value=ahora, step=1)
            num_fin = t2.number_input("Hora Fin:", value=ahora, step=1)

            # 6. EVIDENCIA
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
                mt = df_tecnicos[df_tecnicos[ct_id] == id_resp]
                nom_final = mt[ct_nom].iloc[0] if not mt.empty else id_resp

                fila = [
                    date.today().isocalendar()[1], date.today().strftime("%Y-%m-%d"), turno,
                    nom_final, ", ".join(apoyo), celda_sel, robot_sel, 
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

elif menu == "📊 Estadísticas":
    st.title("📊 Indicadores")
    # Código de estadísticas (se mantiene igual)
