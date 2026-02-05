import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="Scanner Minimi Pro", layout="wide")

# Inizializzazione Session State per evitare reset
if 'df_risultati' not in st.session_state:
    st.session_state.df_risultati = pd.DataFrame()

st.title("📉 Scanner Minimi Annuali")

# --- Sidebar ---
st.sidebar.header("Parametri di Ricerca")
tickers_input = st.sidebar.text_area("Ticker (es: AAPL, TSLA, MSFT)", "AAPL, TSLA, MSFT, NVDA, AMZN")
threshold = st.sidebar.slider("Distanza massima dal minimo (%)", 0, 50, 10)

today = datetime.today()
prev_year = today.year - 1

def fetch_data(ticker_list):
    results = []
    tickers = [t.strip().upper() for t in ticker_list.split(",") if t.strip()]
    
    progress = st.progress(0)
    status_text = st.empty()
    
    for i, ticker in enumerate(tickers):
        status_text.text(f"Analisi {ticker}...")
        try:
            # Scarichiamo dati (auto_adjust=False per OHLC puro come TradingView)
            data = yf.download(ticker, start=f"{prev_year}-01-01", progress=False, auto_adjust=False)
            
            if not data.empty:
                data_prev = data[data.index.year == prev_year]
                if not data_prev.empty:
                    # Minimo assoluto (Low) dell'anno scorso
                    min_absolute = float(data_prev['Low'].min())
                    # Ultima chiusura disponibile
                    current_price = float(data['Close'].iloc[-1])
                    
                    dist_perc = ((current_price - min_absolute) / min_absolute) * 100
                    
                    results.append({
                        "Ticker": ticker,
                        "Prezzo Attuale": current_price,
                        f"Minimo {prev_year}": min_absolute,
                        "Distanza %": dist_perc
                    })
        except:
            continue
        progress.progress((i + 1) / len(tickers))
    
    progress.empty()
    status_text.empty()
    return pd.DataFrame(results)

# --- Pulsante Scansione ---
if st.sidebar.button("Avvia Scansione", type="primary"):
    st.session_state.df_risultati = fetch_data(tickers_input)

# --- Visualizzazione Risultati ---
df = st.session_state.df_risultati

if not df.empty:
    # Filtro dinamico
    filtered_df = df[df["Distanza %"] <= threshold].sort_values("Distanza %")
    
    st.subheader(f"Risultati entro il {threshold}% dal minimo del {prev_year}")
    
    # --- FIX ERRORE: Formattazione selettiva ---
    # Formattiamo solo le colonne numeriche per evitare il ValueError sulle stringhe
    col_min = f"Minimo {prev_year}"
    st.dataframe(
        filtered_df.style.format({
            "Prezzo Attuale": "{:.2f}",
            col_min: "{:.2f}",
            "Distanza %": "{:.2f}%"
        }), 
        use_container_width=True, 
        hide_index=True
    )

    st.divider()

    # --- Analisi Grafica ---
    st.subheader("Analisi Grafica")
    scelta = st.selectbox("Seleziona un titolo per visualizzare il grafico:", filtered_df["Ticker"].unique())

    if scelta:
        # Scarichiamo dati per il grafico (candlestick)
        dati_plot = yf.download(scelta, start=f"{prev_year}-01-01", progress=False)
        row_scelta = filtered_df[filtered_df["Ticker"] == scelta]
        min_line = row_scelta[col_min].values[0]

        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=dati_plot.index,
            open=dati_plot['Open'],
            high=dati_plot['High'],
            low=dati_plot['Low'],
            close=dati_plot['Close'],
            name=scelta
        ))
        
        fig.add_hline(y=min_line, line_dash="dash", line_color="red", 
                      annotation_text=f"Supporto Min {prev_year}", 
                      annotation_position="bottom right")

        fig.update_layout(
            title=f"Grafico OHLC {scelta} (Minimo {prev_year}: {min_line:.2f})",
            xaxis_rangeslider_visible=False, 
            height=600,
            template="plotly_dark" # Più simile alla Dark Mode di TradingView
        )
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Configura i ticker e clicca su 'Avvia Scansione' per iniziare.")