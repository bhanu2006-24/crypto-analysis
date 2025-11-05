import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from datetime import datetime

# ------------------------------
# PAGE CONFIG
# ------------------------------
st.set_page_config(page_title="Crypto Analytics Suite", layout="wide")

# ------------------------------
# CONSTANTS
# ------------------------------
MAX_PER_PAGE = 250
SELECTED_COLS = [
    "symbol", "name", "image",
    "current_price", "market_cap", "market_cap_rank", "total_volume",
    "circulating_supply", "total_supply",
    "ath", "ath_change_percentage", "ath_date",
    "atl", "atl_change_percentage", "atl_date"
]

# ------------------------------
# FETCHING
# ------------------------------
def fetch_coins_markets(vs_currency="usd", target_size=1000, order="market_cap_desc"):
    rows = []
    pages = (target_size // MAX_PER_PAGE) + (1 if target_size % MAX_PER_PAGE else 0)
    for page in range(1, pages + 1):
        params = {
            "vs_currency": vs_currency,
            "order": order,
            "per_page": MAX_PER_PAGE,
            "page": page,
            "sparkline": False
        }
        r = requests.get("https://api.coingecko.com/api/v3/coins/markets", params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        if not data:
            break
        rows.extend(data)
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    for c in SELECTED_COLS:
        if c not in df.columns:
            df[c] = pd.NA
    df = df[SELECTED_COLS]
    df = df.drop_duplicates(subset=["symbol", "name"])
    return df

# ------------------------------
# CLEANING
# ------------------------------
def clean_crypto_df(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    num_cols = [
        "current_price", "market_cap", "market_cap_rank", "total_volume",
        "circulating_supply", "total_supply", "ath", "atl",
        "ath_change_percentage", "atl_change_percentage"
    ]
    for col in num_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    round_int_cols = ["current_price","market_cap","market_cap_rank","total_volume","circulating_supply","total_supply","ath","atl"]
    for col in round_int_cols:
        df[col] = df[col].round().astype("Int64")
    for col in ["ath_change_percentage","atl_change_percentage"]:
        df[col] = df[col].round(2)
    for col in ["ath_date", "atl_date"]:
        df[col] = pd.to_datetime(df[col], errors="coerce")
    df["ath_year"] = df["ath_date"].dt.year
    df["ath_month"] = df["ath_date"].dt.month
    df["atl_year"] = df["atl_date"].dt.year
    df["atl_month"] = df["atl_date"].dt.month
    df["supply_ratio"] = (df["circulating_supply"] / df["total_supply"]).replace([pd.NA, float("inf")], pd.NA)
    df["market_cap_rank"] = df["market_cap_rank"].astype("Int64")
    df = df.sort_values(by=["market_cap_rank"], na_position="last")
    return df

# ------------------------------
# PIPELINE
# ------------------------------
@st.cache_data(show_spinner=False)
def pipeline(vs_currency: str, target_size: int):
    raw = fetch_coins_markets(vs_currency=vs_currency, target_size=target_size)
    clean = clean_crypto_df(raw.copy())
    return clean, len(raw)

# ------------------------------
# SIDEBAR
# ------------------------------
st.sidebar.title("Controls")
vs_currency = st.sidebar.selectbox("Currency", ["usd", "inr", "eur", "gbp", "jpy"], index=0)
target_size = st.sidebar.selectbox("Target coins to load", [500, 1000, 5000, 10000], index=1)
refresh = st.sidebar.button("🔄 Refresh data now")

if refresh:
    st.cache_data.clear()

# ------------------------------
# DATA LOAD
# ------------------------------
with st.spinner("Fetching live data from CoinGecko..."):
    df, raw_count = pipeline(vs_currency=vs_currency, target_size=target_size)

st.title("🪙 Crypto Analytics Suite")
st.caption(f"Currency: {vs_currency.upper()} • Requested: {target_size} • Fetched: {raw_count} • Unique after cleaning: {len(df)}")
st.divider()

if df.empty:
    st.warning("No data returned. Try lowering target size or changing currency.")
    st.stop()

# ------------------------------
# GLOBAL FILTERS
# ------------------------------
col_f1, col_f2, col_f3 = st.columns([2,2,2])
with col_f1:
    search = st.text_input("Search (by name or symbol)", "", placeholder="e.g., btc, eth, sol")
with col_f2:
    cap_min, cap_max = int(df["market_cap"].min(skipna=True)), int(df["market_cap"].max(skipna=True))
    market_cap_range = st.slider("Market Cap Range", min_value=cap_min, max_value=cap_max, value=(cap_min, cap_max))
with col_f3:
    price_min, price_max = int(df["current_price"].min(skipna=True)), int(df["current_price"].max(skipna=True))
    price_range = st.slider("Price Range", min_value=price_min, max_value=price_max, value=(price_min, price_max))

fdf = df.copy()
if search.strip():
    s = search.strip().lower()
    fdf = fdf[fdf["name"].str.lower().str.contains(s, na=False) | fdf["symbol"].str.lower().str.contains(s, na=False)]
fdf = fdf[
    (fdf["market_cap"].fillna(0).between(*market_cap_range)) &
    (fdf["current_price"].fillna(0).between(*price_range))
]

col_y1, col_y2 = st.columns(2)
with col_y1:
    ath_years = sorted([int(y) for y in fdf["ath_year"].dropna().unique()])
    ath_sel = st.multiselect("Filter by ATH year", ath_years)
with col_y2:
    atl_years = sorted([int(y) for y in fdf["atl_year"].dropna().unique()])
    atl_sel = st.multiselect("Filter by ATL year", atl_years)

if ath_sel:
    fdf = fdf[fdf["ath_year"].isin(ath_sel)]
if atl_sel:
    fdf = fdf[fdf["atl_year"].isin(atl_sel)]

# ------------------------------
# KPI CARDS (Responsive)
# ------------------------------
if st.sidebar.checkbox("Mobile mode", value=False):
    k1, k2 = st.columns(2)
    k3, k4 = st.columns(2)
    k5, = st.columns(1)
else:
    k1, k2, k3, k4, k5 = st.columns(5)

k1.metric("Coins", f"{len(fdf)}")
k2.metric("Avg Price", f"{fdf['current_price'].mean(skipna=True):,.2f}")
k3.metric("Avg Market Cap", f"{fdf['market_cap'].mean(skipna=True):,.0f}")
k4.metric("Median Supply Ratio", f"{fdf['supply_ratio'].median(skipna=True):.2f}" if fdf["supply_ratio"].notna().any() else "NA")
if fdf["atl_change_percentage"].notna().any():
    top_above_atl = fdf.loc[fdf["atl_change_percentage"].idxmax()]["name"]
    k5.metric("Farthest above ATL", top_above_atl)
else:
    k5.metric("Farthest above ATL", "NA")

st.divider()

# ------------------------------
# TABS
# ------------------------------
# ------------------------------
# TABS
# ------------------------------
tab_overview, tab_marketcap, tab_price, tab_supply, tab_athatl, tab_table = st.tabs(
    ["Overview", "Market Share", "Prices", "Supply", "ATH/ATL", "Table"]
)

# --- Overview ---
with tab_overview:
    st.subheader("Top coins by market cap")
    topN = st.slider("Select top N", 5, 50, 10)
    top_df = fdf.nsmallest(topN, "market_cap_rank", keep="all") if fdf["market_cap_rank"].notna().any() else fdf.nlargest(topN, "market_cap")

    c1, c2 = st.columns([1,1])
    with c1:
        fig = px.bar(
            top_df.sort_values("market_cap", ascending=True),
            x="market_cap", y="name",
            title=f"Top {topN} by market cap"
        )
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        fig = px.pie(
            top_df, values="market_cap", names="name",
            title=f"Top {topN} market cap share"
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Top coins detail")
    st.dataframe(
        top_df[["symbol","name","current_price","market_cap","market_cap_rank","total_volume","supply_ratio"]],
        use_container_width=True
    )

# --- Market Cap ---
with tab_marketcap:
    st.subheader("Market cap distribution")
    fig = px.histogram(fdf, x="market_cap", nbins=50, title="Market Cap Distribution")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Market cap vs volume")
    fig = px.scatter(
        fdf, x="market_cap", y="total_volume",
        color="name", size="market_cap", hover_name="name",
        title="Market cap vs 24h volume"
    )
    st.plotly_chart(fig, use_container_width=True)

# --- Prices ---
with tab_price:
    st.subheader("Price distribution")
    fig = px.histogram(fdf, x="current_price", nbins=50, title="Price Distribution")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Top prices")
    top_price = fdf.nlargest(15, "current_price")
    fig = px.bar(
        top_price.sort_values("current_price"),
        x="current_price", y="name", orientation="h",
        title="Top 15 by price"
    )
    st.plotly_chart(fig, use_container_width=True)

# --- Supply ---
with tab_supply:
    st.subheader("Supply ratio (circulating / total)")
    fig = px.histogram(fdf, x="supply_ratio", nbins=30, title="Supply Ratio Distribution")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Circulating vs total supply")
    showN = st.slider("Show top N by circulating supply", 5, 50, 10, key="supplyN")
    top_supply = fdf.nlargest(showN, "circulating_supply")
    fig = px.bar(
        top_supply.sort_values("circulating_supply"),
        x="circulating_supply", y="name", orientation="h",
        title=f"Top {showN} by circulating supply"
    )
    st.plotly_chart(fig, use_container_width=True)

# --- ATH / ATL ---
with tab_athatl:
    st.subheader("ATH year distribution")
    fig = px.histogram(fdf, x="ath_year", title="ATH Year Distribution")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("ATL year distribution")
    fig = px.histogram(fdf, x="atl_year", title="ATL Year Distribution")
    st.plotly_chart(fig, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Farthest below ATH (%)")
        below_ath = fdf.nsmallest(15, "ath_change_percentage")
        fig = px.bar(
            below_ath.sort_values("ath_change_percentage"),
            x="ath_change_percentage", y="name", orientation="h",
            title="Farthest Below ATH (%)"
        )
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        st.subheader("Farthest above ATL (%)")
        above_atl = fdf.nlargest(15, "atl_change_percentage")
        fig = px.bar(
            above_atl.sort_values("atl_change_percentage"),
            x="atl_change_percentage", y="name", orientation="h",
            title="Farthest Above ATL (%)"
        )
        st.plotly_chart(fig, use_container_width=True)

# --- Table ---
with tab_table:
    st.subheader("Full dataset")
    show_logos = st.checkbox("Show logos in table (slower)", value=False)
    tbl = fdf.copy()
    if show_logos:
        tbl["logo"] = tbl["image"].apply(lambda url: f"![]({url})" if pd.notna(url) else "")
        st.markdown(
            tbl[["logo","symbol","name","current_price","market_cap","market_cap_rank","total_volume","supply_ratio"]].to_markdown(index=False),
            unsafe_allow_html=True
        )
    else:
        st.dataframe(
            tbl[["symbol","name","current_price","market_cap","market_cap_rank","total_volume","supply_ratio","ath","atl","ath_year","atl_year"]],
            use_container_width=True
        )

# ------------------------------
# FOOTER
# ------------------------------
st.divider()
st.caption(f"Last refreshed: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC • Data is live per run • Built for scale and clarity.")
