import pandas as pd
import numpy as np

# === CONFIG ===
INPUT_CSV = "old.csv"
OUTPUT_CSV = "adjusted.csv"

# === LOAD DATA ===
df = pd.read_csv(INPUT_CSV)

# === APPLY CONDITIONAL MODIFICATION ===
# Only update rows where Accel is 0, Brake is applied, and the car is moving fast enough
mask = (df['Accel'] == 0) & (df['Brake'] > 0) & (df['SpeedX'] > 10)

# Generate random values (0.1 or 0.2) for the matching rows
replacement_values = np.random.choice([0.1, 0.2], size=mask.sum())

# Apply replacements
df.loc[mask, 'Accel'] = replacement_values

# === SAVE NEW CSV ===
df.to_csv(OUTPUT_CSV, index=False)

print(f"✅ Modified {mask.sum()} rows. New file saved to: {OUTPUT_CSV}")
