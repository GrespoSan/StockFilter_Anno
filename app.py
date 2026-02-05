import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="Scanner Minimi Pro", layout="wide")

# --- Inizializzazione Session State ---
if 'df_risultati' not in st.session_state:
    st.session_state.df_risultati = pd.DataFrame()

st.title("📉 Scanner Minimi Annuali + Caricamento Liste")

# --- Sidebar ---
st.sidebar.header("Configurazione Input")

# 1. Opzione Caricamento File
uploaded_file = st.sidebar.file_uploader("Carica un file .txt con i ticker", type="txt")

# 2. Area di testo (usata se non c'è il file o per aggiunte rapide)
manual_input = st.sidebar.text_area("Oppure inserisci manualmente (es: AAPL, TSLA)", "AAPL, MSFT, GOOGL")

# 3. Parametri tecnici
threshold = st.sidebar.slider("Distanza massima dal minimo (%)", 0, 50, 10)

today = datetime.today()
prev_year = today.year - 1

def fetch_data(ticker_list_raw):
    """Elabora la lista di ticker e scarica i dati"""
    results = []
    
    # Pulizia della lista: gestisce virgole, spazi e a capo
    tickers = ticker_list_raw.replace('\n', ',').replace(' ', ',').split(',')
    tickers = [t.strip().upper() for t in tickers if t.strip()]
    
    if not tickers:
        return pd.DataFrame()

    progress = st.progress(0)
    status_text = st.empty()
    
    for i, ticker in enumerate(tickers):
        status_text.text(f"Analisi in corso: {ticker} ({i+1}/{len(tickers)})")
        try:
            data = yf.download(ticker, start=f"{prev_year}-01-01", progress=False, auto_adjust=False)
            
            # Fix MultiIndex
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)

            if not data.empty:
                data_prev = data[data.index.year == prev_year]
                if not data_prev.empty:
                    min_abs = float(data_prev['Low'].min())
                    current_price = float(data['Close'].iloc[-1])
                    dist_perc = ((current_price - min_abs) / min_abs) * 100
                    
                    results.append({
                        "Ticker": ticker,
                        "Prezzo": current_price,
                        "Minimo_Anno_Prec": min_abs,
                        "Distanza_Perc": dist_perc
                    })
        except:
            continue
        progress.progress((i + 1) / len(tickers))
    
    progress.empty()
    status_text.empty()
    return pd.DataFrame(results)

# --- Logica di attivazione ---
if st.sidebar.button("Avvia Scansione", type="primary"):
    input_final = ""
    
    # Se l'utente ha caricato un file, usa quello
    if uploaded_file is not None:
        input_final = uploaded_file.read().decode("utf-8")
    else:
        # Altrimenti usa l'input manuale
        input_final = manual_input
        
    if input_final:
        st.session_state.df_risultati = fetch_data(input_final)
    else:
        st.error("Inserisci almeno un ticker o carica un file!")

# --- Visualizzazione Risultati ---
df = st.session_state.df_risultati

if not df.empty:
    filtered_df = df[df["Distanza_Perc"] <= threshold].sort_values("Distanza_Perc").copy()
    
    st.subheader(f"🔍 Titoli filtrati (entro il {threshold}% dal minimo {prev_year})")
    
    if not filtered_df.empty:
        st.dataframe(
            filtered_df.rename(columns={
                "Minimo_Anno_Prec": f"Minimo {prev_year}",
                "Distanza_Perc": "Distanza %"
            }).style.format({
                "Prezzo": "{:.2f}",
                f"Minimo {prev_year}": "{:.2f}",
                "Distanza %": "{:.2f}%"
            }), 
            use_container_width=True, 
            hide_index=True
        )

        # --- Grafico ---
        st.divider()
        st.subheader("📊 Analisi Tecnica Dettagliata")
        scelta = st.selectbox("Seleziona un titolo per il grafico:", filtered_df["Ticker"].unique())

        if scelta:
            dati_plot = yf.download(scelta, start=f"{prev_year}-01-01", progress=False)
            if isinstance(dati_plot.columns, pd.MultiIndex):
                dati_plot.columns = dati_plot.columns.get_level_values(0)

            valore_minimo = filtered_df.loc[filtered_df["Ticker"] == scelta, "Minimo_Anno_Prec"].values[0]

            fig = go.Figure()
            fig.add_trace(go.Candlestick(
                x=dati_plot.index, open=dati_plot['Open'], high=dati_plot['High'],
                low=dati_plot['Low'], close=dati_plot['Close'], name=scelta
            ))
            fig.add_hline(y=valore_minimo, line_dash="dash", line_color="red", 
                          annotation_text=f"Supporto {prev_year}", annotation_position="bottom right")
            
            fig.update_layout(title=f"{scelta} - Test del Minimo", xaxis_rangeslider_visible=False, 
                              height=500, template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning(f"Nessun titolo trovato con distanza inferiore al {threshold}%.")
else:
    st.info("Carica un file o inserisci i ticker, poi clicca su 'Avvia Scansione'.")