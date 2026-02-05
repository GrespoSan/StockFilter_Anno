import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="Scanner Minimi Pro", layout="wide")

# --- FIX 1: Inizializzazione Session State ---
# Questo evita che l'app si resetti quando selezioni un grafico
if 'df_risultati' not in st.session_state:
    st.session_state.df_risultati = pd.DataFrame()

st.title("📉 Scanner Minimi Annuali (Versione Corretta)")

# --- Sidebar ---
st.sidebar.header("Parametri di Ricerca")
tickers_input = st.sidebar.text_area("Ticker (es: AAPL, TSLA, MSFT)", "AAPL, TSLA, MSFT, NVDA, AMZN")
threshold = st.sidebar.slider("Distanza massima dal minimo (%)", 0, 50, 10)

today = datetime.today()
prev_year = today.year - 1

# --- Funzione Scaricamento ---
def fetch_data(ticker_list):
    results = []
    tickers = [t.strip().upper() for t in ticker_list.split(",") if t.strip()]
    
    progress = st.progress(0)
    for i, ticker in enumerate(tickers):
        try:
            # Scarichiamo un range ampio per coprire tutto l'anno scorso e oggi
            # Usiamo auto_adjust=False per avere i prezzi 'puri' (più simili a TV)
            data = yf.download(ticker, start=f"{prev_year}-01-01", progress=False, auto_adjust=False)
            
            if not data.empty:
                # FIX 2: Minimo assoluto (Low) dell'anno scorso, non solo chiusura
                data_prev = data[data.index.year == prev_year]
                if not data_prev.empty:
                    # Usiamo 'Low' per trovare il minimo assoluto della candela (come su TV)
                    min_absolute = data_prev['Low'].min()
                    # Prezzo di chiusura di ieri (o ultimo disponibile)
                    current_price = data['Close'].iloc[-1]
                    
                    dist_perc = ((current_price - min_absolute) / min_absolute) * 100
                    
                    results.append({
                        "Ticker": ticker,
                        "Prezzo Attuale": float(current_price),
                        f"Minimo {prev_year} (Low)": float(min_absolute),
                        "Distanza %": float(dist_perc)
                    })
        except:
            pass
        progress.progress((i + 1) / len(tickers))
    progress.empty()
    return pd.DataFrame(results)

# --- Pulsante Scansione ---
if st.sidebar.button("Avvia Scansione", type="primary"):
    st.session_state.df_risultati = fetch_data(tickers_input)

# --- Visualizzazione Risultati ---
df = st.session_state.df_risultati

if not df.empty:
    # Applichiamo il filtro dell'intervallo
    filtered_df = df[df["Distanza %"] <= threshold].sort_values("Distanza %")
    
    st.subheader(f"Risultati entro il {threshold}% dal minimo del {prev_year}")
    st.dataframe(filtered_df.style.format("{:.2f}"), use_container_width=True, hide_index=True)

    st.divider()

    # --- FIX 3: Gestione Grafico senza Reset ---
    st.subheader("Analisi Grafica")
    # La selectbox ora pesca dai risultati filtrati già presenti in memoria
    scelta = st.selectbox("Seleziona un titolo per il grafico:", filtered_df["Ticker"].unique())

    if scelta:
        # Riscarichiamo i dati solo per il grafico selezionato
        dati_plot = yf.download(scelta, start=f"{prev_year}-01-01", progress=False)
        min_line = filtered_df[filtered_df["Ticker"] == scelta][f"Minimo {prev_year} (Low)"].values[0]

        fig = go.Figure()
        # Candlestick per somigliare a TradingView
        fig.add_trace(go.Candlestick(
            x=dati_plot.index,
            open=dati_plot['Open'],
            high=dati_plot['High'],
            low=dati_plot['Low'],
            close=dati_plot['Close'],
            name=scelta
        ))
        
        # Linea del minimo dell'anno scorso
        fig.add_hline(y=min_line, line_dash="dash", line_color="red", 
                      annotation_text=f"Minimo {prev_year}", annotation_position="bottom right")

        fig.update_layout(title=f"Grafico {scelta}", xaxis_rangeslider_visible=False, height=600)
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Fai clic su 'Avvia Scansione' nella barra laterale per caricare i dati.")