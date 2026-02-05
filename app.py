import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# Configurazione Pagina
st.set_page_config(page_title="Scanner Rimbalzo Supporto", layout="wide")

if 'df_risultati' not in st.session_state:
    st.session_state.df_risultati = pd.DataFrame()

st.title("📉 Scanner: Ritest del Minimo e Rimbalzo")
st.markdown("Cerca titoli che nel 2026 hanno toccato il minimo del 2025 e ora stanno risalendo.")

# --- Sidebar ---
st.sidebar.header("Parametri")
uploaded_file = st.sidebar.file_uploader("Carica .txt con Ticker", type="txt")
manual_input = st.sidebar.text_area("Oppure inserisci manuale", "PYPL, DIS, INTC, BABA, SBUX")

st.sidebar.subheader("1. Logica del Tocco")
retest_threshold = st.sidebar.slider("Distanza massima del test (%)", 0.0, 5.0, 1.5, 
                                     help="Quanto deve essere andato vicino al minimo 2025 quest'anno?")

st.sidebar.subheader("2. Logica della Risalita")
min_bounce = st.sidebar.slider("Rimbalzo minimo richiesto (%)", 0.0, 20.0, 2.0, 
                               help="Di quanto deve essere risalito dal minimo toccato quest'anno?")

today = datetime.today()
curr_year = today.year
prev_year = curr_year - 1

def fetch_data(ticker_list_raw):
    results = []
    tickers = ticker_list_raw.replace('\n', ',').replace(' ', ',').split(',')
    tickers = [t.strip().upper() for t in tickers if t.strip()]
    
    if not tickers: return pd.DataFrame()

    prog_bar = st.progress(0)
    for i, ticker in enumerate(tickers):
        try:
            data = yf.download(ticker, start=f"{prev_year}-01-01", progress=False, auto_adjust=False)
            if isinstance(data.columns, pd.MultiIndex): data.columns = data.columns.get_level_values(0)

            if not data.empty:
                # 1. Minimo Assoluto 2025
                data_prev = data[data.index.year == prev_year]
                if data_prev.empty: continue
                min_2025 = float(data_prev['Low'].min())
                
                # 2. Analisi 2026
                data_curr = data[data.index.year == curr_year]
                if data_curr.empty: continue
                
                min_2026 = float(data_curr['Low'].min())
                current_price = float(data_curr['Close'].iloc[-1])
                
                # CALCOLO 1: Il prezzo quest'anno è andato vicino al minimo dell'anno scorso?
                # (Minimo 2026 - Minimo 2025) / Minimo 2025
                test_closeness = ((min_2026 - min_2025) / min_2025) * 100
                
                # CALCOLO 2: Quanto è risalito dal punto più basso di quest'anno?
                # (Prezzo Attuale - Minimo 2026) / Minimo 2026
                bounce_perc = ((current_price - min_2026) / min_2026) * 100

                results.append({
                    "Ticker": ticker,
                    "Prezzo Attuale": current_price,
                    "Minimo 2025": min_2025,
                    "Minimo 2026 (Il Tocco)": min_2026,
                    "Vicino al Supporto (%)": test_closeness,
                    "Rimbalzo Effettuato (%)": bounce_perc
                })
        except: continue
        prog_bar.progress((i + 1) / len(tickers))
    prog_bar.empty()
    return pd.DataFrame(results)

if st.sidebar.button("CERCA RITEST E RIMBALZI", type="primary"):
    input_data = uploaded_file.read().decode("utf-8") if uploaded_file else manual_input
    if input_data.strip():
        st.session_state.df_risultati = fetch_data(input_data)

# --- Visualizzazione ---
df = st.session_state.df_risultati

if not df.empty:
    # FILTRO RIGOROSO:
    # 1. Il test deve essere stato entro la soglia (es. il minimo 2026 è vicino al minimo 2025)
    # 2. Il rimbalzo deve essere superiore alla soglia scelta
    mask = (df["Vicino al Supporto (%)"].abs() <= retest_threshold) & (df["Rimbalzo Effettuato (%)"] >= min_bounce)
    filtered = df[mask].sort_values("Rimbalzo Effettuato (%)", ascending=False)

    if not filtered.empty:
        st.subheader(f"✅ Titoli che hanno confermato il supporto e sono risaliti")
        st.dataframe(
            filtered.style.background_gradient(subset=["Rimbalzo Effettuato (%)"], cmap="Greens")
            .format({"Prezzo Attuale": "{:.2f}", "Minimo 2025": "{:.2f}", 
                     "Minimo 2026 (Il Tocco)": "{:.2f}", "Vicino al Supporto (%)": "{:.2f}%", 
                     "Rimbalzo Effettuato (%)": "{:.2f}%"}),
            use_container_width=True, hide_index=True
        )

        st.divider()
        scelta = st.selectbox("Seleziona titolo per il grafico:", filtered["Ticker"].unique())
        
        if scelta:
            dati_plot = yf.download(scelta, start=f"{prev_year}-01-01", progress=False)
            if isinstance(dati_plot.columns, pd.MultiIndex): dati_plot.columns = dati_plot.columns.get_level_values(0)
            
            row = filtered[filtered["Ticker"] == scelta].iloc[0]
            
            fig = go.Figure(data=[go.Candlestick(
                x=dati_plot.index, open=dati_plot['Open'], high=dati_plot['High'],
                low=dati_plot['Low'], close=dati_plot['Close'], name=scelta
            )])
            
            # Linea Minimo 2025 (Il Supporto)
            fig.add_hline(y=row['Minimo 2025'], line_dash="dash", line_color="red", 
                          annotation_text="SUPPORTO 2025")
            
            # Evidenzia il minimo toccato quest'anno
            fig.add_annotation(x=dati_plot[dati_plot.index.year == curr_year]['Low'].idxmin(),
                               y=row['Minimo 2026 (Il Tocco)'], text="IL TOCCO",
                               showarrow=True, arrowhead=2, bgcolor="yellow", font=dict(color="black"))

            fig.update_layout(title=f"{scelta}: Rimbalzo del {row['Rimbalzo Effettuato (%)']:.2f}% dal minimo 2026", 
                              xaxis_rangeslider_visible=False, template="plotly_dark", height=500)
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Nessun titolo soddisfa entrambi i criteri di Test e Rimbalzo.")
else:
    st.info("Avvia la scansione per trovare i segnali.")