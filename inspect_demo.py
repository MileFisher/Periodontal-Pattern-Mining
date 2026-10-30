import pandas as pd

file_path = "data/raw/DEMO_F.xpt"

df = pd.read_sas(file_path, format="xport")

# 1. Show the first 5 rows
print("\n--- First 5 Rows ---")
print(df.head())

# 2. Show the number of rows and columns
print("\n--- Dataset Shape ---")
print(df.shape)

# 3. Show all column names
print("\n--- Column Names ---")
print(df.columns.tolist())

# 4. Show the first 10 participant IDs
print("\n--- First 10 Participant IDs ---")
print(df["SEQN"].head(10))