
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor
from sklearn.multioutput import MultiOutputRegressor
from sklearn.metrics import mean_squared_error
import matplotlib.pyplot as plt
import joblib

# === CONFIG ===
DATA_PATH = "old.csv"
MODEL_PATH = "torcs_model.pkl"
SCALER_PATH = "scaler.pkl"

# === LOAD DATA ===
df = pd.read_csv(DATA_PATH)

features = ['SpeedX', 'SpeedY', 'SpeedZ', 'TrackPos', 'Angle', 'RPM', 'Gear_State']
targets = ['Steer', 'Accel', 'Brake']

df = df[features + targets].dropna()

# Optional: Sample for quick training
# df = df.sample(n=10000, random_state=42)

X = df[features]
y = df[targets]

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42)

model = MultiOutputRegressor(RandomForestRegressor(n_estimators=30, random_state=42))
model.fit(X_train, y_train)

# Save model and scaler
joblib.dump(model, MODEL_PATH)
joblib.dump(scaler, SCALER_PATH)

# Predict and evaluate
y_pred = model.predict(X_test)

for i, target in enumerate(targets):
    mse = mean_squared_error(y_test[target], y_pred[:, i])
    print(f"{target} MSE: {mse:.6f}")

# Plot for Steer
plt.figure(figsize=(8, 4))
plt.scatter(y_test['Steer'], y_pred[:, 0], alpha=0.3)
plt.xlabel("Actual Steer")
plt.ylabel("Predicted Steer")
plt.title("Actual vs Predicted Steer")
plt.grid(True)
plt.tight_layout()
plt.show()
