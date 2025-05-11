import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.multioutput import MultiOutputRegressor
from sklearn.metrics import mean_squared_error
from xgboost import XGBRegressor
import joblib
import matplotlib.pyplot as plt

# === LOAD DATA ===
df = pd.read_csv("adjusted.csv")

# Drop unnecessary columns if they exist
df = df.drop(columns=[col for col in df.columns if col not in ['SpeedX', 'SpeedY', 'SpeedZ', 'TrackPos', 'Angle', 'RPM', 'Gear_State', 'Steer', 'Accel', 'Brake']])

features = ['SpeedX', 'SpeedY', 'SpeedZ', 'TrackPos', 'Angle', 'RPM', 'Gear_State']
targets = ['Steer', 'Accel', 'Brake']

# Drop rows with missing values
df = df[features + targets].dropna()

X = df[features]
y = df[targets]

# Scale the features
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# Train/test split
X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42)

# Train XGBoost
model = MultiOutputRegressor(XGBRegressor(n_estimators=100, max_depth=6, learning_rate=0.1, random_state=42))
model.fit(X_train, y_train)

# Save model and scaler
joblib.dump(model, "xg_torcs_model.pkl")
joblib.dump(scaler, "scaler.pkl")

# Evaluate
y_pred = model.predict(X_test)
for i, col in enumerate(targets):
    mse = mean_squared_error(y_test[col], y_pred[:, i])
    print(f"{col} MSE: {mse:.6f}")

# Plot steering
plt.figure(figsize=(8, 4))
plt.scatter(y_test['Steer'], y_pred[:, 0], alpha=0.3)
plt.xlabel("Actual Steer")
plt.ylabel("Predicted Steer")
plt.title("Actual vs Predicted Steer (XGBoost)")
plt.grid(True)
plt.tight_layout()
plt.show()
