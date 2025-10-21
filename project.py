import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.express as px

# ================================================================
# 🏦 Streamlit App Config
# ================================================================
st.set_page_config(page_title="Zenith Bank Dashboard", layout="wide")
st.title("🏦 Zenith Bank Dashboard")
st.markdown("### Customer Spend & Transaction Insights")
#
# ================================================================
# 🗂 Page Navigation on Main Page
# ================================================================
st.markdown("---")
page = st.radio("Select Page", [
    "📊 KPIs",
    "🧍 Spend by Gender",
    " Spend by Age Group",
    " Spend by Marital Status",
    "💳 Transactions by Payment Type",
    "💼 Total Spend by Occupation",
    "🏷️ Total Spend by Category",
    "🏆 Top 10 Spending Customers"
], index=0, horizontal=True)
st.markdown("---")

# ================================================================
# 📥 Load Data
# ================================================================
@st.cache_data
def load_data():
    customers = pd.read_csv("dim_customers.csv")
    spends = pd.read_csv("fact_spends.csv")

    # Clean column names
    customers.columns = (
        customers.columns.str.lower()
        .str.strip()
        .str.replace(" ", "_")
        .str.replace(r"[^a-z0-9_]", "", regex=True)
    )
    spends.columns = (
        spends.columns.str.lower()
        .str.strip()
        .str.replace(" ", "_")
        .str.replace(r"[^a-z0-9_]", "", regex=True)
    )

    # Merge on customer_id
    df = pd.merge(spends, customers, on="customer_id", how="left")

    # Fix marital_status column
    for col in df.columns:
        if "marital" in col.lower():
            df.rename(columns={col: "marital_status"}, inplace=True)
            break

    # Handle DOB → Age
    if "dob" in df.columns:
        df["dob"] = pd.to_datetime(df["dob"], errors="coerce")
        df["age"] = datetime.now().year - df["dob"].dt.year
    elif "age_group" in df.columns:
        mapping = {"21-24": 22, "25-34": 29, "35-44": 39, "45+": 50}
        df["age"] = df["age_group"].map(mapping)
    elif "age" not in df.columns:
        df["age"] = None

    # Create Age Groups
    bins = [0, 20, 24, 34, 44, 54, 64, 100]
    labels = ["<20", "21-24", "25-34", "35-44", "45-54", "55-64", "65+"]
    df["age_group"] = pd.cut(df["age"], bins=bins, labels=labels, right=True)

    # Ensure 'spend' is numeric
    df["spend"] = pd.to_numeric(df["spend"], errors="coerce").fillna(0)

    return df

df = load_data()

# ================================================================
# 🧭 Sidebar Filters
# ================================================================
st.sidebar.header("🔍 Filters")

# City Filter
if "city" in df.columns:
    cities = sorted(df["city"].dropna().unique())
    selected_cities = st.sidebar.multiselect("Select City", cities, default=cities)
    df = df[df["city"].isin(selected_cities)]

# Occupation Filter
if "occupation" in df.columns:
    occupations = sorted(df["occupation"].dropna().unique())
    selected_occupations = st.sidebar.multiselect("Select Occupation", occupations, default=occupations)
    df = df[df["occupation"].isin(selected_occupations)]

# Category Filter
if "category" in df.columns:
    categories = sorted(df["category"].dropna().unique())
    selected_categories = st.sidebar.multiselect("Select Category", categories, default=categories)
    df = df[df["category"].isin(selected_categories)]

# Age Filter
if df["age"].notnull().any():
    min_age, max_age = int(df["age"].min()), int(df["age"].max())
    selected_age = st.sidebar.slider("Select Age Range", min_age, max_age, (min_age, max_age))
    df = df[df["age"].between(selected_age[0], selected_age[1])]

# ================================================================
# 💰 Currency Conversion USD → INR
# ================================================================
USD_TO_INR = 83  # Conversion rate
df["spend_inr"] = df["spend"] * USD_TO_INR

# ================================================================
# 📊 Display Pages Based on Selection
# ================================================================
if page == "📊 KPIs":
    st.subheader("📈 Key Performance Indicators")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Spend", f"₹{df['spend_inr'].sum():,.2f}")
    col2.metric("Unique Customers", df["customer_id"].nunique())
    col3.metric("Total Transactions", df.shape[0])

elif page == "🧍 Spend by Gender":
    st.subheader("🧍 Spend Distribution by Gender")
    if "gender" in df.columns:
        gdf = df.groupby("gender")["spend_inr"].sum().reset_index()
        fig_gender = px.pie(gdf, names="gender", values="spend_inr", hole=0.4, title="Spend by Gender (INR)")
        st.plotly_chart(fig_gender, use_container_width=True)

elif page == " Spend by Age Group":
    st.subheader("Spend by Age Group")
    age_summary = df.groupby(["city", "occupation", "category", "marital_status", "age_group"])["spend_inr"].sum().reset_index()
    fig_age = px.bar(
        age_summary,
        x="city",
        y="spend_inr",
        color="age_group",
        barmode="group",
        facet_col="occupation",
        facet_col_wrap=2,
        title="Spend by Age Group (INR) across City, Occupation, Category & Marital Status"
    )
    st.plotly_chart(fig_age, use_container_width=True)

elif page == " Spend by Marital Status":
    st.subheader("Spend by Marital Status across City, Occupation & Category")
    marital_summary = df.groupby(["city", "occupation", "category", "marital_status"])["spend_inr"].sum().reset_index()
    fig_marital = px.bar(
        marital_summary,
        x="city",
        y="spend_inr",
        color="marital_status",
        barmode="group",
        facet_col="occupation",
        facet_col_wrap=2,
        title="Spend by Marital Status (INR) across City, Occupation & Category"
    )
    st.plotly_chart(fig_marital, use_container_width=True)

elif page == "💳 Transactions by Payment Type":
    st.subheader("💳 Transactions by Payment Type, City, Occupation & Category")
    if "payment_type" in df.columns:
        tx = df.groupby(["city", "occupation", "category", "payment_type"]).size().reset_index(name="transaction_count")
        fig_tx = px.bar(
            tx,
            x="occupation",
            y="transaction_count",
            color="payment_type",
            barmode="group",
            facet_col="city",
            facet_col_wrap=2,
            title="Transactions by Payment Type across City, Occupation & Category"
        )
        st.plotly_chart(fig_tx, use_container_width=True)

elif page == "💼 Total Spend by Occupation":
    st.subheader("💼 Total Spend by Occupation")
    occ = df.groupby("occupation")["spend_inr"].sum().reset_index()
    fig_occ = px.bar(occ, x="occupation", y="spend_inr", text_auto=True, title="Total Spend by Occupation (INR)")
    st.plotly_chart(fig_occ, use_container_width=True)

elif page == "🏷️ Total Spend by Category":
    st.subheader("🏷️ Total Spend by Category")
    if "category" in df.columns:
        cat_spend = df.groupby("category")["spend_inr"].sum().reset_index().sort_values("spend_inr", ascending=False)
        fig_category = px.bar(cat_spend, x="category", y="spend_inr", text_auto=True, color="spend_inr", title="Total Spend by Category (INR)")
        st.plotly_chart(fig_category, use_container_width=True)

elif page == "🏆 Top 10 Spending Customers":
    st.subheader("🏆 Top 10 Spending Customers")
    name_cols = [col for col in ["first_name", "last_name"] if col in df.columns]
    group_cols = ["customer_id"] + name_cols
    top10 = df.groupby(group_cols)["spend_inr"].sum().reset_index().sort_values("spend_inr", ascending=False).head(10)
    if "first_name" in df.columns:
        top10["name"] = top10["first_name"].fillna("") + " " + top10.get("last_name", "")
    else:
        top10["name"] = top10["customer_id"].astype(str)
    fig_top10 = px.bar(top10, x="name", y="spend_inr", text_auto=True, title="Top 10 Customers by Spend (INR)", color="spend_inr")
    st.plotly_chart(fig_top10, use_container_width=True)

# ================================================================
# 🧾 Footer
# ================================================================
st.markdown("---")
st.markdown("<p style='text-align:center; color:gray;'>👨‍💻 Zenith Bank Analytics Dashboard © 2025</p>", unsafe_allow_html=True)
