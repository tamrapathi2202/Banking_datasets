import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.express as px

# ================================================================
# 🏦 Streamlit App Config
# ================================================================
st.set_page_config(page_title="Zenith Bank Dashboard", layout="wide")
st.title("🏦 Zenith Bank Dashboard")
st.markdown("### Customer Spend & Transaction Insights")

# ================================================================
# 🗂 Page Navigation
# ================================================================
st.markdown("---")
page = st.radio(
    "Select Page",
    [
        "📊 KPIs",
        "🧍 Spend by Gender",
        "👥 Spend by Age Group",
        "💍 Spend by Marital Status",
        "💳 Transactions by Payment Type",
        "💼 Total Spend by Occupation",
        "🏷️ Total Spend by Category",
        "🏆 Top 10 Spending Customers",
    ],
    index=0,
    horizontal=True,
)
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

    # Merge
    df = pd.merge(spends, customers, on="customer_id", how="left")

    # Fix marital_status column
    for col in df.columns:
        if "marital" in col.lower():
            df.rename(columns={col: "marital_status"}, inplace=True)
            break

    # Convert DOB to Age or use age_group from CSV
    if "dob" in df.columns:
        df["dob"] = pd.to_datetime(df["dob"], errors="coerce")
        today = pd.to_datetime(datetime.now().date())
        df["age"] = (today - df["dob"]).dt.days // 365
        # Create age groups from calculated age
        bins = [0, 20, 24, 34, 45, 120]
        labels = ["<20", "21-24", "25-34", "35-45", "45+"]
        df["age_group"] = pd.cut(df["age"], bins=bins, labels=labels, right=True)
    elif "age_group" in df.columns:
        # Use the age_group from CSV directly and create age column for filtering
        mapping = {"21-24": 22, "25-34": 29, "35-45": 39, "45+": 50}
        df["age"] = df["age_group"].map(mapping)
    elif "age" not in df.columns:
        df["age"] = np.nan
        df["age_group"] = None

    df["age"] = pd.to_numeric(df["age"], errors="coerce")

    # Ensure spend numeric
    df["spend"] = pd.to_numeric(df["spend"], errors="coerce").fillna(0)

    return df


df = load_data()

# ================================================================
# 🧭 Sidebar Filters
# ================================================================
st.sidebar.header("🔍 Filters")

if "city" in df.columns:
    cities = sorted(df["city"].dropna().unique())
    selected_cities = st.sidebar.multiselect("Select City", cities, default=cities)
    df = df[df["city"].isin(selected_cities)]

if "occupation" in df.columns:
    occupations = sorted(df["occupation"].dropna().unique())
    selected_occupations = st.sidebar.multiselect(
        "Select Occupation", occupations, default=occupations
    )
    df = df[df["occupation"].isin(selected_occupations)]

if "category" in df.columns:
    categories = sorted(df["category"].dropna().unique())
    selected_categories = st.sidebar.multiselect(
        "Select Category", categories, default=categories
    )
    df = df[df["category"].isin(selected_categories)]

if df["age"].notnull().any():
    min_age, max_age = int(df["age"].min()), int(df["age"].max())
    selected_age = st.sidebar.slider(
        "Select Age Range", min_age, max_age, (min_age, max_age)
    )
    df = df[df["age"].between(selected_age[0], selected_age[1])]

# ================================================================
# 💰 Currency Conversion USD → INR
# ================================================================
USD_TO_INR = 83
df["spend_inr"] = df["spend"] * USD_TO_INR

# ================================================================
# 📊 Display Pages
# ================================================================
if page == "📊 KPIs":
    st.subheader("📈 Key Performance Indicators")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Spend", f"₹{df['spend_inr'].sum():,.2f}")
    c2.metric("Unique Customers", df["customer_id"].nunique())
    c3.metric("Total Transactions", df.shape[0])

elif page == "🧍 Spend by Gender":
    st.subheader("🧍 Spend by Gender")
    if "gender" in df.columns:
        g = df.groupby("gender")["spend_inr"].sum().reset_index()
        fig = px.pie(
            g,
            names="gender",
            values="spend_inr",
            hole=0.4,
            title="Spend by Gender (INR)",
        )
        st.plotly_chart(fig, use_container_width=True)

elif page == "👥 Spend by Age Group":
    st.subheader("👥 Spend by Age Group")

    all_age_groups = ["<20", "21-24", "25-34", "35-45", "45+"]

    # Group by age_group only, aggregating across all dimensions
    age_summary = df.groupby("age_group", dropna=False)["spend_inr"].sum().reset_index()

    # Ensure all age groups are represented
    all_age_df = pd.DataFrame({"age_group": all_age_groups})
    age_summary = all_age_df.merge(age_summary, on="age_group", how="left")
    age_summary["spend_inr"] = age_summary["spend_inr"].fillna(0)
    age_summary["age_group"] = pd.Categorical(
        age_summary["age_group"], categories=all_age_groups, ordered=True
    )
    age_summary = age_summary.sort_values("age_group")

    # Plot bar chart showing all age groups
    fig_age = px.bar(
        age_summary,
        x="age_group",
        y="spend_inr",
        color="age_group",
        category_orders={"age_group": all_age_groups},
        title="Spend by Age Group (INR) across City, Occupation, Category & Marital Status",
        labels={"spend_inr": "Total Spend (INR)", "age_group": "Age Group"},
        text_auto=True,
    )
    st.plotly_chart(fig_age, use_container_width=True)

elif page == "💍 Spend by Marital Status":
    st.subheader("💍 Spend by Marital Status")
    m = (
        df.groupby(["city", "occupation", "category", "marital_status"])["spend_inr"]
        .sum()
        .reset_index()
    )
    fig = px.bar(
        m,
        x="city",
        y="spend_inr",
        color="marital_status",
        barmode="group",
        facet_col="occupation",
        facet_col_wrap=2,
    )
    st.plotly_chart(fig, use_container_width=True)

elif page == "💳 Transactions by Payment Type":
    st.subheader("💳 Transactions by Payment Type")

    # Show filter summary
    filter_summary = []
    if "city" in df.columns:
        selected = df["city"].unique().tolist()
        filter_summary.append(f"**Cities:** {', '.join(selected)}")
    if "occupation" in df.columns:
        selected = df["occupation"].unique().tolist()
        filter_summary.append(f"**Occupations:** {', '.join(selected)}")
    if "category" in df.columns:
        selected = df["category"].unique().tolist()
        filter_summary.append(f"**Categories:** {', '.join(selected)}")

    st.info(" | ".join(filter_summary) + f" | **Total Records:** {len(df)}")

    if "payment_type" in df.columns:
        # Metric selection
        metric = st.radio(
            "Select Metric to Visualize:",
            ["Transaction Count", "Total Spend Amount"],
            horizontal=True,
        )

        # Group by occupation and payment_type
        tx = (
            df.groupby(["occupation", "payment_type"])
            .agg(
                transaction_count=("payment_type", "size"),
                total_spend=("spend_inr", "sum"),
            )
            .reset_index()
        )

        if metric == "Transaction Count":
            y_col = "transaction_count"
            title_text = "Transaction Counts"
            y_label = "Number of Transactions"
            st.caption(
                "ℹ️ **Note:** In this dataset, transaction counts are perfectly balanced across payment types."
            )
        else:
            y_col = "total_spend"
            title_text = "Total Spend (INR)"
            y_label = "Total Spend (INR)"

        # Show summary table
        with st.expander(f"📊 View {metric} Data Table"):
            st.dataframe(
                tx.pivot(
                    index="occupation", columns="payment_type", values=y_col
                ).fillna(0)
            )

        fig = px.bar(
            tx,
            x="occupation",
            y=y_col,
            color="payment_type",
            barmode="group",
            title=f"{title_text} by Payment Type (Filtered by: {', '.join(filter_summary[:2])})",
            text_auto=True,
            labels={y_col: y_label, "occupation": "Occupation"},
        )
        st.plotly_chart(fig, use_container_width=True)

elif page == "💼 Total Spend by Occupation":
    st.subheader("💼 Total Spend by Occupation")
    o = df.groupby("occupation")["spend_inr"].sum().reset_index()
    fig = px.bar(
        o,
        x="occupation",
        y="spend_inr",
        text_auto=True,
        title="Total Spend by Occupation (INR)",
    )
    st.plotly_chart(fig, use_container_width=True)

elif page == "🏷️ Total Spend by Category":
    st.subheader("🏷️ Total Spend by Category")
    c = (
        df.groupby("category")["spend_inr"]
        .sum()
        .reset_index()
        .sort_values("spend_inr", ascending=False)
    )
    fig = px.bar(
        c,
        x="category",
        y="spend_inr",
        text_auto=True,
        color="spend_inr",
        title="Total Spend by Category (INR)",
    )
    st.plotly_chart(fig, use_container_width=True)

elif page == "🏆 Top 10 Spending Customers":
    st.subheader("🏆 Top 10 Spending Customers")
    name_cols = [col for col in ["first_name", "last_name"] if col in df.columns]
    group_cols = ["customer_id"] + name_cols
    top10 = (
        df.groupby(group_cols)["spend_inr"]
        .sum()
        .reset_index()
        .sort_values("spend_inr", ascending=False)
        .head(10)
    )
    if "first_name" in df.columns:
        top10["name"] = (
            top10["first_name"].fillna("") + " " + top10.get("last_name", "")
        )
    else:
        top10["name"] = top10["customer_id"].astype(str)
    fig = px.bar(
        top10,
        x="name",
        y="spend_inr",
        text_auto=True,
        color="spend_inr",
        title="Top 10 Customers by Spend (INR)",
    )
    st.plotly_chart(fig, use_container_width=True)

# ================================================================
# 🧾 Footer
# ================================================================
st.markdown("---")
st.markdown(
    "<p style='text-align:center; color:gray;'>👨‍💻 Zenith Bank Analytics Dashboard © 2025</p>",
    unsafe_allow_html=True,
)
