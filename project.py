import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.express as px

# ==========================================================
# 🎯 Streamlit Page Configuration
# ==========================================================
st.set_page_config(page_title="Zenith Bank Dashboard", layout="wide")

st.title("🏦 Zenith Bank Dashboard")
st.markdown("#### Customer Spend & Transaction Insights")
st.markdown("---")

# ==========================================================
# 📥 Load and Prepare Data
# ==========================================================
@st.cache_data
def load_data():
    customers = pd.read_csv("dim_customers.csv")
    spends = pd.read_csv("fact_spends.csv")

    # Clean column names
    customers.columns = customers.columns.str.lower().str.strip()
    spends.columns = spends.columns.str.lower().str.strip()

    # Identify transaction column (if exists)
    possible_txn_cols = ["transaction_id", "txn_id", "trans_id", "spend_id"]
    txn_col = next((col for col in possible_txn_cols if col in spends.columns), None)

    # Create synthetic transaction id if missing
    if not txn_col:
        spends["transaction_id"] = range(1, len(spends) + 1)
        txn_col = "transaction_id"

    # Merge datasets
    df = pd.merge(spends, customers, on="customer_id", how="left")

    # Handle age or age_group
    if "dob" in df.columns:
        df["dob"] = pd.to_datetime(df["dob"], errors="coerce")
        df["age"] = datetime.now().year - df["dob"].dt.year
    elif "age_group" in df.columns:
        age_map = {
            "21-24": 22,
            "25-34": 29,
            "35-44": 39,
            "45+": 50
        }
        df["age"] = df["age_group"].map(age_map)
    else:
        df["age"] = None

    return df, txn_col

df, txn_col = load_data()

# ==========================================================
# 🧭 Sidebar Filters
# ==========================================================
st.sidebar.header("🔍 Filters")

# --- 🏙️ City Filter (with Average Spend) ---
if "city" in df.columns:
    city_avg = (
        df.groupby("city")["spend"]
        .mean()
        .reset_index()
        .sort_values("spend", ascending=False)
    )
    city_avg["label"] = city_avg["city"] + " ($" + city_avg["spend"].round(2).astype(str) + ")"

    selected_city_labels = st.sidebar.multiselect(
        "Select City (Average Spend shown)",
        options=city_avg["label"].tolist(),
        default=city_avg["label"].tolist(),
        key="city_multiselect"
    )

    selected_cities = city_avg[city_avg["label"].isin(selected_city_labels)]["city"].tolist()
    df = df[df["city"].isin(selected_cities)]

# --- 👔 Occupation Filter ---
df = df.dropna(subset=["occupation"])
occupations = sorted(df["occupation"].unique())
selected_occupations = st.sidebar.multiselect(
    "Select Occupation(s)",
    occupations,
    default=occupations,
    key="occupation_multiselect"
)

# --- 🎂 Age Filter ---
if df["age"].notnull().any():
    min_age, max_age = int(df["age"].min()), int(df["age"].max())
    selected_age = st.sidebar.slider(
        "Select Age Range", min_value=min_age, max_value=max_age, value=(min_age, max_age), key="age_slider"
    )
else:
    selected_age = (None, None)

# --- 🛍️ Category Filter ---
if "category" in df.columns:
    categories = sorted(df["category"].dropna().unique())
    selected_categories = st.sidebar.multiselect(
        "Select Spending Category(s)", categories, default=categories, key="category_multiselect"
    )
else:
    selected_categories = None

# ==========================================================
# 🔄 Apply Filters
# ==========================================================
df_filtered = df[df["occupation"].isin(selected_occupations)]
if selected_age != (None, None):
    df_filtered = df_filtered[df_filtered["age"].between(selected_age[0], selected_age[1])]
if selected_categories is not None:
    df_filtered = df_filtered[df_filtered["category"].isin(selected_categories)]

# ==========================================================
# 📊 KPIs
# ==========================================================
st.subheader("📈 Key Performance Indicators")
col1, col2, col3 = st.columns(3)

total_txns = df_filtered[txn_col].nunique()
unique_customers = df_filtered["customer_id"].nunique()
total_spend = df_filtered["spend"].sum()

col1.metric("Total Transactions", f"{total_txns:,}")
col2.metric("Unique Customers", f"{unique_customers:,}")
col3.metric("Total Spend", f"${total_spend:,.2f}")

st.markdown("---")

# ==========================================================
# 🧍‍♂️🧍‍♀️ Spend Distribution by Gender
# ==========================================================
st.subheader("🧍 Spend Distribution by Gender")

if "gender" in df_filtered.columns:
    gender_spend = (
        df_filtered.groupby("gender")["spend"]
        .sum()
        .reset_index()
        .sort_values("spend", ascending=False)
    )

    fig_gender = px.pie(
        gender_spend,
        names="gender",
        values="spend",
        hole=0.4,
        color_discrete_sequence=px.colors.qualitative.Set2,
        title="🧍‍♂️🧍‍♀️ Total Spend by Gender"
    )

    fig_gender.update_traces(textinfo="label+percent", pull=[0.05, 0.05])
    fig_gender.update_layout(title_x=0.3)

    st.plotly_chart(fig_gender, use_container_width=True)
else:
    st.info("Gender information is not available in the dataset.")

# ==========================================================
# 💳 Transactions by Payment Type and Occupation
# ==========================================================
st.subheader("💳 Transactions by Payment Type and Occupation")
if "payment_type" in df_filtered.columns:
    tx_summary = (
        df_filtered.groupby(["occupation", "payment_type"])
        .agg(transaction_count=(txn_col, "count"), total_spend=("spend", "sum"))
        .reset_index()
    )
    tx_summary = tx_summary.sort_values(["occupation", "transaction_count"], ascending=[True, False])

    with st.expander("🔎 View Transaction Summary Data"):
        st.dataframe(tx_summary)

    fig_tx = px.bar(
        tx_summary,
        x="occupation",
        y="transaction_count",
        color="payment_type",
        barmode="group",
        text_auto=True,
        title="💳 Transactions by Payment Type and Occupation"
    )
    fig_tx.update_layout(
        xaxis_title="Occupation",
        yaxis_title="Transaction Count",
        legend_title="Payment Type",
        title_x=0.25
    )
    st.plotly_chart(fig_tx, use_container_width=True)

# ==========================================================
# 💼 Total Spend by Occupation
# ==========================================================
st.subheader("💼 Total Spend by Occupation")
spend_occ = df_filtered.groupby("occupation")["spend"].sum().reset_index()
fig_spend = px.bar(
    spend_occ,
    x="occupation",
    y="spend",
    text_auto=True,
    title="💼 Total Spend by Occupation"
)
fig_spend.update_layout(xaxis_title="Occupation", yaxis_title="Total Spend")
st.plotly_chart(fig_spend, use_container_width=True)

# ==========================================================
# 💰 Total Spend by Category
# ==========================================================
if "category" in df_filtered.columns:
    st.subheader("💰 Total Spend by Category")
    spend_cat = df_filtered.groupby("category")["spend"].sum().reset_index().sort_values("spend", ascending=False)
    fig_cat = px.bar(
        spend_cat,
        x="category",
        y="spend",
        text_auto=True,
        title="💰 Total Spend by Category"
    )
    fig_cat.update_layout(xaxis_title="Category", yaxis_title="Total Spend")
    st.plotly_chart(fig_cat, use_container_width=True)

# ==========================================================
# 📈 Spend by Age
# ==========================================================
if df_filtered["age"].notnull().any():
    st.subheader("📈 Spend by Age")
    spend_age = df_filtered.groupby("age")["spend"].sum().reset_index()
    fig_age = px.line(
        spend_age,
        x="age",
        y="spend",
        markers=True,
        title="📈 Spend by Age"
    )
    fig_age.update_layout(xaxis_title="Age", yaxis_title="Total Spend")
    st.plotly_chart(fig_age, use_container_width=True)

# ==========================================================
# 🏆 Top 10 Spending Customers (Fixed)
# ==========================================================
st.subheader("🏆 Top 10 Spending Customers")

# Handle missing name columns safely
name_cols = [col for col in ["first_name", "last_name"] if col in df_filtered.columns]

# Group by existing columns
group_cols = ["customer_id"] + name_cols

top_customers = (
    df_filtered.groupby(group_cols, as_index=False)["spend"]
    .sum()
    .sort_values("spend", ascending=False)
    .head(10)
)

# Create readable display name
if "first_name" in df_filtered.columns or "last_name" in df_filtered.columns:
    top_customers["customer_name"] = (
        top_customers.get("first_name", "") + " " + top_customers.get("last_name", "")
    ).str.strip()
    top_customers["customer_name"] = top_customers["customer_name"].replace("", "Unknown Customer")
else:
    top_customers["customer_name"] = top_customers["customer_id"].astype(str)

# Plot bar chart
fig_top10 = px.bar(
    top_customers,
    x="customer_name",
    y="spend",
    text_auto=".2s",
    title="🏆 Top 10 Customers by Spend (Filtered View)",
    color="spend",
    color_continuous_scale="Blues"
)
fig_top10.update_layout(
    xaxis_title="Customer",
    yaxis_title="Total Spend",
    xaxis_tickangle=-45,
    title_x=0.25
)
st.plotly_chart(fig_top10, use_container_width=True)

with st.expander("📋 View Top 10 Customer Details"):
    display_cols = ["customer_id", "spend", "city", "gender", "occupation"]
    existing_cols = [c for c in display_cols if c in df_filtered.columns]
    st.dataframe(
        df_filtered[df_filtered["customer_id"].isin(top_customers["customer_id"])][existing_cols]
        .sort_values("spend", ascending=False)
    )

# ==========================================================
# 🧾 Footer
# ==========================================================
st.markdown("---")
st.markdown(
    "<p style='text-align:center; color:gray;'>👨‍💻 Created by Data Team | Zenith Bank © 2025</p>",
    unsafe_allow_html=True
)
