import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

st.title("Confronto Prezzo Chiusura vs Minimo Anno Precedente")

# Caricamento file simboli
uploaded_file = st.file_uploader("Carica un file .txt con i simboli (uno per riga)", type="txt")

if uploaded_file:
    symbols = [line.strip().upper() for line in uploaded_file.read().decode("utf-8").splitlines() if line.strip()]
    st.write(f"Simboli caricati: {symbols}")

    threshold = st.number_input(
        "Mostra solo titoli entro ±X% dal minimo dell'anno scorso", 
        min_value=0.0, value=5.0, step=0.1
    )

    yesterday = datetime.today() - timedelta(days=1)
    last_year = yesterday.year - 1
    start_date = f"{last_year}-01-01"
    end_date = f"{last_year}-12-31"

    results = {}

    for symbol in symbols:
        try:
            # Dati anno precedente
            data_last_year = yf.download(symbol, start=start_date, end=end_date)
            if data_last_year.empty:
                st.warning(f"Nessun dato disponibile per {symbol} nell'anno precedente")
                continue

            min_low = data_last_year['Low'].min()

            # Ultimi 10 giorni per essere sicuri di avere una chiusura valida
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="10d")
            if hist.empty:
                st.warning(f"Nessun dato di chiusura disponibile per {symbol} negli ultimi 10 giorni")
                continue

            # Prendi la colonna 'Close' se esiste, altrimenti 'Adj Close'
            if 'Close' in hist.columns:
                close_yesterday = hist['Close'][-1]
            elif 'Adj Close' in hist.columns:
                close_yesterday = hist['Adj Close'][-1]
            else:
                st.warning(f"Colonna Close/Adj Close non trovata per {symbol}")
                continue

            diff_pct = ((close_yesterday - min_low) / min_low) * 100

            if abs(diff_pct) <= threshold:
                results[symbol] = {
                    'Min_Anno_Precedente': min_low,
                    'Chiusura_Recente': close_yesterday,
                    'Diff_%': diff_pct
                }

        except Exception as e:
            st.error(f"Errore con {symbol}: {e}")
            continue

    if results:
        df_results = pd.DataFrame(results).T.sort_values(by='Diff_%')
        st.dataframe(df_results)
    else:
        st.info(f"Nessun titolo entro ±{threshold}% dal minimo dell'anno scorso.")

else:
    st.info("Carica un file .txt per iniziare.")
