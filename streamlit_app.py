import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

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

# Function to calculate stock levels over the next 8 weeks
def calculate_future_stock(current_stock, forecast, on_order_data):
    stock_levels = [current_stock]
    for week in range(1, 9):
        stock = stock_levels[-1] - forecast[week-1]
        if not on_order_data.empty:
            stock += on_order_data[on_order_data["Week"] == week]["OnOrder"].sum()
        stock_levels.append(max(stock, 0))  # Ensure stock doesn't go negative
    return stock_levels

# Streamlit app
def main():
    st.title("Safety Stock Calculator")
    
    st.sidebar.header("Parameters")
    lead_time = st.sidebar.number_input("Lead Time (in days)", min_value=1, value=7)
    service_level = st.sidebar.selectbox("Service Level", [90, 95, 99], index=1)
    
    st.sidebar.header("Upload Data")
    uploaded_sales = st.sidebar.file_uploader("Upload Historical Sales Data (CSV)", type=["csv"])
    uploaded_stock = st.sidebar.file_uploader("Upload Current Stock Levels (CSV)", type=["csv"])
    uploaded_on_order = st.sidebar.file_uploader("Upload On Order Data (CSV)", type=["csv"])
    
    if uploaded_sales is not None and uploaded_stock is not None and uploaded_on_order is not None:
        sales_data = pd.read_csv(uploaded_sales)
        stock_data = pd.read_csv(uploaded_stock)
        on_order_data = pd.read_csv(uploaded_on_order)
        
        if set(["ArticleID", "Date", "HistoricalSales"]).issubset(sales_data.columns) and \
           set(["ArticleID", "CurrentStock"]).issubset(stock_data.columns) and \
           set(["ArticleID", "Date", "OnOrder"]).issubset(on_order_data.columns):
            
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
                    
                    safety_stock = calculate_safety_stock(historical_sales, lead_time, service_level)
                    
                    # Calculate weekly forecast
                    weekly_forecast = [calculate_moving_average(historical_sales[-3:]) for _ in range(8)]
                    
                    results.append({
                        "ArticleID": article_id,
                        "Safety Stock": safety_stock,
                        "Current Stock": current_stock_level,
                        "Reorder Needed": current_stock_level < safety_stock
                    })
                    
                    forecasts.append({
                        "ArticleID": article_id,
                        "Forecasted Sales (Next 8 Weeks)": weekly_forecast
                    })
                    
                    on_order_article = on_order_data[on_order_data["ArticleID"] == article_id]
                    stock_levels = calculate_future_stock(current_stock_level, weekly_forecast, on_order_article)
                    stock_projections.append({
                        "ArticleID": article_id,
                        "Stock Levels (Next 8 Weeks)": stock_levels
                    })
            
            results_df = pd.DataFrame(results)
            forecasts_df = pd.DataFrame(forecasts)
            
            st.write("### Safety Stock Calculation Results")
            st.write(results_df)
            
            st.write("### Future Sales Forecast (Moving Average)")
            st.write(forecasts_df)
            
            st.write("### Stock Projection Over Next 8 Weeks")
            article_ids = sales_data["ArticleID"].unique()
            selected_article = st.selectbox("Select ArticleID to visualize", article_ids)
            
            selected_projection = next((proj for proj in stock_projections if proj["ArticleID"] == selected_article), None)
            selected_forecast = next((fcst for fcst in forecasts if fcst["ArticleID"] == selected_article), None)
            
            if selected_projection and selected_forecast:
                fig, ax = plt.subplots()
                ax.plot(range(9), selected_projection["Stock Levels (Next 8 Weeks)"], marker='o', label="Stock Level")
                ax.axhline(y=results_df[results_df["ArticleID"] == selected_article]["Safety Stock"].values[0], color='r', linestyle='--', label="Safety Stock")
                ax.set_xlabel("Weeks")
                ax.set_ylabel("Stock Level")
                ax.set_title(f"Stock Projection for ArticleID {selected_article}")
                ax.legend()
                st.pyplot(fig)
            
            st.download_button(
                label="Download Results as CSV",
                data=results_df.to_csv(index=False).encode('utf-8'),
                file_name="safety_stock_results.csv",
                mime="text/csv"
            )
        else:
            st.error("Please ensure all files contain the required columns.")
    else:
        st.error("Please upload all required data files.")

if __name__ == "__main__":
    main()
