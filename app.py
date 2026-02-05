import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# Configurazione Pagina
st.set_page_config(page_title="Scanner Minimi & Ritest", layout="wide")

# --- Session State ---
if 'df_risultati' not in st.session_state:
    st.session_state.df_risultati = pd.DataFrame()

st.title("📉 Scanner Supporti: Minimi {prev_year} & Ritest 2026")

# --- Sidebar ---
st.sidebar.header("Parametri")
uploaded_file = st.sidebar.file_uploader("Carica .txt", type="txt")
manual_input = st.sidebar.text_area("Ticker manuali", "AAPL, MSFT, TSLA, NVDA, PYPL, DIS, INTC")

# Parametri Filtro
threshold = st.sidebar.slider("Distanza dal minimo (%)", 0.0, 10.0, 3.0, step=0.5)
st.sidebar.markdown("---")
st.sidebar.subheader("Logica Ritest")
retest_zone = st.sidebar.slider("Soglia zona ritest (%)", 0.1, 5.0, 1.5, help="Entro quale % dal minimo consideriamo un 'tocco'?")

# Date
today = datetime.today()
curr_year = today.year # 2026
prev_year = curr_year - 1 # 2025

def fetch_data(ticker_list_raw):
    results = []
    tickers = ticker_list_raw.replace('\n', ',').replace(' ', ',').split(',')
    tickers = [t.strip().upper() for t in tickers if t.strip()]
    
    if not tickers: return pd.DataFrame()

    prog_bar = st.progress(0)
    status_text = st.empty()
    
    for i, ticker in enumerate(tickers):
        status_text.text(f"Analisi {ticker}...")
        try:
            # Scarichiamo dati dal 2025 ad oggi
            data = yf.download(ticker, start=f"{prev_year}-01-01", progress=False, auto_adjust=False)
            
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)

            if not data.empty:
                # 1. Minimo Anno Precedente (2025)
                data_prev = data[data.index.year == prev_year]
                if data_prev.empty: continue
                min_2025 = float(data_prev['Low'].min())
                
                # 2. Dati Anno Corrente (2026)
                data_curr = data[data.index.year == curr_year]
                if data_curr.empty: continue
                
                last_price = float(data_curr['Close'].iloc[-1])
                dist_perc = ((last_price - min_2025) / min_2025) * 100
                
                # 3. LOGICA RITEST: quante volte il Low del 2026 è entrato nella zona?
                # Zona = Min 2025 * (1 + soglia zone)
                upper_bound = min_2025 * (1 + (retest_zone / 100))
                # Contiamo i giorni in cui il minimo di giornata ha toccato la zona
                touches = data_curr[data_curr['Low'] <= upper_bound]
                num_retests = len(touches)

                results.append({
                    "Ticker": ticker,
                    "Prezzo": last_price,
                    "Min_2025": min_2025,
                    "Distanza_%": dist_perc,
                    "Num_Ritest_2026": num_retests
                })
        except:
            continue
        prog_bar.progress((i + 1) / len(tickers))
    
    prog_bar.empty()
    status_text.empty()
    return pd.DataFrame(results)

# --- Pulsante Esecuzione ---
if st.sidebar.button("ANALIZZA MERCATO", type="primary"):
    input_data = uploaded_file.read().decode("utf-8") if uploaded_file else manual_input
    if input_data.strip():
        st.session_state.df_risultati = fetch_data(input_data)

# --- Risultati ---
df_res = st.session_state.df_risultati

if not df_res.empty:
    # Applichiamo il filtro distanza
    filtered = df_res[df_res["Distanza_%"] <= threshold].sort_values("Num_Ritest_2026", ascending=False)

    if not filtered.empty:
        st.subheader(f"Titoli nel range del {threshold}% dal minimo {prev_year}")
        
        # Coloriamo la colonna ritest per evidenziare i ritest multipli
        st.dataframe(
            filtered.style.background_gradient(subset=["Num_Ritest_2026"], cmap="YlGn")
            .format({"Prezzo": "{:.2f}", "Min_2025": "{:.2f}", "Distanza_%": "{:.2f}%"}),
            use_container_width=True, hide_index=True
        )

        st.divider()
        
        # Selezione Grafico
        col1, col2 = st.columns([1, 3])
        with col1:
            scelta = st.selectbox("Dettaglio Titolo:", filtered["Ticker"].unique())
            info = filtered[filtered["Ticker"] == scelta].iloc[0]
            st.metric("Ritest nel 2026", int(info['Num_Ritest_2026']))
            st.write(f"Il prezzo ha toccato la zona di supporto (entro il {retest_zone}%) per **{int(info['Num_Ritest_2026'])}** giorni quest'anno.")

        with col2:
            dati_plot = yf.download(scelta, start=f"{prev_year}-01-01", progress=False)
            if isinstance(dati_plot.columns, pd.MultiIndex): dati_plot.columns = dati_plot.columns.get_level_values(0)
            
            fig = go.Figure(data=[go.Candlestick(
                x=dati_plot.index, open=dati_plot['Open'], high=dati_plot['High'],
                low=dati_plot['Low'], close=dati_plot['Close'], name=scelta
            )])
            
            # Linea Minimo 2025
            fig.add_hline(y=info['Min_2025'], line_dash="dash", line_color="red", 
                          annotation_text="SUPPORTO 2025", annotation_position="bottom right")
            
            # Fascia Ritest (Zona)
            fig.add_hrect(y0=info['Min_2025'], y1=info['Min_2025']*(1+(retest_zone/100)), 
                          fillcolor="green", opacity=0.1, line_width=0, name="Zona Ritest")

            fig.update_layout(title=f"{scelta}: Analisi Supporto e Ritest", 
                              xaxis_rangeslider_visible=False, template="plotly_dark", height=500)
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Nessun titolo trovato con i parametri attuali.")
else:
    st.info("Avvia la scansione per vedere i dati.")