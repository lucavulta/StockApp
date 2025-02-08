import streamlit as st
import pandas as pd
import numpy as np

# Function to calculate safety stock
def calculate_safety_stock(demand_series, lead_time, service_level):
    demand_std = np.std(demand_series)
    z_score = {90: 1.28, 95: 1.65, 99: 2.33}.get(service_level, 1.65)
    safety_stock = z_score * demand_std * np.sqrt(lead_time)
    return round(safety_stock, 1)

# Function to calculate future forecast using moving average
def calculate_moving_average(demand_series, window=3):
    moving_avg = np.convolve(demand_series, np.ones(window)/window, mode='valid')
    return moving_avg[-1] if len(moving_avg) > 0 else 0

# Streamlit app
def main():
    st.title("Safety Stock Calculator")
    
    st.sidebar.header("Parameters")
    lead_time = st.sidebar.number_input("Lead Time (in days)", min_value=1, value=7)
    service_level = st.sidebar.selectbox("Service Level", [90, 95, 99], index=1)
    
    st.sidebar.header("Upload Data")
    uploaded_sales = st.sidebar.file_uploader("Upload Historical Sales Data (CSV)", type=["csv"])
    
    if uploaded_sales is not None:
        sales_data = pd.read_csv(uploaded_sales)
        
        if set(["ArticleID", "Date", "HistoricalSales"]).issubset(sales_data.columns):
            sales_data["Date"] = pd.to_datetime(sales_data["Date"])
            st.write("### Historical Sales Data")
            st.write(sales_data)
            
            uploaded_stock = st.sidebar.file_uploader("Upload Current Stock Levels (CSV)", type=["csv"])
            
            if uploaded_stock is not None:
                stock_data = pd.read_csv(uploaded_stock)
                
                if set(["ArticleID", "CurrentStock"]).issubset(stock_data.columns):
                    st.write("### Current Stock Levels")
                    st.write(stock_data)
                    
                    results = []
                    forecasts = []
                    
                    for article_id in sales_data["ArticleID"].unique():
                        article_sales = sales_data[sales_data["ArticleID"] == article_id]
                        historical_sales = article_sales.sort_values("Date")["HistoricalSales"].values
                        
                        stock_row = stock_data[stock_data["ArticleID"] == article_id]
                        if not stock_row.empty:
                            current_stock_level = stock_row.iloc[0]["CurrentStock"]
                            
                            safety_stock = calculate_safety_stock(historical_sales, lead_time, service_level)
                            forecast = calculate_moving_average(historical_sales)
                            
                            results.append({
                                "ArticleID": article_id,
                                "Safety Stock": safety_stock,
                                "Current Stock": current_stock_level,
                                "Reorder Needed": current_stock_level < safety_stock
                            })
                            
                            forecasts.append({
                                "ArticleID": article_id,
                                "Forecasted Sales": round(forecast, 1)
                            })
                    
                    results_df = pd.DataFrame(results)
                    st.write("### Safety Stock Calculation Results")
                    st.write(results_df)
                    
                    forecasts_df = pd.DataFrame(forecasts)
                    st.write("### Future Sales Forecast (Moving Average)")
                    st.write(forecasts_df)
                    
                    st.download_button(
                        label="Download Results as CSV",
                        data=results_df.to_csv(index=False).encode('utf-8'),
                        file_name="safety_stock_results.csv",
                        mime="text/csv"
                    )
                else:
                    st.error("Stock file must contain 'ArticleID' and 'CurrentStock' columns.")
        else:
            st.error("Sales file must contain 'ArticleID', 'Date', and 'HistoricalSales' columns.")

if __name__ == "__main__":
    main()
