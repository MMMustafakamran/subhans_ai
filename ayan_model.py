import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.multioutput import MultiOutputRegressor
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler
import joblib  # for saving the model

# Load preprocessed data
X = pd.read_csv('X_processed.csv')
y = pd.read_csv('y_processed.csv')  # Must contain the target(s): e.g., angle or angle+accel+brake

# Scale inputs
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# 1. Train-test split
X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42)

# 2. Define model
base_model = RandomForestRegressor(n_estimators=100, random_state=42)
model = MultiOutputRegressor(base_model)

# 3. Train
model.fit(X_train, y_train)

# 4. Predict & evaluate
y_pred = model.predict(X_test)
mse = mean_squared_error(y_test, y_pred)
r2 = r2_score(y_test, y_pred)

print(f"Mean Squared Error: {mse:.4f}")
print(f"R2 Score: {r2:.4f}")

# 5. Save model and scaler
joblib.dump(model, 'driving_model.pkl')
joblib.dump(scaler, 'scaler.pkl')
