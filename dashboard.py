import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Crypto Dashboard", layout="wide")

@st.cache_data
def load_data():
    df = pd.read_csv("crypto_clean.csv")
    return df

df = load_data()

st.title("🪙 Crypto Dashboard")
st.markdown("Interactive dashboard built from CoinGecko API data")

# --- Sidebar Filters ---
st.sidebar.header("Filters")

# Market Cap Range
cap_min, cap_max = int(df["market_cap"].min()), int(df["market_cap"].max())
market_cap_range = st.sidebar.slider("Market Cap Range", cap_min, cap_max, (cap_min, cap_max))

# Price Range
price_min, price_max = int(df["current_price"].min()), int(df["current_price"].max())
price_range = st.sidebar.slider("Price Range", price_min, price_max, (price_min, price_max))

# ATH Year Filter
ath_years = sorted(df["ath_year"].dropna().unique())
ath_filter = st.sidebar.multiselect("ATH Year", ath_years)

# ATL Year Filter
atl_years = sorted(df["atl_year"].dropna().unique())
atl_filter = st.sidebar.multiselect("ATL Year", atl_years)

# Apply filters
filtered_df = df[
    (df["market_cap"].between(*market_cap_range)) &
    (df["current_price"].between(*price_range))
]
if ath_filter:
    filtered_df = filtered_df[filtered_df["ath_year"].isin(ath_filter)]
if atl_filter:
    filtered_df = filtered_df[filtered_df["atl_year"].isin(atl_filter)]

# --- KPI Cards ---
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Coins", f"{len(filtered_df)}")
col2.metric("Avg Price", f"${filtered_df['current_price'].mean():,.2f}")
col3.metric("Avg Market Cap", f"${filtered_df['market_cap'].mean():,.0f}")
col4.metric("Top ATH Year", int(filtered_df['ath_year'].mode()[0]) if not filtered_df.empty else "NA")
col5.metric("Top ATL Year", int(filtered_df['atl_year'].mode()[0]) if not filtered_df.empty else "NA")

# --- Tabs ---
tab1, tab2, tab3, tab4, tab5 = st.tabs(["Overview", "Market Cap", "Price", "Supply", "ATH/ATL"])

with tab1:
    st.subheader("Top 10 Coins by Market Cap")
    top10 = filtered_df.nlargest(10, "market_cap")
    st.dataframe(top10[["symbol","name","current_price","market_cap","market_cap_rank"]])

    st.subheader("Top 5 Coins Market Share")
    fig = px.pie(top10.head(5), values="market_cap", names="name", title="Top 5 Market Cap Share")
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.subheader("Market Cap Distribution")
    fig = px.histogram(filtered_df, x="market_cap", nbins=40, title="Market Cap Distribution")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Top 10 by Market Cap")
    fig = px.bar(top10, x="market_cap", y="name", orientation="h", title="Top 10 Market Cap")
    st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.subheader("Price Distribution")
    fig = px.histogram(filtered_df, x="current_price", nbins=40, title="Price Distribution")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Top 10 by Price")
    top_price = filtered_df.nlargest(10, "current_price")
    fig = px.bar(top_price, x="current_price", y="name", orientation="h", title="Top 10 Prices")
    st.plotly_chart(fig, use_container_width=True)

with tab4:
    st.subheader("Circulating vs Total Supply Ratio")
    filtered_df["supply_ratio"] = filtered_df["circulating_supply"] / filtered_df["total_supply"]
    fig = px.histogram(filtered_df, x="supply_ratio", nbins=30, title="Supply Ratio Distribution")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Top 10 by Circulating Supply")
    top_supply = filtered_df.nlargest(10, "circulating_supply")
    fig = px.bar(top_supply, x="circulating_supply", y="name", orientation="h", title="Top 10 Circulating Supply")
    st.plotly_chart(fig, use_container_width=True)

with tab5:
    st.subheader("ATH Year Distribution")
    fig = px.histogram(filtered_df, x="ath_year", title="ATH Year Distribution")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("ATL Year Distribution")
    fig = px.histogram(filtered_df, x="atl_year", title="ATL Year Distribution")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Top 10 Farthest Below ATH")
    below_ath = filtered_df.nsmallest(10, "ath_change_percentage")
    fig = px.bar(below_ath, x="ath_change_percentage", y="name", orientation="h", title="Farthest Below ATH (%)")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Top 10 Farthest Above ATL")
    above_atl = filtered_df.nlargest(10, "atl_change_percentage")
    fig = px.bar(above_atl, x="atl_change_percentage", y="name", orientation="h", title="Farthest Above ATL (%)")
    st.plotly_chart(fig, use_container_width=True)
