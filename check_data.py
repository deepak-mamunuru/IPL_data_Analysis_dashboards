import pandas as pd

matches = pd.read_csv("data/matches.csv")
deliveries = pd.read_csv("data/deliveries.csv")

print("\nMATCHES COLUMNS:")
print(matches.columns.tolist())

print("\nDELIVERIES COLUMNS:")
print(deliveries.columns.tolist())

print("\nMATCHES FIRST 5 ROWS:")
print(matches.head())

print("\nDELIVERIES FIRST 5 ROWS:")
print(deliveries.head())