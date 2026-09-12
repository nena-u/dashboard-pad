# ============================================================
# Dashboard: Oportunidad y Demanda en Atención Domiciliaria (PAD)
# Preguntas que responde:
#   1) ¿Dónde está la brecha frente a la meta de 2 días de oportunidad?
#   2) ¿Los picos de demanda coinciden con el incumplimiento?
# ============================================================

# ===== PASO 1: IMPORTS =====
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, html, dcc, Input, Output, callback
import dash_bootstrap_components as dbc

# ===== PASO 2: CARGA Y PREPARACIÓN DE DATOS =====

# Cargamos el Excel directamente desde la misma carpeta donde está este script
df = pd.read_excel('dataset_1.xlsx')

# Limpiamos espacios sobrantes en los nombres de columna
df.columns = df.columns.str.strip()

# Convertimos las columnas de fecha (texto) a formato datetime real
date_cols = ['FECHA DE NACIMIENTO', 'FECHA DE INGRESO AL PROGRAMA',
             'FECHA DE PRESTACION DEL SERVICIO', 'FECHA DE EGRESO']
for c in date_cols:
    df[c] = pd.to_datetime(df[c], errors='coerce')

# Eliminamos columnas que no se usan en este análisis:
# TELEFONO no aporta a ningún gráfico; FECHA DE EGRESO tiene casi todo nulo
df = df.drop(columns=['TELEFONO', 'FECHA DE EGRESO'], errors='ignore')

# Estandarizamos texto (minúsculas, sin espacios) para que los filtros no dupliquen categorías
cat_cols = ['SERVICIO REQUERIDO', 'EPS', 'REGIMEN', 'GENERO', 'TIPO DE DOC', 'RANGO DE EDADES',
            'SISTEMA', 'CE10 PRINCIPAL', 'DIAGNOSTIC DE INGRESO', 'MUNICIPIO', 'BARRIO', 'ESTADO']
for c in cat_cols:
    df[c] = df[c].astype(str).str.strip().str.lower()

# Quitamos filas duplicadas exactas
df = df.drop_duplicates()

# Calculamos la OPORTUNIDAD_DIAS (días entre ingreso y primera atención) -> clave para la Pregunta 1
df['OPORTUNIDAD_DIAS'] = (df['FECHA DE PRESTACION DEL SERVICIO'] - df['FECHA DE INGRESO AL PROGRAMA']).dt.days
df['CUMPLE_META'] = df['OPORTUNIDAD_DIAS'] <= 2  # la meta del negocio es máximo 2 días

# Creamos variables temporales -> clave para la Pregunta 2
df['SEMANA'] = df['FECHA DE INGRESO AL PROGRAMA'].dt.to_period('W').dt.start_time
df['MES'] = df['FECHA DE INGRESO AL PROGRAMA'].dt.to_period('M').dt.to_timestamp()
dias_es = {0: 'Lunes', 1: 'Martes', 2: 'Miércoles', 3: 'Jueves', 4: 'Viernes', 5: 'Sábado', 6: 'Domingo'}
df['DIA_SEMANA'] = df['FECHA DE INGRESO AL PROGRAMA'].dt.dayofweek.map(dias_es)

print(f"Dataset listo: {df.shape[0]} registros, {df.shape[1]} columnas")

# ===== PASO 3: INSTANCIA DE LA APP + LAYOUT =====
app = Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])

def kpi_card(titulo, valor_id, color, icono):
    return dbc.Card(dbc.CardBody([
        html.Div(icono, style={"fontSize": "1.5rem"}),
        html.P(titulo, className="text-muted mb-1 mt-1", style={"fontSize": "0.85rem"}),
        html.H3("---", id=valor_id, className=f"text-{color} fw-bold")  # placeholder inicial
    ]), className="shadow-sm text-center h-100")

app.layout = dbc.Container([

    # Fila 1: título y subtítulo
    dbc.Row([
        dbc.Col([
            html.H2("🏥 Oportunidad y Demanda en Atención Domiciliaria", className="mt-3 mb-0"),
            html.P("Análisis para la toma de decisiones — Programa de Atención Domiciliaria (PAD)",
                   className="text-muted")
        ])
    ]),
    html.Hr(),

    # Fila 2: filtros interactivos
    dbc.Row([
        dbc.Col([html.Label("📅 Rango de fecha de ingreso", className="fw-bold"),
                 dcc.DatePickerRange(id="filtro-fechas",
                                     start_date=df["FECHA DE INGRESO AL PROGRAMA"].min(),
                                     end_date=df["FECHA DE INGRESO AL PROGRAMA"].max(),
                                     display_format="DD/MM/YYYY")], width=4),
        dbc.Col([html.Label("🏢 EPS", className="fw-bold"),
                 dcc.Dropdown(id="filtro-eps",
                              options=[{"label": e.title(), "value": e} for e in sorted(df["EPS"].unique())],
                              multi=True, placeholder="Todas")], width=4),
        dbc.Col([html.Label("🩺 Servicio requerido", className="fw-bold"),
                 dcc.Dropdown(id="filtro-servicio",
                              options=[{"label": s.title(), "value": s} for s in sorted(df["SERVICIO REQUERIDO"].unique())],
                              multi=True, placeholder="Todos")], width=4),
    ], className="mb-4"),

    # Fila 3: las 4 tarjetas KPI
    dbc.Row([
        dbc.Col(kpi_card("Oportunidad promedio", "kpi-oportunidad", "primary", "⏱️"), width=3),
        dbc.Col(kpi_card("Cumplimiento de meta (≤2 días)", "kpi-cumple", "success", "✅"), width=3),
        dbc.Col(kpi_card("Servicio más crítico", "kpi-peor", "danger", "⚠️"), width=3),
        dbc.Col(kpi_card("Ingresos en el periodo", "kpi-total", "info", "👥"), width=3),
    ], className="mb-4"),

    # Fila 4: gráficos de la Pregunta 1
    dbc.Card([
        dbc.CardHeader(html.H4("📊 Pregunta 1: ¿Dónde está la brecha frente a la meta de 2 días?", className="mb-0")),
        dbc.CardBody([
            dbc.Row([
                dbc.Col(dcc.Graph(id="grafico-barras-servicio"), width=6),
                dbc.Col(dcc.Graph(id="grafico-boxplot-servicio"), width=6),
            ]),
            html.P(id="insight-barras", className="text-muted fst-italic small mt-1"),
            dcc.Graph(id="grafico-heatmap-servicio-eps"),
        ])
    ], className="mb-4 shadow-sm"),

    # Fila 5: gráficos de la Pregunta 2
    dbc.Card([
        dbc.CardHeader(html.H4("📈 Pregunta 2: ¿Los picos de demanda coinciden con el incumplimiento?", className="mb-0")),
        dbc.CardBody([
            dcc.Graph(id="grafico-combinado-semana"),
            html.P(id="insight-semana", className="text-muted fst-italic small mt-1"),
            dcc.Graph(id="grafico-heatmap-dia-mes"),
        ])
    ], className="mb-4 shadow-sm"),

], fluid=True, style={"backgroundColor": "#f8f9fa", "padding": "20px"})

# ===== PASO 4: CALLBACK (4 KPIs + 5 gráficos + 2 frases-hallazgo) =====
@callback(
    Output("kpi-oportunidad", "children"), Output("kpi-cumple", "children"),
    Output("kpi-peor", "children"), Output("kpi-total", "children"),
    Output("grafico-barras-servicio", "figure"), Output("grafico-boxplot-servicio", "figure"),
    Output("grafico-heatmap-servicio-eps", "figure"), Output("grafico-combinado-semana", "figure"),
    Output("grafico-heatmap-dia-mes", "figure"),
    Output("insight-barras", "children"), Output("insight-semana", "children"),
    Input("filtro-fechas", "start_date"), Input("filtro-fechas", "end_date"),
    Input("filtro-eps", "value"), Input("filtro-servicio", "value"),
)
def actualizar(start_date, end_date, eps_sel, servicio_sel):
    # 1) Filtramos el DataFrame según lo seleccionado en los filtros
    dff = df[(df["FECHA DE INGRESO AL PROGRAMA"] >= start_date) & (df["FECHA DE INGRESO AL PROGRAMA"] <= end_date)]
    if eps_sel:
        dff = dff[dff["EPS"].isin(eps_sel)]
    if servicio_sel:
        dff = dff[dff["SERVICIO REQUERIDO"].isin(servicio_sel)]

    # 2) Calculamos los 4 KPIs
    oport_prom = round(dff["OPORTUNIDAD_DIAS"].mean(), 1) if len(dff) else 0
    pct_cumple = round(dff["CUMPLE_META"].mean() * 100, 1) if len(dff) else 0
    peor = dff.groupby("SERVICIO REQUERIDO")["OPORTUNIDAD_DIAS"].mean().idxmax().title() if len(dff) else "N/A"
    total = len(dff)

    # 3) Gráfico de barras horizontales: oportunidad promedio por servicio
    resumen = dff.groupby("SERVICIO REQUERIDO")["OPORTUNIDAD_DIAS"].mean().sort_values().reset_index()
    resumen["SERVICIO REQUERIDO"] = resumen["SERVICIO REQUERIDO"].str.title()
    fig1 = px.bar(resumen, x="OPORTUNIDAD_DIAS", y="SERVICIO REQUERIDO", orientation="h",
                  title="Oportunidad promedio por servicio (línea roja = meta de 2 días)",
                  labels={"OPORTUNIDAD_DIAS": "Días promedio", "SERVICIO REQUERIDO": ""},
                  color="OPORTUNIDAD_DIAS", color_continuous_scale="RdYlGn_r")
    fig1.add_vline(x=2, line_dash="dash", line_color="red", line_width=2)
    fig1.update_layout(coloraxis_showscale=False)

    # 4) Boxplot: dispersión de oportunidad por servicio
    dff_box = dff.copy()
    dff_box["SERVICIO REQUERIDO"] = dff_box["SERVICIO REQUERIDO"].str.title()
    fig2 = px.box(dff_box, x="SERVICIO REQUERIDO", y="OPORTUNIDAD_DIAS", title="Dispersión de oportunidad por servicio")
    fig2.update_xaxes(tickangle=45)
    fig2.add_hline(y=2, line_dash="dash", line_color="red")

    # 5) Heatmap: cruce Servicio x EPS
    pivot = dff.pivot_table(index="SERVICIO REQUERIDO", columns="EPS", values="OPORTUNIDAD_DIAS", aggfunc="mean")
    pivot.index = pivot.index.str.title()
    pivot.columns = pivot.columns.str.title()
    fig3 = px.imshow(pivot, text_auto=".1f", aspect="auto", color_continuous_scale="RdYlGn_r",
                      title="Mapa de calor: Oportunidad promedio por Servicio y EPS")

    # 6) Combinado: volumen de ingresos (barras) + % de incumplimiento (línea) por semana
    resumen_sem = dff.groupby("SEMANA").agg(
        volumen=("OPORTUNIDAD_DIAS", "count"),
        pct_incumple=("CUMPLE_META", lambda x: (1 - x.mean()) * 100)
    ).reset_index()
    fig4 = go.Figure()
    fig4.add_bar(x=resumen_sem["SEMANA"], y=resumen_sem["volumen"], name="Volumen de ingresos", marker_color="#2E75B6")
    fig4.add_trace(go.Scatter(x=resumen_sem["SEMANA"], y=resumen_sem["pct_incumple"], name="% Incumplimiento",
                               yaxis="y2", mode="lines+markers", line=dict(color="#E63946", width=3)))
    fig4.update_layout(title="Volumen de ingresos vs % de incumplimiento (por semana)",
                        yaxis=dict(title="Volumen de ingresos"),
                        yaxis2=dict(title="% Incumplimiento", overlaying="y", side="right"),
                        legend=dict(orientation="h", y=1.15))

    # 7) Heatmap: día de la semana x mes
    orden_dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    pivot2 = dff.pivot_table(index="DIA_SEMANA", columns="MES", values="OPORTUNIDAD_DIAS", aggfunc="count").reindex(orden_dias)
    fig5 = px.imshow(pivot2, aspect="auto", color_continuous_scale="Blues", text_auto=True,
                      title="Volumen de ingresos: Día de la semana x Mes")

    # 8) Frases-hallazgo automáticas
    insight_barras = (f"💡 '{resumen.iloc[-1]['SERVICIO REQUERIDO']}' tiene la mayor oportunidad promedio "
                       f"({resumen.iloc[-1]['OPORTUNIDAD_DIAS']:.1f} días), superando la meta por "
                       f"{resumen.iloc[-1]['OPORTUNIDAD_DIAS']-2:.1f} días.")
    semana_pico = resumen_sem.loc[resumen_sem['volumen'].idxmax()]
    insight_semana = (f"💡 La semana del {semana_pico['SEMANA'].strftime('%d/%m')} tuvo el mayor volumen "
                       f"({int(semana_pico['volumen'])} ingresos) con un {semana_pico['pct_incumple']:.0f}% de incumplimiento.")

    return (f"{oport_prom} días", f"{pct_cumple}%", peor, f"{total}",
            fig1, fig2, fig3, fig4, fig5, insight_barras, insight_semana)

# ===== PASO 5: EJECUCIÓN =====
# Exponemos el servidor Flask interno de Dash: Render/gunicorn lo necesitan para desplegar en internet
server = app.server

if __name__ == '__main__':
    app.run(debug=True)
