import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# Configurazione Pagina
st.set_page_config(page_title="Scanner Minimi Pro", layout="wide")

# --- Inizializzazione Session State ---
if 'df_risultati' not in st.session_state:
    st.session_state.df_risultati = pd.DataFrame()

st.title("📉 Scanner Minimi Annuali")

# --- Sidebar ---
st.sidebar.header("Configurazione")

# Caricamento File o Inserimento Manuale
uploaded_file = st.sidebar.file_uploader("1. Carica file .txt", type="txt")
manual_input = st.sidebar.text_area("2. Oppure inserisci qui (es: AAPL, TSLA)", "AAPL, MSFT, GOOGL, NVDA, TSLA, AMZN, NFLX, META")

# SOGLIA % - Questo valore controlla tutto il filtro
threshold = st.sidebar.slider("Mostra solo titoli entro il (%):", 0, 50, 5)

today = datetime.today()
prev_year = today.year - 1
st.sidebar.info(f"Confronto con minimi del **{prev_year}**")

def fetch_data(ticker_list_raw):
    """Scarica i dati e calcola le distanze"""
    results = []
    # Pulizia input
    tickers = ticker_list_raw.replace('\n', ',').replace(' ', ',').split(',')
    tickers = [t.strip().upper() for t in tickers if t.strip()]
    
    if not tickers:
        return pd.DataFrame()

    progress = st.progress(0)
    status_text = st.empty()
    
    for i, ticker in enumerate(tickers):
        status_text.text(f"Analisi: {ticker} ({i+1}/{len(tickers)})")
        try:
            # Scarichiamo dati (auto_adjust=False per avere Low reale come TradingView)
            data = yf.download(ticker, start=f"{prev_year}-01-01", progress=False, auto_adjust=False)
            
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)

            if not data.empty:
                data_prev = data[data.index.year == prev_year]
                if not data_prev.empty:
                    min_abs = float(data_prev['Low'].min())
                    current_price = float(data['Close'].iloc[-1])
                    # Calcolo distanza percentuale
                    dist_perc = ((current_price - min_abs) / min_abs) * 100
                    
                    results.append({
                        "Ticker": ticker,
                        "Prezzo": current_price,
                        "Min_Prev_Year": min_abs,
                        "Dist_Perc": dist_perc
                    })
        except:
            continue
        progress.progress((i + 1) / len(tickers))
    
    progress.empty()
    status_text.empty()
    return pd.DataFrame(results)

# --- Azione Scansione ---
if st.sidebar.button("AVVIA SCANSIONE", type="primary"):
    input_data = uploaded_file.read().decode("utf-8") if uploaded_file else manual_input
    if input_data:
        st.session_state.df_risultati = fetch_data(input_data)
    else:
        st.error("Inserisci dei ticker!")

# --- LOGICA DI FILTRO RIGOROSA ---
df_all = st.session_state.df_risultati

if not df_all.empty:
    # FILTRO: Teniamo solo quelli <= soglia (es: se soglia è 5%, esclude quelli al 6%)
    filtered_df = df_all[df_all["Dist_Perc"] <= threshold].sort_values("Dist_Perc").copy()
    
    if not filtered_df.empty:
        st.success(f"Trovati {len(filtered_df)} titoli che rispettano il criterio (≤ {threshold}%)")
        
        # 1. Tabella Formattata
        display_df = filtered_df.rename(columns={
            "Min_Prev_Year": f"Minimo {prev_year}",
            "Dist_Perc": "Distanza %"
        })
        
        st.dataframe(
            display_df.style.format({
                "Prezzo": "{:.2f}",
                f"Minimo {prev_year}": "{:.2f}",
                "Distanza %": "{:.2f}%"
            }), 
            use_container_width=True, 
            hide_index=True
        )

        # 2. Pulsante Export (scarica solo i filtrati)
        csv = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Scarica questi risultati (CSV)", csv, "risultati_filtrati.csv", "text/csv")

        # 3. Grafico (il menu a tendina mostra SOLO i filtrati)
        st.divider()
        st.subheader("Analisi Grafica")
        scelta = st.selectbox("Seleziona tra i titoli filtrati:", filtered_df["Ticker"].unique())

        if scelta:
            dati_plot = yf.download(scelta, start=f"{prev_year}-01-01", progress=False)
            if isinstance(dati_plot.columns, pd.MultiIndex):
                dati_plot.columns = dati_plot.columns.get_level_values(0)
            
            # Recupero il valore del minimo dal dataframe filtrato
            val_min = filtered_df.loc[filtered_df["Ticker"] == scelta, "Min_Prev_Year"].values[0]

            fig = go.Figure(data=[go.Candlestick(
                x=dati_plot.index, open=dati_plot['Open'], high=dati_plot['High'],
                low=dati_plot['Low'], close=dati_plot['Close'], name=scelta
            )])
            fig.add_hline(y=val_min, line_dash="dash", line_color="red", annotation_text="Supporto Anno Prec.")
            fig.update_layout(title=f"{scelta} (Min {prev_year}: {val_min:.2f})", 
                              xaxis_rangeslider_visible=False, template="plotly_dark", height=500)
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning(f"Nessun titolo trovato entro il {threshold}%. Prova ad aumentare la soglia.")
else:
    st.info("Configura i ticker e clicca su 'AVVIA SCANSIONE'.")