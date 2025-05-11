import pandas as pd
from sklearn.preprocessing import StandardScaler

# Load raw data
df = pd.read_csv("telemetry_log_cleaned.csv")

# 1. Drop unused or empty fields
df = df.drop(columns=['x', 'y'])  # they’re empty anyway

# 2. Remove idle frames (when car isn't moving)
df = df[df['speedX'] > 5]

# 3. Drop NaN values (optional: or fill with 0 or interpolation)
df = df.dropna()

# 4. Compute time delta
df['dt'] = df['timestamp'].diff().fillna(0.001)

# 5. Compute acceleration
df['accelerationX'] = df['speedX'].diff().fillna(0) / df['dt']
df['accelerationY'] = df['speedY'].diff().fillna(0) / df['dt']
df['accelerationZ'] = df['speedZ'].diff().fillna(0) / df['dt']

# 6. Drop any rows with unreasonable acceleration (optional)
df = df[(df['accelerationX'].abs() < 50) & (df['accelerationY'].abs() < 50)]

# 7. Feature and target selection
features = ['angle', 'damage', 'distFromStart', 'distRaced', 'fuel', 'gear',
            'rpm', 'speedX', 'speedY', 'speedZ', 'trackPos', 'z',
            'accelerationX', 'accelerationY', 'accelerationZ']

# Define placeholder targets — adjust these based on your logging setup
# e.g., if you stored `steering`, `accel`, `brake` separately
targets = ['angle']  # or ['steering', 'accel', 'brake'] if you have them

# Normalize features
scaler = StandardScaler()
X_scaled = scaler.fit_transform(df[features])

# Save processed data
pd.DataFrame(X_scaled, columns=features).to_csv("X_processed.csv", index=False)
df[targets].to_csv("y_processed.csv", index=False)
