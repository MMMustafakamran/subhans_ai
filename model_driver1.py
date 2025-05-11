
import joblib
import numpy as np
from driver import Driver
import sys
import time

class ModelDriver(Driver):
    def __init__(self, stage):
        super().__init__(stage)

        try:
            self.model = joblib.load('xg_torcs_model.pkl')
            self.scaler = joblib.load('scaler.pkl')
            print("✅ Model and scaler loaded successfully.")
        except Exception as e:
            print(f"❌ Error loading model or scaler: {e}")
            self.model = None
            self.scaler = None

        self.features = ['SpeedX', 'SpeedY', 'SpeedZ', 'TrackPos', 'Angle', 'RPM', 'Gear_State']
        self.use_model = False

    def _get_model_prediction(self):
        if self.model is None or self.scaler is None:
            return None

        input_data = np.array([[ 
            self.state.speedX,
            self.state.speedY,
            self.state.speedZ,
            self.state.trackPos,
            self.state.angle,
            self.state.getRpm(),
            self.state.gear
        ]])

        input_scaled = self.scaler.transform(input_data)
        prediction = self.model.predict(input_scaled)[0]

        steer = float(np.clip(prediction[0], -1.0, 1.0))
        accel = float(np.clip(prediction[1], 0.0, 1.0))
        brake = float(np.clip(prediction[2], 0.0, 1.0))
        return steer, accel, brake

    def drive(self, msg):
        super().drive(msg)

        if self.use_model:
            prediction = self._get_model_prediction()
            if prediction:
                steer, accel, brake = prediction
                self.control.steer = steer
                self.control.accel = accel
                self.control.brake = brake
                print(f"🧠 Model Driving → Steer: {steer:.2f}, Accel: {accel:.2f}, Brake: {brake:.2f}")

        return self.control.toMsg()

    def _manual_input_loop(self):
        self.last_steer_direction = None
        self.is_stopped = False

        if sys.platform.startswith("win"):
            import msvcrt
            while not self.should_quit:
                if msvcrt.kbhit():
                    key = msvcrt.getch()
                    if key.lower() == b'm':
                        self.use_model = not self.use_model
                        print(f"🧠 Model control {'enabled' if self.use_model else 'disabled'}")
                time.sleep(0.05)
        else:
            import select, tty, termios
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            tty.setcbreak(fd)
            try:
                while not self.should_quit:
                    dr, _, _ = select.select([sys.stdin], [], [], 0)
                    if dr:
                        key = sys.stdin.read(1)
                        if key.lower() == 'm':
                            self.use_model = not self.use_model
                            print(f"🧠 Model control {'enabled' if self.use_model else 'disabled'}")
                    time.sleep(0.05)
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
