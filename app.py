import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# Configurazione della pagina
st.set_page_config(page_title="Scanner Minimi Anno Precedente", layout="wide")

st.title("🎯 Cacciatore di Minimi: Filtro Attivo")
st.markdown("""
Questa app mostra **SOLO** i titoli il cui prezzo attuale è vicino al minimo dell'anno scorso 
entro la soglia percentuale definita nella barra laterale.
""")

# --- Sidebar per Input ---
st.sidebar.header("Filtri")

# Lista di default
default_tickers = "AAPL, MSFT, GOOGL, TSLA, AMZN, NVDA, INT, PFE, KO, XOM"
tickers_input = st.sidebar.text_area("Inserisci i Ticker (separati da virgola)", default_tickers)

# SLIDER FONDAMENTALE: Definisce l'intervallo
threshold = st.sidebar.slider("Mostra solo se la distanza dal minimo è inferiore al (%):", 0, 50, 5)

# Calcolo delle date
today = datetime.today()
current_year = today.year
previous_year = current_year - 1

st.sidebar.info(f"Confronto con i minimi del: **{previous_year}**")

# --- Funzione di caricamento dati ---
@st.cache_data(ttl=3600)
def get_stock_data(ticker_list):
    results = []
    tickers = [t.strip().upper() for t in ticker_list.split(",") if t.strip()]
    
    if not tickers:
        return []

    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, ticker in enumerate(tickers):
        status_text.text(f"Analisi {ticker}...")
        try:
            # Scarichiamo dati dall'anno precedente ad oggi
            start_date = f"{previous_year}-01-01"
            data = yf.download(ticker, start=start_date, progress=False, auto_adjust=True)
            
            if not data.empty:
                # 1. Filtro dati anno precedente
                data_prev_year = data[data.index.year == previous_year]
                
                if not data_prev_year.empty:
                    # Gestione colonne (Fix per yfinance updates)
                    if isinstance(data.columns, pd.MultiIndex):
                        close_prev = data_prev_year['Close'][ticker]
                        last_price = data['Close'][ticker].iloc[-1]
                    else:
                        close_prev = data_prev_year['Close']
                        last_price = data['Close'].iloc[-1]
                        
                    min_prev_year = close_prev.min()

                    # 2. Calcolo Distanza %
                    # Formula: (Prezzo - Minimo) / Minimo * 100
                    diff_percent = ((last_price - min_prev_year) / min_prev_year) * 100
                    
                    last_date = data.index[-1].strftime('%Y-%m-%d')

                    results.append({
                        "Ticker": ticker,
                        "Prezzo Attuale": float(last_price),
                        "Data": last_date,
                        f"Minimo {previous_year}": float(min_prev_year),
                        "Distanza (%)": float(diff_percent)
                    })
        except Exception as e:
            pass # Ignoriamo errori temporanei per non bloccare il loop
        
        progress_bar.progress((i + 1) / len(tickers))
    
    progress_bar.empty()
    status_text.empty()
    return pd.DataFrame(results)

# --- Esecuzione Logica ---
if st.button("Cerca Titoli nell'Intervallo", type="primary"):
    with st.spinner('Scansione mercati in corso...'):
        df = get_stock_data(tickers_input)

    if not df.empty:
        # --- FILTRO ATTIVO ---
        # Teniamo solo le righe dove la distanza % è minore o uguale alla soglia
        filtered_df = df[df["Distanza (%)"] <= threshold].copy()
        
        # Ordiniamo: dai più vicini (o sotto) al minimo a salire
        filtered_df = filtered_df.sort_values(by="Distanza (%)", ascending=True)

        # Contatori
        total_scanned = len(df)
        found_matches = len(filtered_df)

        if found_matches > 0:
            st.success(f"Trovati **{found_matches}** titoli su {total_scanned} all'interno del {threshold}% dal minimo.")
            
            # Formattazione per la tabella
            st.dataframe(
                filtered_df.style.format({
                    "Prezzo Attuale": "{:.2f}", 
                    f"Minimo {previous_year}": "{:.2f}", 
                    "Distanza (%)": "{:+.2f}%" # Mette il + se positivo, - se negativo
                }).background_gradient(subset=["Distanza (%)"], cmap="RdYlGn_r", vmin=0, vmax=threshold),
                use_container_width=True,
                hide_index=True
            )
            
            # --- Grafico (Solo per i filtrati) ---
            st.divider()
            st.subheader("Visualizzazione Grafica")
            
            # Selectbox contiene solo i titoli filtrati
            selected_ticker = st.selectbox("Seleziona titolo per dettagli:", filtered_df["Ticker"].unique())
            
            if selected_ticker:
                ticker_data = yf.download(selected_ticker, start=f"{previous_year}-01-01", progress=False, auto_adjust=True)
                
                # Recupero dati per grafico
                if isinstance(ticker_data.columns, pd.MultiIndex):
                    plot_close = ticker_data['Close'][selected_ticker]
                else:
                    plot_close = ticker_data['Close']
                
                min_val = filtered_df[filtered_df["Ticker"] == selected_ticker][f"Minimo {previous_year}"].values[0]

                fig = go.Figure()
                fig.add_trace(go.Scatter(x=ticker_data.index, y=plot_close, mode='lines', name='Prezzo', line=dict(color='blue')))
                fig.add_hline(y=min_val, line_dash="dash", line_color="red", annotation_text="Supporto Minimo Prev.", annotation_position="bottom right")
                
                fig.update_layout(title=f"{selected_ticker} - Test del Minimo", template="plotly_white", height=450)
                st.plotly_chart(fig, use_container_width=True)

        else:
            st