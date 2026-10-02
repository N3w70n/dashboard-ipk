
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from pathlib import Path

st.set_page_config(
    page_title="IPK | Monitoreo operacional",
    page_icon="🚌",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE = Path(__file__).parent
DATA = BASE / "ipk_procesado.csv"

@st.cache_data
def load_data():
    d = pd.read_csv(DATA)
    d["fecha"] = pd.to_datetime(
    d["fecha"],
    format="mixed",
    errors="coerce"
)
    d["ruta"] = d["ruta"].astype(str)
    d["mes"] = d["fecha"].dt.strftime("%Y-%m")
    return d

df = load_data()

# ---------- Helpers ----------
def weighted_ipk(x):
    km = x["kilometros"].sum()
    pax = x.loc[x["pasajeros"].notna(), "pasajeros"].sum()
    km_valid = x.loc[x["pasajeros"].notna(), "kilometros"].sum()
    return pax / km_valid if km_valid > 0 else np.nan

def aggregate_ipk(x, grain):
    g = x.groupby(grain, as_index=False).agg(
        pasajeros=("pasajeros","sum"),
        kilometros=("kilometros","sum"),
        registros=("ruta","size"),
        pasajeros_nulos=("pasajeros", lambda s: s.isna().sum()),
    )
    # Para IPK, el denominador se limita a los km cuya observación de pasajeros es válida.
    valid = x[x["pasajeros"].notna()].groupby(grain, as_index=False)["kilometros"].sum()
    valid = valid.rename(columns={"kilometros":"kilometros_ipk"})
    g = g.drop(columns=["kilometros"]).merge(valid, on=grain, how="left")
    g["ipk"] = g["pasajeros"] / g["kilometros_ipk"]
    return g

def fmt_num(v, dec=2):
    return "—" if pd.isna(v) else f"{v:,.{dec}f}"

def period_delta(curr, prev):
    if pd.isna(prev) or prev == 0 or pd.isna(curr):
        return np.nan
    return (curr / prev - 1) * 100

# ---------- Header ----------
st.title("IPK — Índice de Pasajeros por Kilómetro")
st.caption(
    "Monitoreo ejecutivo del desempeño operacional. "
    "IPK = pasajeros movilizados / kilómetros realizados."
)

# ---------- Filters ----------
with st.sidebar:
    st.header("Filtros")
    min_d, max_d = df["fecha"].min().date(), df["fecha"].max().date()
    dates = st.date_input("Rango de fechas", value=(min_d, max_d), min_value=min_d, max_value=max_d)
    if isinstance(dates, tuple) and len(dates) == 2:
        start, end = pd.Timestamp(dates[0]), pd.Timestamp(dates[1])
    else:
        start = end = pd.Timestamp(dates)

    routes = sorted(df["ruta"].dropna().unique().tolist())
    selected_routes = st.multiselect("Ruta", routes, default=routes, help="Seleccione una o varias rutas.")
    if not selected_routes:
        selected_routes = routes

    st.divider()
    st.subheader("Calidad del dato")
    st.metric("Registros", f"{len(df):,}")
    st.metric("Rutas", f"{df['ruta'].nunique():,}")
    st.metric("Pasajeros nulos", f"{df['pasajeros'].isna().sum():,}")
    st.caption("Los registros con pasajeros nulos no entran al cálculo del IPK; sus kilómetros se mantienen visibles en calidad de datos.")

mask = df["fecha"].between(start, end) & df["ruta"].isin(selected_routes)
d = df.loc[mask].copy()

if d.empty:
    st.warning("No hay datos para los filtros seleccionados.")
    st.stop()

# ---------- KPIs ----------
ipk_now = weighted_ipk(d)
pax = d["pasajeros"].sum(min_count=1)
km_total = d["kilometros"].sum()
valid_km = d.loc[d["pasajeros"].notna(),"kilometros"].sum()
missing_pct = d["pasajeros"].isna().mean()*100

# Previous period of equal length immediately before selection
period_days = (end - start).days + 1
prev_end = start - pd.Timedelta(days=1)
prev_start = prev_end - pd.Timedelta(days=period_days-1)
prev = df.loc[
    df["fecha"].between(prev_start, prev_end) &
    df["ruta"].isin(selected_routes)
]
ipk_prev = weighted_ipk(prev)
delta = period_delta(ipk_now, ipk_prev)

c1,c2,c3,c4,c5,c6 = st.columns(6)
c1.metric("IPK promedio ponderado", fmt_num(ipk_now,3), f"{delta:+.1f}% vs período anterior" if pd.notna(delta) else None)
c2.metric("IPK máximo diario", fmt_num(d.loc[d["pasajeros"].notna(),"ipk"].max(),3))
c3.metric("IPK mínimo diario", fmt_num(d.loc[d["pasajeros"].notna(),"ipk"].min(),3))
c4.metric("Pasajeros movilizados", fmt_num(pax,0))
c5.metric("Kilómetros realizados", fmt_num(km_total,0))
c6.metric("Pasajeros faltantes", f"{d['pasajeros'].isna().sum():,}", f"{missing_pct:.2f}% de registros")

st.divider()

# ---------- Main trend ----------
daily = aggregate_ipk(d, ["fecha","ruta"])
fig = px.line(
    daily, x="fecha", y="ipk", color="ruta",
    markers=False, hover_data={"ipk":":.3f","pasajeros":":,.0f","kilometros_ipk":":,.1f"},
)
fig.update_layout(
    title="Evolución diaria del IPK por ruta",
    xaxis_title=None, yaxis_title="IPK",
    legend_title="Ruta", height=470,
    margin=dict(l=10,r=10,t=55,b=10),
)
st.plotly_chart(fig, use_container_width=True)

# ---------- Route comparison ----------
left, right = st.columns([1.25, 1])

route = aggregate_ipk(d, ["ruta"]).sort_values("ipk", ascending=False)
route["vs_promedio"] = (route["ipk"]/ipk_now-1)*100

with left:
    fig2 = px.bar(
        route, x="ipk", y="ruta", orientation="h",
        color="ipk", color_continuous_scale="Blues",
        hover_data={"ipk":":.3f","pasajeros":":,.0f","kilometros_ipk":":,.1f","vs_promedio":":+.1f"},
    )
    fig2.update_layout(title="Ranking de rutas por IPK", xaxis_title="IPK", yaxis_title=None, height=560, coloraxis_showscale=False)
    st.plotly_chart(fig2, use_container_width=True)

with right:
    st.subheader("Top 5 y bottom 5")
    top5 = route.head(5)[["ruta","ipk","vs_promedio"]].copy()
    bot5 = route.tail(5).sort_values("ipk")[["ruta","ipk","vs_promedio"]].copy()
    top5.columns = ["Ruta","IPK","vs promedio"]
    bot5.columns = ["Ruta","IPK","vs promedio"]
    st.markdown("**Mayor IPK**")
    st.dataframe(top5.style.format({"IPK":"{:.3f}","vs promedio":"{:+.1f}%"}), hide_index=True, use_container_width=True)
    st.markdown("**Menor IPK**")
    st.dataframe(bot5.style.format({"IPK":"{:.3f}","vs promedio":"{:+.1f}%"}), hide_index=True, use_container_width=True)

# ---------- Monthly pattern ----------
monthly = aggregate_ipk(d, ["mes","ruta"])
monthly["mes_dt"] = pd.to_datetime(monthly["mes"])
fig3 = px.line(
    monthly.sort_values("mes_dt"), x="mes_dt", y="ipk", color="ruta",
    markers=True, hover_data={"ipk":":.3f","pasajeros":":,.0f","kilometros_ipk":":,.1f"}
)
fig3.update_layout(title="Comportamiento mensual del IPK", xaxis_title=None, yaxis_title="IPK", height=420)
st.plotly_chart(fig3, use_container_width=True)

# ---------- Automatic insights ----------
st.subheader("Observaciones automáticas")
insights = []

# Best / worst route
if len(route):
    best = route.iloc[0]
    worst = route.iloc[-1]
    insights.append(
        f"**Desempeño relativo:** {best['ruta']} presenta el IPK más alto del período ({best['ipk']:.3f}), "
        f"{best['vs_promedio']:+.1f}% frente al IPK ponderado del conjunto seleccionado. "
        "Conviene revisar sus condiciones operativas para identificar factores replicables."
    )
    insights.append(
        f"**Oportunidad de revisión:** {worst['ruta']} presenta el IPK más bajo ({worst['ipk']:.3f}), "
        f"{worst['vs_promedio']:+.1f}% frente al promedio seleccionado. "
        "Se recomienda revisar demanda, oferta kilométrica y programación antes de atribuir una causa."
    )

# Trend by route using monthly linear slope
trend_rows = []
for r in selected_routes:
    z = monthly[monthly["ruta"] == r].sort_values("mes_dt")
    if len(z) >= 4:
        x = np.arange(len(z))
        slope = np.polyfit(x, z["ipk"], 1)[0]
        trend_rows.append((r, slope, z["ipk"].iloc[0], z["ipk"].iloc[-1]))
if trend_rows:
    td = pd.DataFrame(trend_rows, columns=["ruta","pendiente","inicio","fin"])
    up = td.sort_values("pendiente", ascending=False).iloc[0]
    down = td.sort_values("pendiente").iloc[0]
    if up["pendiente"] > 0:
        insights.append(
            f"**Tendencia creciente:** {up['ruta']} muestra la mayor pendiente positiva del IPK mensual "
            f"({up['pendiente']:+.3f} puntos de IPK por mes en la ventana seleccionada)."
        )
    if down["pendiente"] < 0:
        insights.append(
            f"**Tendencia decreciente:** {down['ruta']} muestra la mayor pendiente negativa "
            f"({down['pendiente']:+.3f} puntos de IPK por mes). Es un candidato para revisión operacional."
        )

# Outliers: robust IQR on daily IPK
valid_daily = daily.dropna(subset=["ipk"]).copy()
if len(valid_daily) >= 20:
    q1, q3 = valid_daily["ipk"].quantile([.25,.75])
    iqr = q3-q1
    low, high = q1-1.5*iqr, q3+1.5*iqr
    outs = valid_daily[(valid_daily["ipk"] < low) | (valid_daily["ipk"] > high)]
    if len(outs):
        share = len(outs)/len(valid_daily)*100
        insights.append(
            f"**Variaciones atípicas:** se detectaron {len(outs):,} observaciones diarias ({share:.1f}%) "
            f"fuera del rango IQR [{low:.3f}, {high:.3f}]. Deben contrastarse con novedades operativas, "
            "cambios de demanda o calidad del dato."
        )

# Best/worst month in current selection
m_all = aggregate_ipk(d, ["mes"]).dropna(subset=["ipk"])
if not m_all.empty:
    bm = m_all.loc[m_all["ipk"].idxmax()]
    wm = m_all.loc[m_all["ipk"].idxmin()]
    insights.append(
        f"**Mejor mes:** {bm['mes']} con IPK {bm['ipk']:.3f}. "
        f"**Peor mes:** {wm['mes']} con IPK {wm['ipk']:.3f}."
    )

# Quality warning
if missing_pct > 0:
    insights.append(
        f"**Calidad:** {d['pasajeros'].isna().sum():,} registros ({missing_pct:.2f}%) no tienen pasajeros. "
        f"Representan {d.loc[d['pasajeros'].isna(),'kilometros'].sum()/km_total*100:.2f}% de los kilómetros filtrados. "
        "El IPK se calcula únicamente sobre kilómetros con pasajeros válidos para evitar introducir un denominador no comparable."
    )

for i in insights:
    st.info(i)

# ---------- Detail ----------
with st.expander("Detalle de datos y metodología"):
    st.markdown("""
    **Grano principal:** fecha + ruta.  
    **IPK diario:** pasajeros movilizados / kilómetros realizados, usando únicamente registros con pasajeros válidos.  
    **IPK agregado:** suma de pasajeros / suma de kilómetros válidos; esto evita promediar ratios y pondera por operación real.  
    **Comparación de período:** período inmediatamente anterior con la misma duración en días.  
    **Outliers:** regla IQR (1,5 × rango intercuartílico) sobre IPK diario; es una señal estadística, no una causa operacional.  
    **Semana, mes, trimestre y año:** se derivan directamente de la fecha de operación.
    """)

    q = pd.DataFrame({
        "Control": [
            "Registros","Rutas","Fecha mínima","Fecha máxima","Pasajeros nulos",
            "Kilómetros = 0","Kilómetros negativos","Pasajeros negativos",
            "Duplicados fila","Duplicados fecha+ruta"
        ],
        "Resultado": [
            f"{len(df):,}", f"{df['ruta'].nunique():,}", str(df["fecha"].min().date()),
            str(df["fecha"].max().date()), f"{df['pasajeros'].isna().sum():,}",
            f"{(df['kilometros']==0).sum():,}", f"{(df['kilometros']<0).sum():,}",
            f"{(df['pasajeros']<0).sum():,}", f"{df.duplicated().sum():,}",
            f"{df.duplicated(['fecha','ruta']).sum():,}"
        ]
    })
    st.dataframe(q, hide_index=True, use_container_width=True)

st.caption("Fuente: ipk_zonal.xlsx · Hoja IPK · Dashboard generado con Streamlit + Plotly")
