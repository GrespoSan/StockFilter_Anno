import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

st.title("Confronto Prezzo Chiusura Ieri vs Minimo Anno Precedente")

# Caricamento file simboli
uploaded_file = st.file_uploader("Carica un file .txt con i simboli (uno per riga)", type="txt")

if uploaded_file:
    # Legge i simboli dal file
    symbols = [line.strip().upper() for line in uploaded_file.read().decode("utf-8").splitlines() if line.strip()]
    
    st.write(f"Simboli caricati: {symbols}")

    # Soglia percentuale opzionale
    threshold = st.number_input("Mostra solo titoli entro X% dal minimo dell'anno scorso", min_value=0.0, value=5.0, step=0.1)

    # Calcolo date
    yesterday = datetime.today() - timedelta(days=1)
    yesterday_str = yesterday.strftime('%Y-%m-%d')

    last_year = yesterday.year - 1
    start_date = f"{last_year}-01-01"
    end_date = f"{last_year}-12-31"

    results = {}

    for symbol in symbols:
        # Dati anno precedente
        data_last_year = yf.download(symbol, start=start_date, end=end_date)
        if data_last_year.empty:
            st.warning(f"Nessun dato disponibile per {symbol} nell'anno precedente")
            continue

        min_low = data_last_year['Low'].min()

        # Dati chiusura ieri
        data_yesterday = yf.download(symbol, start=yesterday_str, end=yesterday_str)
        if data_yesterday.empty:
            st.warning(f"Nessun dato di chiusura disponibile per {symbol} ieri")
            continue

        close_yesterday = data_yesterday['Close'][0]

        diff_pct = ((close_yesterday - min_low) / min_low) * 100

        # Salva solo se entro la soglia scelta
        if abs(diff_pct) <= threshold:
            results[symbol] = {
                'Min_Anno_Precedente': min_low,
                'Chiusura_Ieri': close_yesterday,
                'Diff_%': diff_pct
            }

    if results:
        df_results = pd.DataFrame(results).T
        df_results = df_results.sort_values(by='Diff_%')
        st.dataframe(df_results)
    else:
        st.info(f"Nessun titolo entro ±{threshold}% dal minimo dell'anno scorso.")
else:
    st.info("Carica un file .txt per iniziare.")
