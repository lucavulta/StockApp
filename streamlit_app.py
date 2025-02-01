import streamlit as st
import pandas as pd
import numpy as np

# Function to calculate safety stock
def calculate_safety_stock(demand_series, lead_time, service_level):
    # Calculate standard deviation of demand
    demand_std = np.std(demand_series)
    
    # Z-score based on service level (e.g., 95% -> 1.65)
    z_score = {
        90: 1.28,
        95: 1.65,
        99: 2.33
    }.get(service_level, 1.65)  # Default to 95% if not found
    
    # Calculate safety stock and round up to 1 decimal place
    safety_stock = z_score * demand_std * np.sqrt(lead_time)
    return round(safety_stock, 1)

# Function to calculate future forecast using moving average
def calculate_moving_average(demand_series, window=3):
    # Calculate moving average
    moving_avg = np.convolve(demand_series, np.ones(window)/window, mode='valid')
    return moving_avg[-1]  # Return the last value as the forecast

# Streamlit app
def main():
    st.title("Safety Stock Calculator")
    
    # Input for lead time and service level (before file uploads)
    st.sidebar.header("Parameters")
    lead_time = st.sidebar.number_input("Lead Time (in days)", min_value=1, value=7)
    service_level = st.sidebar.selectbox("Service Level", [90, 95, 99], index=1)
    
    # Upload historical sales data
    st.sidebar.header("Upload Data")
    uploaded_file = st.sidebar.file_uploader("Upload Historical Sales Data (CSV)", type=["csv"])
    
    if uploaded_file is not None:
        # Load data
        data = pd.read_csv(uploaded_file)
        st.write("### Historical Sales Data")
        st.write(data)
        
        # Input for current stock levels
        current_stock = st.sidebar.file_uploader("Upload Current Stock Levels (CSV)", type=["csv"])
        
        if current_stock is not None:
            stock_data = pd.read_csv(current_stock)
            st.write("### Current Stock Levels")
            st.write(stock_data)
            
            # Merge historical sales and current stock data
            merged_data = pd.merge(data, stock_data, on="Article ID", how="inner")
            
            # Calculate safety stock for each article
            results = []
            forecasts = []
            for _, row in merged_data.iterrows():
                article_id = row["Article ID"]
                historical_sales = row[1:-1]  # Assuming historical sales are in columns 1 to n-1
                current_stock_level = row["Current Stock"]
                
                # Calculate safety stock
                safety_stock = calculate_safety_stock(historical_sales, lead_time, service_level)
                
                # Calculate future forecast using moving average
                forecast = calculate_moving_average(historical_sales)
                
                results.append({
                    "Article ID": article_id,
                    "Safety Stock": safety_stock,
                    "Current Stock": current_stock_level,
                    "Reorder Needed": current_stock_level < safety_stock
                })
                
                forecasts.append({
                    "Article ID": article_id,
                    "Forecasted Sales": round(forecast, 1)
                })
            
            # Display safety stock results
            results_df = pd.DataFrame(results)
            st.write("### Safety Stock Calculation Results")
            st.write(results_df)
            
            # Display forecast results
            forecasts_df = pd.DataFrame(forecasts)
            st.write("### Future Sales Forecast (Moving Average)")
            st.write(forecasts_df)
            
            # Option to download results
            st.download_button(
                label="Download Results as CSV",
                data=results_df.to_csv(index=False).encode('utf-8'),
                file_name="safety_stock_results.csv",
                mime="text/csv"
            )

if __name__ == "__main__":
    main()
