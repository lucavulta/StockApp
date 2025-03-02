import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import mplcursors  # Per aggiungere i pop-up al grafico

# Function to calculate safety stock
def calculate_safety_stock(demand_series, lead_time, service_level):
    demand_std = np.std(demand_series)
    z_score = {90: 1.28, 91: 1.34, 92: 1.41, 93: 1.48, 94: 1.55, 95: 1.65, 96: 1.75, 97: 1.88, 98: 2.05, 99: 2.33}.get(service_level, 1.65)
    safety_stock = z_score * demand_std * np.sqrt(lead_time)
    return round(safety_stock, 1)

# Function to calculate future forecast using moving average
def calculate_moving_average(demand_series, window=3):
    moving_avg = np.convolve(demand_series, np.ones(window)/window, mode='valid')
    return moving_avg[-1] if len(moving_avg) > 0 else 0

# Function to calculate stock levels over the next 8 weeks
def calculate_future_stock(current_stock, forecast, on_order_data):
    stock_levels = [current_stock]
    for week in range(1, 9):
        stock = stock_levels[-1] - forecast[week-1]
        if not on_order_data.empty:
            stock += on_order_data[on_order_data["Week"] == week]["OnOrder"].sum()
        stock_levels.append(max(stock, 0))  # Ensure stock doesn't go negative
    return stock_levels

# Function to generate export data
def generate_export_data(results_df, stock_projections):
    export_data = []
    for proj in stock_projections:
        article_id = proj["ArticleID"]
        stock_levels = proj["Stock Levels (Next 8 Weeks)"]
        safety_stock = results_df[results_df["ArticleID"] == article_id]["Safety Stock"].values[0]
        reorder_quantity = results_df[results_df["ArticleID"] == article_id]["Reorder Quantity"].values[0]
        
        # Gestione del caso in cui reorder_quantity è "N/A"
        if reorder_quantity == "N/A":
            reorder_quantity_rounded = "N/A"
        else:
            reorder_quantity_rounded = round(reorder_quantity, 1)  # Arrotondamento a una cifra decimale
        
        for week, stock in enumerate(stock_levels):
            export_data.append({
                "Article": article_id,
                "Week": week,
                "Expected Stock": round(stock, 1),  # Arrotondamento a una cifra decimale
                "SafetyStock": round(safety_stock, 1),  # Arrotondamento a una cifra decimale
                "ReorderQuantity": reorder_quantity_rounded if week == 0 else 0  # ReorderQuantity solo per la settimana 0
            })
    return pd.DataFrame(export_data)

# Streamlit app
def main():
    st.title("Safety Stock Calculator")
    
    st.sidebar.header("Parameters")
    service_level = st.sidebar.slider("Service Level", min_value=90, max_value=99, value=95, step=1)  # Slider per il service level
    
    st.sidebar.header("Upload Data")
    uploaded_sales = st.sidebar.file_uploader("Upload Historical Sales Data (CSV)", type=["csv"])
    uploaded_stock = st.sidebar.file_uploader("Upload Current Stock Levels (CSV)", type=["csv"])
    uploaded_on_order = st.sidebar.file_uploader("Upload On Order Data (CSV)", type=["csv"])
    
    if uploaded_sales is not None and uploaded_stock is not None and uploaded_on_order is not None:
        sales_data = pd.read_csv(uploaded_sales)
        stock_data = pd.read_csv(uploaded_stock)
        on_order_data = pd.read_csv(uploaded_on_order)
        
        if set(["ArticleID", "Date", "HistoricalSales"]).issubset(sales_data.columns) and \
           set(["ArticleID", "CurrentStock", "LeadTime", "Reorder LeadTime"]).issubset(stock_data.columns) and \
           set(["ArticleID", "Date", "OnOrder"]).issubset(on_order_data.columns):  # Aggiunta colonna Reorder LeadTime
            
            sales_data["Date"] = pd.to_datetime(sales_data["Date"])
            on_order_data["Date"] = pd.to_datetime(on_order_data["Date"])
            on_order_data["Week"] = (on_order_data["Date"] - pd.Timestamp.today()).dt.days // 7 + 1
            
            st.success("All data uploaded successfully!")
            
            results = []
            forecasts = []
            stock_projections = []
            
            for article_id in sales_data["ArticleID"].unique():
                article_sales = sales_data[sales_data["ArticleID"] == article_id]
                historical_sales = article_sales.sort_values("Date")["HistoricalSales"].values
                
                stock_row = stock_data[stock_data["ArticleID"] == article_id]
                if not stock_row.empty:
                    current_stock_level = stock_row.iloc[0]["CurrentStock"]
                    lead_time = stock_row.iloc[0]["LeadTime"]  # Legge il lead time dal file CurrentStock
                    reorder_lead_time = stock_row.iloc[0]["Reorder LeadTime"]  # Legge il Reorder LeadTime dal file CurrentStock
                    
                    safety_stock = calculate_safety_stock(historical_sales, lead_time, service_level)
                    
                    # Calculate weekly forecast
                    weekly_forecast = [calculate_moving_average(historical_sales[-3:]) for _ in range(8)]
                    avg_weekly_forecast = round(np.mean(weekly_forecast), 1)
                    
                    on_order_article = on_order_data[on_order_data["ArticleID"] == article_id]
                    stock_levels = calculate_future_stock(current_stock_level, weekly_forecast, on_order_article)
                    
                    # Find the week when stock goes below safety stock
                    safety_stock_week = next((i for i, x in enumerate(stock_levels) if x < safety_stock), None)
                    safety_stock_week = safety_stock_week - 1 if safety_stock_week is not None and safety_stock_week > 0 else "N/A"
                    
                    # Find the week when stock goes to 0
                    stock_out_week = next((i for i, x in enumerate(stock_levels) if x == 0), None)
                    stock_out_week = stock_out_week if stock_out_week is not None else "N/A"
                    
                    # Calculate Reorder Week
                    reorder_week = 0 + reorder_lead_time  # Reorder Week = 0 + Reorder LeadTime
                    
                    # Calculate Reorder Quantity
                    if safety_stock_week != "N/A":
                        stock_at_lead_time = stock_levels[reorder_lead_time]
                        on_order_at_lead_time = on_order_article[on_order_article["Week"] == reorder_lead_time]["OnOrder"].sum()
                        reorder_quantity = (avg_weekly_forecast * reorder_lead_time) + safety_stock - stock_at_lead_time - on_order_at_lead_time
                        reorder_quantity = round(reorder_quantity, 1)
                    else:
                        reorder_quantity = "N/A"
                    
                    results.append({
                        "ArticleID": article_id,
                        "Current Stock": round(current_stock_level, 1),
                        "Lead Time": lead_time,  # Aggiunta della colonna Lead Time
                        "Reorder LeadTime": reorder_lead_time,  # Aggiunta della colonna Reorder LeadTime
                        "Safety Stock": safety_stock,
                        "Average Weekly Forecast": avg_weekly_forecast,
                        "Safety Stock Week": safety_stock_week,
                        "Stock Out Week": stock_out_week,
                        "Reorder Quantity": reorder_quantity,
                        "Reorder Needed": current_stock_level < safety_stock
                    })
                    
                    stock_projections.append({
                        "ArticleID": article_id,
                        "Stock Levels (Next 8 Weeks)": stock_levels,
                        "Reorder Week": reorder_week  # Aggiunta della Reorder Week per il grafico
                    })
            
            results_df = pd.DataFrame(results)
            
            # Reorder columns (rimuovere Reorder Week)
            results_df = results_df[["ArticleID", "Current Stock", "Lead Time", "Reorder LeadTime", "Safety Stock", "Average Weekly Forecast", "Safety Stock Week", "Stock Out Week", "Reorder Quantity", "Reorder Needed"]]
            
            st.write("### Safety Stock Calculation Results")
            
            # Formattazione condizionale per i valori numerici
            def format_value(x):
                if isinstance(x, (int, float)) and x != "N/A":
                    return f"{x:.1f}"
                return x
            
            # Applica la formattazione solo alle colonne numeriche
            formatted_df = results_df.copy()
            for col in ["Current Stock", "Lead Time", "Reorder LeadTime", "Safety Stock", "Average Weekly Forecast", "Reorder Quantity"]:
                formatted_df[col] = formatted_df[col].apply(format_value)
            
            # Allineamento al centro delle colonne
            st.dataframe(formatted_df.style.applymap(lambda x: 'color: red' if x == "N/A" else 'color: black').set_properties(**{'text-align': 'center'}))
            
            st.write("### Stock Projection Over Next 8 Weeks")
            article_ids = sales_data["ArticleID"].unique()
            selected_article = st.selectbox("Select ArticleID to visualize", article_ids)
            
            selected_projection = next((proj for proj in stock_projections if proj["ArticleID"] == selected_article), None)
            
            if selected_projection:
                fig, ax = plt.subplots()
                ax.plot(range(9), selected_projection["Stock Levels (Next 8 Weeks)"], marker='o', label="Stock Level")
                ax.axhline(y=results_df[results_df["ArticleID"] == selected_article]["Safety Stock"].values[0], color='r', linestyle='--', label="Safety Stock")
                
                # Aggiungi la linea verticale tratteggiata per la Reorder Week
                reorder_week = selected_projection["Reorder Week"]
                ax.axvline(x=reorder_week, color='g', linestyle='--', label=f"Reorder Week ({reorder_week})")
                
                ax.set_xlabel("Weeks")
                ax.set_ylabel("Stock Level")
                ax.set_title(f"Stock Projection for ArticleID {selected_article}")
                ax.legend()

                # Aggiungi i pop-up con mplcursors
                cursor = mplcursors.cursor(ax, hover=True)
                @cursor.connect("add")
                def on_add(sel):
                    week = sel.target[0]
                    stock_level = sel.target[1]
                    safety_stock = results_df[results_df["ArticleID"] == selected_article]["Safety Stock"].values[0]
                    sel.annotation.set_text(f"Week: {week}\nStock Level: {stock_level}\nSafety Stock: {safety_stock}")
                
                st.pyplot(fig)
            
            # Generate export data
            export_df = generate_export_data(results_df, stock_projections)
            
            st.download_button(
                label="Download Results as CSV",
                data=results_df.to_csv(index=False).encode('utf-8'),
                file_name="safety_stock_results.csv",
                mime="text/csv"
            )
            
            st.download_button(
                label="Download Export Data as CSV",
                data=export_df.to_csv(index=False).encode('utf-8'),
                file_name="export_data.csv",
                mime="text/csv"
            )
        else:
            st.error("Please ensure all files contain the required columns.")
    else:
        st.error("Please upload all required data files.")

if __name__ == "__main__":
    main()
