import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Configurazione della pagina
st.set_page_config(page_title="Analisi Minimi Anno Precedente", layout="wide")

st.title("📉 Cacciatore di Minimi: Confronto con l'Anno Precedente")
st.markdown("""
Questa applicazione confronta l'**ultimo prezzo di chiusura** con il **prezzo minimo** registrato durante l'intero **anno solare precedente**.
Utile per individuare titoli che sono tornati su livelli di supporto storici.
""")

# --- Sidebar per Input ---
st.sidebar.header("Impostazioni")

# Lista di default di ticker (puoi aggiungerne altri)
default_tickers = "AAPL, MSFT, GOOGL, TSLA, AMZN, NVDA, INT"
tickers_input = st.sidebar.text_area("Inserisci i Ticker (separati da virgola)", default_tickers)

# Soglia di vicinanza (filtro opzionale)
threshold = st.sidebar.slider("Evidenzia se distante dal minimo meno del (%):", 0, 50, 10)

# Calcolo delle date
today = datetime.today()
current_year = today.year
previous_year = current_year - 1

st.sidebar.info(f"Anno Precedente analizzato: **{previous_year}**")

# --- Funzione di caricamento dati ---
@st.cache_data(ttl=3600) # Cache dei dati per 1 ora
def get_stock_data(ticker_list):
    results = []
    
    # Pulizia della lista ticker
    tickers = [t.strip().upper() for t in ticker_list.split(",") if t.strip()]
    
    if not tickers:
        return []

    # Barra di progresso
    progress_bar = st.progress(0)
    
    for i, ticker in enumerate(tickers):
        try:
            # Scarichiamo dati dall'inizio dell'anno precedente ad oggi
            start_date = f"{previous_year}-01-01"
            data = yf.download(ticker, start=start_date, progress=False, auto_adjust=True)
            
            if data.empty:
                continue

            # 1. Filtriamo i dati solo dell'anno precedente per trovare il minimo
            data_prev_year = data[data.index.year == previous_year]
            
            if data_prev_year.empty:
                # Gestione caso: azienda non esisteva l'anno scorso o dati mancanti
                min_prev_year = None
            else:
                # Se yfinance restituisce MultiIndex (spesso capita con nuove versioni), gestiamo colonne
                if isinstance(data.columns, pd.MultiIndex):
                    close_col = data_prev_year['Close'][ticker]
                else:
                    close_col = data_prev_year['Close']
                    
                min_prev_year = close_col.min()

            # 2. Otteniamo l'ultimo prezzo disponibile (Chiusura di ieri/oggi)
            if isinstance(data.columns, pd.MultiIndex):
                last_price = data['Close'][ticker].iloc[-1]
            else:
                last_price = data['Close'].iloc[-1]
            
            last_date = data.index[-1].strftime('%Y-%m-%d')

            # 3. Calcoli
            if min_prev_year:
                # Distanza percentuale dal minimo: (Prezzo - Minimo) / Minimo * 100
                diff_percent = ((last_price - min_prev_year) / min_prev_year) * 100
                
                results.append({
                    "Ticker": ticker,
                    "Prezzo Attuale": round(last_price, 2),
                    "Data Ultimo Prezzo": last_date,
                    f"Minimo {previous_year}": round(min_prev_year, 2),
                    "Distanza dal Min (%)": round(diff_percent, 2)
                })
        except Exception as e:
            st.error(f"Errore con {ticker}: {e}")
        
        # Aggiorna barra progresso
        progress_bar.progress((i + 1) / len(tickers))
    
    progress_bar.empty()
    return pd.DataFrame(results)

# --- Esecuzione Logica ---
if st.button("Analizza Titoli", type="primary"):
    with st.spinner('Scaricamento dati in corso...'):
        df = get_stock_data(tickers_input)

    if not df.empty:
        # Ordinamento: mostriamo prima quelli più vicini al minimo (distanza % minore)
        df = df.sort_values(by="Distanza dal Min (%)", ascending=True)

        # --- Visualizzazione Tabella ---
        st.subheader(f"📊 Risultati (Ordinati per vicinanza al minimo del {previous_year})")
        
        # Funzione per evidenziare le righe
        def highlight_close_to_min(val):
            color = 'background-color: #ffcccc' if val <= threshold else '' # Rosso chiaro se vicino al minimo
            return color

        # Mostriamo il dataframe con stile
        st.dataframe(
            df.style.map(highlight_close_to_min, subset=['Distanza dal Min (%)'])
            .format({
                "Prezzo Attuale": "{:.2f}", 
                f"Minimo {previous_year}": "{:.2f}", 
                "Distanza dal Min (%)": "{:.2f}%"
            }),
            use_container_width=True,
            hide_index=True
        )

        # --- Visualizzazione Grafica Dettagliata ---
        st.divider()
        st.subheader("🔎 Approfondimento Grafico")
        
        selected_ticker = st.selectbox("Seleziona un titolo per vedere il grafico:", df["Ticker"].unique())
        
        if selected_ticker:
            # Ricarichiamo i dati per il grafico specifico
            ticker_data = yf.download(selected_ticker, start=f"{previous_year}-01-01", progress=False, auto_adjust=True)
            
            # Gestione colonne MultiIndex per yfinance
            if isinstance(ticker_data.columns, pd.MultiIndex):
                plot_close = ticker_data['Close'][selected_ticker]
            else:
                plot_close = ticker_data['Close']

            # Recuperiamo il valore minimo dell'anno precedente per tracciare la linea
            min_val = df[df["Ticker"] == selected_ticker][f"Minimo {previous_year}"].values[0]

            fig = go.Figure()
            
            # Linea del prezzo
            fig.add_trace(go.Scatter(
                x=ticker_data.index, 
                y=plot_close, 
                mode='lines', 
                name='Prezzo Chiusura',
                line=dict(color='#2962FF')
            ))

            # Linea orizzontale del minimo anno precedente
            fig.add_hline(
                y=min_val, 
                line_dash="dash", 
                line_color="red", 
                annotation_text=f"Minimo {previous_year}: {min_val}", 
                annotation_position="bottom right"
            )

            # Rettangolo per evidenziare l'anno precedente
            fig.add_vrect(
                x0=f"{previous_year}-01-01", 
                x1=f"{previous_year}-12-31", 
                fillcolor="gray", opacity=0.1, 
                layer="below", line_width=0,
                annotation_text=f"Anno {previous_year}", annotation_position="top left"
            )

            fig.update_layout(
                title=f"Analisi {selected_ticker}: Prezzo vs Minimo {previous_year}",
                xaxis_title="Data",
                yaxis_title="Prezzo",
                template="plotly_white",
                height=500
            )
            
            st.plotly_chart(fig, use_container_width=True)

    else:
        st.warning("Nessun dato trovato o lista vuota.")