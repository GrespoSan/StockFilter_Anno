import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="Scanner Minimi Pro", layout="wide")

# --- Inizializzazione Session State ---
if 'df_risultati' not in st.session_state:
    st.session_state.df_risultati = pd.DataFrame()

st.title("📉 Scanner Minimi Annuali (Versione Stable)")

# --- Sidebar ---
st.sidebar.header("Parametri")
tickers_input = st.sidebar.text_area("Inserisci Ticker (es: AAPL, TSLA)", "AAPL, TSLA, NVDA, AMZN")
threshold = st.sidebar.slider("Distanza massima dal minimo (%)", 0, 50, 10)

today = datetime.today()
prev_year = today.year - 1

def fetch_data(ticker_list):
    results = []
    tickers = [t.strip().upper() for t in ticker_list.split(",") if t.strip()]
    
    progress = st.progress(0)
    status_text = st.empty()
    
    for i, ticker in enumerate(tickers):
        status_text.text(f"Scansione {ticker}...")
        try:
            # Scarichiamo i dati
            data = yf.download(ticker, start=f"{prev_year}-01-01", progress=False, auto_adjust=False)
            
            # --- FIX PER MULTIINDEX (yfinance > 0.2.40) ---
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
                        "Minimo_Anno_Prec": min_abs, # Nome fisso interno
                        "Distanza_Perc": dist_perc
                    })
        except Exception as e:
            print(f"Errore su {ticker}: {e}")
            continue
        progress.progress((i + 1) / len(tickers))
    
    progress.empty()
    status_text.empty()
    return pd.DataFrame(results)

# --- Esecuzione ---
if st.sidebar.button("Avvia Scansione", type="primary"):
    st.session_state.df_risultati = fetch_data(tickers_input)

df = st.session_state.df_risultati

if not df.empty:
    # Filtro
    filtered_df = df[df["Distanza_Perc"] <= threshold].sort_values("Distanza_Perc").copy()
    
    st.subheader(f"Titoli vicino al minimo del {prev_year}")
    
    # Visualizzazione con rinomina colonne "estetica" solo per l'utente
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

    st.divider()

    # --- Grafico ---
    st.subheader("Dettaglio Grafico")
    scelta = st.selectbox("Scegli un ticker dai risultati:", filtered_df["Ticker"].unique())

    if scelta:
        # Recupero i dati per il grafico
        dati_plot = yf.download(scelta, start=f"{prev_year}-01-01", progress=False)
        
        # Appiattisco colonne anche qui per sicurezza
        if isinstance(dati_plot.columns, pd.MultiIndex):
            dati_plot.columns = dati_plot.columns.get_level_values(0)

        # Recupero il valore del minimo usando il nome colonna fisso
        valore_minimo = filtered_df.loc[filtered_df["Ticker"] == scelta, "Minimo_Anno_Prec"].values[0]

        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=dati_plot.index,
            open=dati_plot['Open'],
            high=dati_plot['High'],
            low=dati_plot['Low'],
            close=dati_plot['Close'],
            name="Prezzo"
        ))
        
        fig.add_hline(y=valore_minimo, line_dash="dash", line_color="red", 
                      annotation_text=f"Minimo {prev_year}", annotation_position="bottom right")

        fig.update_layout(
            title=f"{scelta} - Confronto con minimo {prev_year} ({valore_minimo:.2f})",
            xaxis_rangeslider_visible=False, 
            height=500,
            template="plotly_dark"
        )
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Fai clic su 'Avvia Scansione' per caricare i titoli.")