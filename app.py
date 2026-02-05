import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import date, timedelta, datetime
import plotly.graph_objects as go
import io

# --------------------------------------------------
# CONFIG PAGINA
# --------------------------------------------------
st.set_page_config(
    page_title="Prezzo Attuale vs Min/Max Anno Precedente",
    page_icon="📈",
    layout="wide"
)

# --------------------------------------------------
# PERIODI TEMPORALI
# --------------------------------------------------
def get_current_period():
    today = date.today()
    return {
        "start_date": date(today.year, 1, 1),
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
    - 📅 Livelli di riferimento: **{previous_period['label']}**
    - 💰 Prezzo: **ultimo close disponibile**
    """
)

# --------------------------------------------------
# SIMBOLI DEFAULT (NON RIDOTTI)
# --------------------------------------------------
DEFAULT_SYMBOLS = [
    "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA", "NFLX",
    "AMD", "INTC", "CRM", "ORCL", "ADBE", "PYPL", "IBM", "CSCO", "NOW", "SNOW",
    "V", "MA", "JPM", "BAC", "WFC", "GS", "MS", "C", "AXP",
    "JNJ", "PFE", "UNH", "ABBV", "MRK", "TMO", "ABT", "CVS", "AMGN", "GILD",
    "DIS", "KO", "PEP", "WMT", "HD", "MCD", "SBUX", "NKE", "TGT", "COST",
    "BA", "CAT", "GE", "MMM", "XOM", "CVX", "COP", "SLB", "EOG", "HAL",
    "VZ", "T", "TMUS", "CMCSA", "CHTR", "WBD", "FOXA",
    "SPY", "QQQ", "IWM", "VTI", "VNQ", "AMT", "CCI", "EQIX", "PLD",
    "ROKU", "SHOP", "ZM", "DOCU", "OKTA", "TWLO", "NET", "DDOG"
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

st.sidebar.info(f"📊 Simboli analizzati: {len(symbols)}")

# --------------------------------------------------
# DOWNLOAD DATI (UNA CHIAMATA PER SIMBOLO)
# --------------------------------------------------
@st.cache_data(ttl=3600)
def fetch_full_data(symbol, start, end):
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(start=start, end=end + timedelta(days=1))
        if data.empty:
            return None
        return data
    except Exception:
        return None

# --------------------------------------------------
# ANALISI SINGOLO TITOLO
# --------------------------------------------------
def analyze(symbol):
    full_data = fetch_full_data(
        symbol,
        previous_period["start_date"],
        current_period["end_date"]
    )

    if full_data is None or full_data.empty:
        return None

    prev_data = full_data.loc[
        (full_data.index.date >= previous_period["start_date"]) &
        (full_data.index.date <= previous_period["end_date"])
    ]

    curr_data = full_data.loc[
        (full_data.index.date >= current_period["start_date"]) &
        (full_data.index.date <= current_period["end_date"])
    ]

    if prev_data.empty or curr_data.empty:
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
# CLOSE vs MIN ANNO PRECEDENTE
# --------------------------------------------------
st.subheader("📉 Close vicino al MINIMO dell’anno precedente")

min_hits = [r for r in results if abs(r["diff_min"]) <= threshold]

if min_hits:
    df_min = pd.DataFrame([
        {
            "Simbolo": r["symbol"],
            "Min Anno Prec": round(r["prev_min"], 2),
            "Close Attuale": round(r["current_close"], 2),
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
# CLOSE vs MAX ANNO PRECEDENTE
# --------------------------------------------------
st.subheader("📈 Close vicino al MASSIMO dell’anno precedente")

max_hits = [r for r in results if abs(r["diff_max"]) <= threshold]

if max_hits:
    df_max = pd.DataFrame([
        {
            "Simbolo": r["symbol"],
            "Max Anno Prec": round(r["prev_max"], 2),
            "Close Attuale": round(r["current_close"], 2),
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
