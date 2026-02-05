import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import date, timedelta, datetime
import plotly.graph_objects as go
import io
import calendar

# --------------------------------------------------
# CONFIG PAGINA
# --------------------------------------------------
st.set_page_config(
    page_title="Prezzo Attuale vs Min/Max Anno Precedente",
    page_icon="📈",
    layout="wide"
)

# --------------------------------------------------
# FUNZIONI PER PERIODO ANNUALE
# --------------------------------------------------
def get_current_period():
    today = date.today()
    year = today.year

    return {
        "start_date": date(year, 1, 1),
        "end_date": today,
        "label": f"Prezzo Attuale ({today.strftime('%d/%m/%Y')})"
    }

def get_previous_year_period():
    prev_year = date.today().year - 1
    return {
        "start_date": date(prev_year, 1, 1),
        "end_date": date(prev_year, 12, 31),
        "label": f"Anno {prev_year}"
    }

current_period = get_current_period()
previous_period = get_previous_year_period()

# --------------------------------------------------
# TITOLI
# --------------------------------------------------
st.title("📊 Prezzo Attuale vs Min / Max Anno Precedente")
st.markdown(
    f"""
    **Confronto diretto**
    - 📅 **Livelli di riferimento**: {previous_period['label']}
    - 💰 **Prezzo**: ultimo close disponibile
    """
)

# --------------------------------------------------
# SIMBOLI DEFAULT
# --------------------------------------------------
DEFAULT_SYMBOLS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA",
    "JPM", "BAC", "V", "MA",
    "JNJ", "UNH", "PFE",
    "KO", "PEP", "WMT",
    "XOM", "CVX",
    "SPY", "QQQ"
]

# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------
st.sidebar.header("⚙️ Configurazione")

uploaded_file = st.sidebar.file_uploader(
    "📁 Carica file TXT con simboli",
    type=["txt"]
)

if uploaded_file:
    content = uploaded_file.read().decode("utf-8")
    symbols = list(
        dict.fromkeys(
            s.strip().upper()
            for line in content.splitlines()
            for s in line.split(",")
            if s.strip()
        )
    )
else:
    symbols = DEFAULT_SYMBOLS

threshold = st.sidebar.slider(
    "🎯 Soglia vicinanza (%)",
    min_value=1.0,
    max_value=15.0,
    value=5.0,
    step=0.5
)

# --------------------------------------------------
# DOWNLOAD DATI
# --------------------------------------------------
@st.cache_data
def fetch_data(symbol, start, end):
    ticker = yf.Ticker(symbol)
    data = ticker.history(start=start, end=end + timedelta(days=1))
    return data if not data.empty else None

# --------------------------------------------------
# ANALISI SINGOLO TITOLO
# --------------------------------------------------
def analyze(symbol):
    prev_data = fetch_data(
        symbol,
        previous_period["start_date"],
        previous_period["end_date"]
    )

    curr_data = fetch_data(
        symbol,
        current_period["start_date"],
        current_period["end_date"]
    )

    if prev_data is None or curr_data is None:
        return None

    prev_min = prev_data["Low"].min()
    prev_max = prev_data["High"].max()
    prev_min_date = prev_data["Low"].idxmin()
    prev_max_date = prev_data["High"].idxmax()

    current_close = curr_data["Close"].iloc[-1]

    diff_min = (current_close - prev_min) / prev_min * 100
    diff_max = (current_close - prev_max) / prev_max * 100

    return {
        "symbol": symbol,
        "current_close": current_close,
        "prev_min": prev_min,
        "prev_max": prev_max,
        "prev_min_date": prev_min_date,
        "prev_max_date": prev_max_date,
        "diff_min": diff_min,
        "diff_max": diff_max,
        "prev_data": prev_data,
        "curr_data": curr_data
    }

# --------------------------------------------------
# ESECUZIONE ANALISI
# --------------------------------------------------
results = []
with st.spinner("Analisi in corso..."):
    for s in symbols:
        r = analyze(s)
        if r:
            results.append(r)

# --------------------------------------------------
# TABELLA CLOSE vs MIN ANNO PRECEDENTE
# --------------------------------------------------
min_hits = [r for r in results if abs(r["diff_min"]) <= threshold]

st.subheader("📉 Close vicino al MINIMO dell’anno precedente")

if min_hits:
    df_min = pd.DataFrame([
        {
            "Simbolo": r["symbol"],
            "Min Anno Prec": f"{r['prev_min']:.2f}",
            "Close Attuale": f"{r['current_close']:.2f}",
            "Differenza %": round(r["diff_min"], 1),
            "Data Min": r["prev_min_date"].strftime("%d/%m/%Y")
        }
        for r in min_hits
    ]).sort_values("Differenza %")

    st.dataframe(df_min, use_container_width=True)

    csv = io.StringIO()
    df_min.to_csv(csv, index=False)

    st.download_button(
        "📥 Scarica CSV (Min Anno Prec)",
        csv.getvalue(),
        file_name=f"close_vs_min_anno_prec_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv"
    )
else:
    st.info("Nessun titolo vicino al minimo dell’anno precedente.")

# --------------------------------------------------
# TABELLA CLOSE vs MAX ANNO PRECEDENTE
# --------------------------------------------------
max_hits = [r for r in results if abs(r["diff_max"]) <= threshold]

st.subheader("📈 Close vicino al MASSIMO dell’anno precedente")

if max_hits:
    df_max = pd.DataFrame([
        {
            "Simbolo": r["symbol"],
            "Max Anno Prec": f"{r['prev_max']:.2f}",
            "Close Attuale": f"{r['current_close']:.2f}",
            "Differenza %": round(r["diff_max"], 1),
            "Data Max": r["prev_max_date"].strftime("%d/%m/%Y")
        }
        for r in max_hits
    ]).sort_values("Differenza %")

    st.dataframe(df_max, use_container_width=True)

    csv = io.StringIO()
    df_max.to_csv(csv, index=False)

    st.download_button(
        "📥 Scarica CSV (Max Anno Prec)",
        csv.getvalue(),
        file_name=f"close_vs_max_anno_prec_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv"
    )
else:
    st.info("Nessun titolo vicino al massimo dell’anno precedente.")
