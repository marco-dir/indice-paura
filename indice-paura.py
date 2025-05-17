import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

# Configurazione pagina
st.set_page_config(
    page_title="Rapporto VIX/S&P500",
    page_icon="📈",
    layout="wide"
)

# Titolo dell'app
st.title("Indice della Paura: Rapporto VIX/S&P500")

# Sidebar per i parametri dell'utente
st.sidebar.header("Parametri")

# Selezione intervallo di date
today = datetime.now()
default_start = today - timedelta(days=365*5)  # Default: 5 anni

start_date = st.sidebar.date_input(
    "Data di inizio",
    value=default_start,
    max_value=today
)

end_date = st.sidebar.date_input(
    "Data di fine",
    value=today,
    min_value=start_date,
    max_value=today
)

# Checkbox per mostrare/nascondere componenti
show_ma = st.sidebar.checkbox("Mostra media mobile (20 giorni)", value=True)
show_bb = st.sidebar.checkbox("Mostra Bande di Bollinger", value=True)
show_vix = st.sidebar.checkbox("Mostra VIX", value=True)
show_sp500 = st.sidebar.checkbox("Mostra S&P500", value=True)

# Download dei dati
@st.cache_data(ttl=3600)  # Cache per 1 ora
def get_data(start_date, end_date):
    try:
        # Download dati VIX e S&P500
        vix_data = yf.download("^VIX", start=start_date, end=end_date)
        sp500_data = yf.download("^GSPC", start=start_date, end=end_date)
        
        # Verifica che i dati siano stati scaricati correttamente
        if vix_data.empty or sp500_data.empty:
            st.error("Impossibile scaricare i dati. Controlla la connessione internet.")
            return None
        
        # Funzione per ottenere la colonna di chiusura preferibile
        def get_close_price(data):
            if 'Adj Close' in data.columns:
                return data['Adj Close']
            elif 'Close' in data.columns:
                return data['Close']
            else:
                # Se i dati sono multi-level (quando yfinance ritorna più ticker)
                for col in data.columns:
                    if 'Adj Close' in str(col) or 'Close' in str(col):
                        return data[col]
                return data.iloc[:, -1]  # Ultima colonna come fallback
        
        # Assicuriamoci che i dati siano allineati
        combined_data = pd.DataFrame()
        combined_data['VIX'] = get_close_price(vix_data)
        combined_data['SP500'] = get_close_price(sp500_data)
        
        # Rimuovi righe con valori NaN
        combined_data = combined_data.dropna()
        
        if combined_data.empty:
            st.error("Nessun dato valido trovato per il periodo selezionato.")
            return None
        
        # Calcola il rapporto VIX/S&P500 (moltiplicato per 1000 per maggiore leggibilità)
        combined_data['Ratio'] = (combined_data['VIX'] / combined_data['SP500']) * 1000
        
        # Aggiungi la media mobile a 20 giorni
        ma_window = 20
        combined_data[f'Ratio_MA_{ma_window}'] = combined_data['Ratio'].rolling(window=ma_window).mean()
        
        # Calcola le Bande di Bollinger
        bb_period = 20
        bb_std = 2
        combined_data['BB_Middle'] = combined_data['Ratio'].rolling(window=bb_period).mean()
        bb_rolling_std = combined_data['Ratio'].rolling(window=bb_period).std()
        combined_data['BB_Upper'] = combined_data['BB_Middle'] + (bb_rolling_std * bb_std)
        combined_data['BB_Lower'] = combined_data['BB_Middle'] - (bb_rolling_std * bb_std)
        
        return combined_data
    except Exception as e:
        st.error(f"Errore nel download dei dati: {e}")
        st.info("Suggerimento: Prova a modificare l'intervallo di date o riprova più tardi.")
        return None

# Funzione principale
def main():
    # Visualizza un messaggio di caricamento
    with st.spinner('Scaricamento dati in corso...'):
        data = get_data(start_date, end_date)
    
    if data is not None and not data.empty:
        # Informazioni sui dati
        st.subheader("Informazioni sugli Indici")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            vix_current = data['VIX'].iloc[-1]
            vix_previous = data['VIX'].iloc[-2]
            vix_change = vix_current - vix_previous
            vix_change_pct = (vix_change / vix_previous) * 100
            st.metric(
                "VIX (Ultimo valore)", 
                f"{vix_current:.2f}",
                f"{vix_change:.2f} ({vix_change_pct:+.2f}%)"
            )
        
        with col2:
            sp500_current = data['SP500'].iloc[-1]
            sp500_previous = data['SP500'].iloc[-2]
            sp500_change = sp500_current - sp500_previous
            sp500_change_pct = (sp500_change / sp500_previous) * 100
            st.metric(
                "S&P500 (Ultimo valore)", 
                f"{sp500_current:.2f}",
                f"{sp500_change:.2f} ({sp500_change_pct:+.2f}%)"
            )
            
        with col3:
            ratio_current = data['Ratio'].iloc[-1]
            ratio_previous = data['Ratio'].iloc[-2]
            ratio_change = ratio_current - ratio_previous
            ratio_change_pct = (ratio_change / ratio_previous) * 100
            st.metric(
                "Rapporto VIX/S&P500 (×1000)", 
                f"{ratio_current:.2f}",
                f"{ratio_change:.2f} ({ratio_change_pct:+.2f}%)"
            )
        
        # Crea grafico principale
        st.subheader("Grafico Storico")
        
        # Determina se mostrare uno o due grafici
        show_secondary = show_vix or show_sp500
        
        if show_secondary:
            # Crea sottografici
            fig = make_subplots(rows=2, cols=1, 
                               shared_xaxes=True, 
                               vertical_spacing=0.1,
                               row_heights=[0.7, 0.3],
                               subplot_titles=("Rapporto VIX/S&P500", "Indici"))
        else:
            # Crea un singolo grafico
            fig = go.Figure()
        
        # Grafico principale - Rapporto VIX/S&P500
        fig.add_trace(
            go.Scatter(
                x=data.index, 
                y=data['Ratio'],
                name="Rapporto VIX/S&P500",
                line=dict(color='blue', width=1)
            ),
            row=1 if show_secondary else None, 
            col=1 if show_secondary else None
        )
        
        # Aggiungi media mobile (20 giorni)
        if show_ma:
            fig.add_trace(
                go.Scatter(
                    x=data.index, 
                    y=data['Ratio_MA_20'],
                    name="Media Mobile (20 giorni)",
                    line=dict(color='red', width=2)
                ),
                row=1 if show_secondary else None, 
                col=1 if show_secondary else None
            )
        
        # Aggiungi Bande di Bollinger
        if show_bb:
            # Banda superiore
            fig.add_trace(
                go.Scatter(
                    x=data.index,
                    y=data['BB_Upper'],
                    name="Bollinger Superiore",
                    line=dict(color='gray', width=1, dash='dash'),
                    showlegend=True
                ),
                row=1 if show_secondary else None, 
                col=1 if show_secondary else None
            )
            
            # Banda inferiore
            fig.add_trace(
                go.Scatter(
                    x=data.index,
                    y=data['BB_Lower'],
                    name="Bollinger Inferiore",
                    line=dict(color='gray', width=1, dash='dash'),
                    fill='tonexty',
                    fillcolor='rgba(128,128,128,0.1)',
                    showlegend=True
                ),
                row=1 if show_secondary else None, 
                col=1 if show_secondary else None
            )
            
            # Banda centrale (media)
            fig.add_trace(
                go.Scatter(
                    x=data.index,
                    y=data['BB_Middle'],
                    name="Bollinger Media",
                    line=dict(color='purple', width=1, dash='dot'),
                    showlegend=True
                ),
                row=1 if show_secondary else None, 
                col=1 if show_secondary else None
            )
        
        # Grafico secondario - VIX e S&P500 (normalizzati) - solo se necessario
        if show_secondary:
            if show_vix:
                fig.add_trace(
                    go.Scatter(
                        x=data.index, 
                        y=data['VIX'],
                        name="VIX",
                        line=dict(color='orange', width=1)
                    ),
                    row=2, col=1
                )
            
            if show_sp500:
                # Normalizza S&P500 per una migliore visualizzazione
                norm_factor = data['VIX'].mean() / data['SP500'].mean()
                fig.add_trace(
                    go.Scatter(
                        x=data.index, 
                        y=data['SP500'] * norm_factor,
                        name="S&P500 (normalizzato)",
                        line=dict(color='green', width=1)
                    ),
                    row=2, col=1
                )
        
        # Layout migliorato per l'asse temporale
        fig.update_layout(
            height=800,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            template="plotly_white",
            # Configurazione dell'asse X migliorata
            xaxis=dict(
                tickformat='%Y-%m',  # Formato anno-mese
                dtick='M6',  # Tick ogni 6 mesi
                tickangle=45,  # Angolo dei tick per una migliore leggibilità
                showgrid=True,
                gridcolor='lightgray',
                title="Data"
            )
        )
        
        # Se abbiamo sottografici, configura anche l'asse X del secondo grafico
        if show_secondary:
            fig.update_xaxes(
                tickformat='%Y-%m',
                dtick='M6',
                tickangle=45,
                showgrid=True,
                gridcolor='lightgray',
                title="Data",
                row=2, col=1
            )
            # Configura anche il primo grafico se è un subplot
            fig.update_xaxes(
                tickformat='%Y-%m',
                dtick='M6',
                tickangle=45,
                showgrid=True,
                gridcolor='lightgray',
                row=1, col=1
            )
        
        # Titoli degli assi Y
        if show_secondary:
            fig.update_yaxes(title_text="Rapporto VIX/S&P500 (×1000)", row=1, col=1)
            fig.update_yaxes(title_text="Valore Indice", row=2, col=1)
        else:
            fig.update_yaxes(title_text="Rapporto VIX/S&P500 (×1000)")
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Analisi statistica
        st.subheader("📊 Analisi Statistica")
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("Statistiche sul rapporto VIX/S&P500:")
            stats_df = pd.DataFrame({
                'Statistiche': ["Media", "Mediana", "Minimo", "Massimo", "Deviazione Standard"],
                'Valore': [
                    f"{data['Ratio'].mean():.2f}",
                    f"{data['Ratio'].median():.2f}",
                    f"{data['Ratio'].min():.2f}",
                    f"{data['Ratio'].max():.2f}",
                    f"{data['Ratio'].std():.2f}"
                ]
            })
            st.dataframe(stats_df, hide_index=True)
            
            # Aggiungi informazioni sulle Bande di Bollinger
            st.write("Posizione rispetto alle Bande di Bollinger:")
            current_ratio = data['Ratio'].iloc[-1]
            current_bb_upper = data['BB_Upper'].iloc[-1]
            current_bb_lower = data['BB_Lower'].iloc[-1]
            current_bb_middle = data['BB_Middle'].iloc[-1]
            
            if current_ratio > current_bb_upper:
                bb_position = "Sopra la banda superiore (ipercomprato)"
                bb_color = "red"
            elif current_ratio < current_bb_lower:
                bb_position = "Sotto la banda inferiore (ipervenduto)"
                bb_color = "green"
            else:
                bb_position = "All'interno delle bande"
                bb_color = "blue"
                
            st.markdown(f"**Stato attuale**: :{bb_color}[{bb_position}]")
            st.write(f"Banda superiore: {current_bb_upper:.2f}")
            st.write(f"Media: {current_bb_middle:.2f}")
            st.write(f"Banda inferiore: {current_bb_lower:.2f}")
            
        with col2:
            # Calcola i percentili
            percentiles = [10, 25, 50, 75, 90]
            percentile_values = [data['Ratio'].quantile(p/100) for p in percentiles]
            
            # Crea DataFrame per i percentili
            percentile_df = pd.DataFrame({
                'Percentile': [f"{p}%" for p in percentiles],
                'Valore': [f"{val:.2f}" for val in percentile_values]
            })
            
            st.write("Percentili del rapporto:")
            st.dataframe(percentile_df, hide_index=True)
            
            # Classifica il valore attuale
            current_ratio = data['Ratio'].iloc[-1]
            current_percentile = (data['Ratio'] <= current_ratio).mean() * 100
            
            st.write(f"**Valore attuale: {current_ratio:.2f}** (percentile {current_percentile:.1f}%)")
        
        # Tabella dati
        with st.expander("Mostra dati grezzi"):
            st.dataframe(data)
            
            # Pulsante per scaricare i dati
            csv = data.to_csv().encode('utf-8')
            st.download_button(
                label="📥 Scarica dati CSV",
                data=csv,
                file_name=f"vix_sp500_ratio_{start_date}_to_{end_date}.csv",
                mime="text/csv",
            )
            
    else:
        st.error("Nessun dato disponibile per il periodo selezionato. Prova a modificare l'intervallo di date o riprova più tardi.")

    # Footer
    st.markdown("---")
    st.caption("Dati forniti da Yahoo Finance. Aggiornato: " + str(datetime.now().strftime("%d/%m/%Y %H:%M:%S")))

if __name__ == "__main__":
    main()
