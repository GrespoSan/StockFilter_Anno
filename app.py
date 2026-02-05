import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

st.title("Confronto Prezzo Chiusura vs Minimo Anno Precedente")

# Lista simboli
symbols = ["APA", "BKR", "COP", "CVX", "CTRA", "DVN", "EOG", "EQT",
           "EXE", "FANG", "HAL", "KMI", "MPC", "OKE", "OXY", "PSX",
           "SLB", "TRGP", "TPL", "VLO", "WMB", "XOM"]

st.write(f"Simboli usati: {symbols}")

threshold = st.number_input(
    "Mostra solo titoli entro ±X% dal minimo dell'anno scorso", 
    min_value=0.0, value=5.0, step=0.1
)

# Date
yesterday = datetime.today() - timedelta(days=1)
last_year = yesterday.year - 1
start_date = f"{last_year}-01-01"
end_date = f"{last_year}-12-31"

results = {}

for symbol in symbols:
    try:
        # Minimo anno precedente
        data_last_year = yf.download(symbol, start=start_date, end=end_date)
        if data_last_year.empty:
            st.warning(f"Nessun dato disponibile per {symbol} nell'anno precedente")
            continue
        min_low = data_last_year['Low'].min()

        # Ultimi 30 giorni per prendere l'ultima chiusura valida
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="30d")
        if hist.empty:
            st.warning(f"Nessun dato di chiusura disponibile per {symbol} negli ultimi 30 giorni")
            continue

        # Prendi la chiusura
        if 'Close' in hist.columns:
            close_yesterday = hist.iloc[-1]['Close']
        elif 'Adj Close' in hist.columns:
            close_yesterday = hist.iloc[-1]['Adj Close']
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
