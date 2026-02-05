import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# Configurazione Pagina
st.set_page_config(page_title="Scanner Minimi Pro", layout="wide")

# --- Inizializzazione Session State ---
if 'df_risultati' not in st.session_state:
    # Inizializziamo con colonne predefinite per evitare KeyError
    st.session_state.df_risultati = pd.DataFrame(columns=["Ticker", "Prezzo", "Min_Prev_Year", "Dist_Perc"])

st.title("📉 Scanner Minimi Annuali")

# --- Sidebar ---
st.sidebar.header("Configurazione")

uploaded_file = st.sidebar.file_uploader("1. Carica file .txt", type="txt")
manual_input = st.sidebar.text_area("2. Oppure inserisci qui", "AAPL, MSFT, GOOGL, NVDA, TSLA")

threshold = st.sidebar.slider("Mostra solo titoli entro il (%):", 0, 50, 5)

today = datetime.today()
prev_year = today.year - 1

def fetch_data(ticker_list_raw):
    results = []
    tickers = ticker_list_raw.replace('\n', ',').replace(' ', ',').split(',')
    tickers = [t.strip().upper() for t in tickers if t.strip()]
    
    if not tickers:
        return pd.DataFrame(columns=["Ticker", "Prezzo", "Min_Prev_Year", "Dist_Perc"])

    progress = st.progress(0)
    status_text = st.empty()
    
    for i, ticker in enumerate(tickers):
        status_text.text(f"Analisi: {ticker} ({i+1}/{len(tickers)})")
        try:
            # auto_adjust=False per mantenere i prezzi OHLC originali (TradingView style)
            data = yf.download(ticker, start=f"{prev_year}-01-01", progress=False, auto_adjust=False)
            
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)

            if not data.empty:
                data_prev = data[data.index.year == prev_year]
                if not data_prev.empty:
                    min_abs = float(data_prev['Low'].min())
                    current_price = float(data['Close'].iloc[-1])
                    
                    # Formula: $Dist \% = \frac{Prezzo - Min}{Min} \times 100$
                    dist_perc = ((current_price - min_abs) / min_abs) * 100
                    
                    results.append({
                        "Ticker": ticker,
                        "Prezzo": current_price,
                        "Min_Prev_Year": min_abs,
                        "Dist_Perc": dist_perc
                    })
        except Exception:
            continue
        progress.progress((i + 1) / len(tickers))
    
    progress.empty()
    status_text.empty()
    
    # Se results è vuoto, restituiamo un DF con colonne ma senza righe
    if not results:
        return pd.DataFrame(columns=["Ticker", "Prezzo", "Min_Prev_Year", "Dist_Perc"])
        
    return pd.DataFrame(results)

# --- Azione Scansione ---
if st.sidebar.button("AVVIA SCANSIONE", type="primary"):
    input_data = ""
    if uploaded_file:
        input_data = uploaded_file.read().decode("utf-8")
    else:
        input_data = manual_input
        
    if input_data.strip():
        st.session_state.df_risultati = fetch_data(input_data)
    else:
        st.error("Inserisci dei ticker!")

# --- LOGICA DI VISUALIZZAZIONE ---
df_all = st.session_state.df_risultati

# Controllo se la colonna esiste (evita il KeyError)
if not df_all.empty and "Dist_Perc" in df_all.columns:
    
    # Filtro rigoroso
    filtered_df = df_all[df_all["Dist_Perc"] <= threshold].sort_values("Dist_Perc").copy()
    
    if not filtered_df.empty:
        st.success(f"Trovati {len(filtered_df)} titoli entro la soglia del {threshold}%")
        
        # Tabella
        st.dataframe(
            filtered_df.rename(columns={
                "Min_Prev_Year": f"Minimo {prev_year}",
                "Dist_Perc": "Distanza %"
            }).style.format({
                "Prezzo": "{:.2f}",
                f"Minimo {prev_year}": "{:.2f}",
                "Distanza %": "{:.2f}%"
            }), 
            use_container_width=True, 
            hide_index=True
        )

        # Download CSV
        csv = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Scarica Risultati (CSV)", csv, "report_minimi.csv", "text/csv")

        # Grafico
        st.divider()
        scelta = st.selectbox("Analisi Grafica:", filtered_df["Ticker"].unique())

        if scelta:
            dati_plot = yf.download(scelta, start=f"{prev_year}-01-01", progress=False)
            if isinstance(dati_plot.columns, pd.MultiIndex):
                dati_plot.columns = dati_plot.columns.get_level_values(0)
            
            val_min = filtered_df.loc[filtered_df["Ticker"] == scelta, "Min_Prev_Year"].values[0]

            fig = go.Figure(data=[go.Candlestick(
                x=dati_plot.index, open=dati_plot['Open'], high=dati_plot['High'],
                low=dati_plot['Low'], close=dati_plot['Close'], name=scelta
            )])
            fig.add_hline(y=val_min, line_dash="dash", line_color="red", annotation_text=f"Min {prev_year}")
            fig.update_layout(title=f"{scelta} vs Minimo {prev_year}", 
                              xaxis_rangeslider_visible=False, template="plotly_dark", height=500)
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning(f"Nessun titolo trovato entro il {threshold}%. Prova ad aumentare la soglia.")
else:
    if not df_all.empty:
        st.info("Inizia una scansione per visualizzare i risultati.")