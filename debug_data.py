import pandas as pd

# Load data
print("Loading data...")
customers = pd.read_csv("dim_customers.csv")
spends = pd.read_csv("fact_spends.csv")

# Clean column names (matching project.py logic)
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

print(f"Customers shape: {customers.shape}")
print(f"Spends shape: {spends.shape}")

# Check for duplicates in customers
print(f"Unique customer_ids in customers: {customers['customer_id'].nunique()}")
print(f"Total rows in customers: {len(customers)}")

# Merge
print("Merging data...")
df = pd.merge(spends, customers, on="customer_id", how="left")
print(f"Merged df shape: {df.shape}")

# Analyze distribution
print("\n--- Distribution Analysis ---")
if 'occupation' in df.columns and 'payment_type' in df.columns:
    # Group by occupation and payment_type
    counts = df.groupby(['occupation', 'payment_type']).agg(
        transaction_count=('payment_type', 'size'),
        total_spend=('spend', 'sum')
    ).reset_index()
    
    print("\nCounts and Spend by Occupation and Payment Type (First 20 rows):")
    print(counts.head(20))
    
    # Check if counts are identical for each occupation
    print("\nChecking for identical counts and spend within occupations:")
    for occupation in counts['occupation'].unique():
        occ_data = counts[counts['occupation'] == occupation]
        unique_counts = occ_data['transaction_count'].unique()
        unique_spend = occ_data['total_spend'].unique()
        
        print(f"Occupation: {occupation}")
        print(f"  Unique Counts: {unique_counts}")
        print(f"  Unique Spend: {unique_spend}")
        
        if len(unique_counts) == 1:
            print(f"  ⚠️  COUNTS are identical: {unique_counts[0]}")
        if len(unique_spend) > 1:
            print(f"  ✅  SPEND varies (Min: {unique_spend.min()}, Max: {unique_spend.max()})")
        else:
            print(f"  ⚠️  SPEND is also identical!")
else:
    print("Columns 'occupation' or 'payment_type' not found in merged dataframe.")

# Check raw spends data for payment_type distribution
print("\n--- Raw Spends Data Analysis ---")
print(spends['payment_type'].value_counts())
