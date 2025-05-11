import joblib
import numpy as np
from driver import Driver
import sys
import time

class ModelDriver(Driver):
    def __init__(self, stage):
        super().__init__(stage)
        
        # Load the trained model and scaler
        try:
            self.model = joblib.load('xg_torcs_model.pkl')
            self.scaler = joblib.load('scaler.pkl')
            print("✅ Model and scaler loaded successfully!")
        except Exception as e:
            print(f"❌ Error loading model: {e}")
            self.model = None
            self.scaler = None
        
        # Features used by the model
        self.features = ['SpeedX', 'SpeedY', 'SpeedZ', 'TrackPos', 'Angle', 'RPM', 'Gear_State']
        
        # Flag to toggle between manual and model control
        self.use_model = False
        self.in_recovery = False
        self.recovery_start_time = None
        self.in_post_recovery = False
        self.post_recovery_start_time = None
        self.last_recovery_time = 0





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

        steer, accel, brake = prediction
        steer = np.clip(steer, -1.0, 1.0)
        accel = np.clip(accel, 0.0, 1.0)
        brake = np.clip(brake, 0.0, 1.0)

        return steer, accel, brake

    def drive(self, msg):
        super().drive(msg)

        if self.use_model:
            speed = self.state.getSpeedX()
            angle = self.state.angle
            track_pos = self.state.trackPos
            current_time = time.time()

            # === Post-Recovery Forward Phase ===
            if self.in_post_recovery:
                if current_time - self.post_recovery_start_time < 4.0:
                    self.control.gear = 1
                    self.control.accel = 0.5
                    self.control.brake = 0.0

                    if angle > 0.5:
                        self.control.steer = -0.5  # steer right
                    elif angle < -0.5:
                        self.control.steer = 0.5   # steer left
                    else:
                        self.control.steer = 0.0

                    print("🚀 Post-recovery acceleration with angle steer")
                    return self.control.toMsg()
                else:
                    print("🎯 Post-recovery done — resuming model")
                    self.in_post_recovery = False

            # === Recovery Exit ===
            if self.in_recovery:
                if current_time - self.recovery_start_time > 3.0:
                    print("✅ Exiting recovery mode")
                    self.in_recovery = False
                    self.last_recovery_time = current_time

                    self.in_post_recovery = True
                    self.post_recovery_start_time = current_time
                    self.control.gear = 1
                    self.control.accel = 0.2
                    self.control.brake = 0.0
                    self.control.steer = 0.0
                    return self.control.toMsg()
                else:
                    # === Angle-based Reverse Recovery ===
                    self.control.gear = -1
                    self.control.accel = 0.3
                    self.control.brake = 0.0

                    if angle > 0.5:
                        self.control.steer = -0.5  # steer right
                    elif angle < -0.5:
                        self.control.steer = 0.5   # steer left
                    else:
                        self.control.steer = 0.0

                    print(f"🔄 Recovering in reverse using angle: {angle:.2f}")
                    return self.control.toMsg()

            # === Stuck Detection ===
            if speed < 0.3 and (current_time - self.last_recovery_time > 5):
                print("🛑 Stuck detected — entering recovery mode")
                self.in_recovery = True
                self.recovery_start_time = current_time
                return self.drive(msg)  # Trigger recovery logic immediately

            # === Normal Model Control ===
            prediction = self._get_model_prediction()
            if prediction:
                steer, accel, brake = prediction
                self.control.steer = steer
                self.control.accel = accel
                self.control.brake = brake
                print(f"🧠 Model driving → Steer: {steer:.2f}, Accel: {accel:.2f}, Brake: {brake:.2f}")

        return self.control.toMsg()








    def _manual_input_loop(self):
        self.last_steer_direction = None
        self.is_stopped = False

        if sys.platform.startswith("win"):
            import msvcrt
            while not self.should_quit:
                if msvcrt.kbhit():
                    key = msvcrt.getch()
                    if key == b'\xe0':
                        key = msvcrt.getch()
                        current_speed = self.state.getSpeedX()
                        self.is_stopped = abs(current_speed) < 0.1

                        if key == b'H':  # Up
                            if self.control.gear == -1:
                                if self.is_stopped:
                                    self.control.gear = 1
                                else:
                                    self.control.brake = min(self.control.brake + 0.1, 1.0)
                                    self.control.accel = 0.0
                            else:
                                self.control.accel = min(self.control.accel + 0.1, 1.0)
                                self.control.brake = 0.0

                        elif key == b'P':  # Down
                            if self.control.gear == -1:
                                self.control.accel = min(self.control.accel + 0.1, 1.0)
                                self.control.brake = 0.0
                            elif self.is_stopped and self.control.gear > 0:
                                self.control.gear = -1
                            else:
                                self.control.brake = min(self.control.brake + 0.1, 1.0)
                                self.control.accel = 0.0

                        elif key == b'M':  # Right → steer left
                            if self.last_steer_direction != "left" or self.control.steer > 0:
                                self.control.steer = 0.0
                                self.last_steer_direction = "left"
                            else:
                                self.control.steer -= 0.1
                                self.control.steer = max(self.control.steer, -1.0)

                        elif key == b'K':  # Left → steer right
                            if self.last_steer_direction != "right" or self.control.steer < 0:
                                self.control.steer = 0.0
                                self.last_steer_direction = "right"
                            else:
                                self.control.steer += 0.1
                                self.control.steer = min(self.control.steer, 1.0)

                    else:
                        if key.lower() == b'z':
                            self.control.gear += 1
                            self.last_manual_shift_time = time.time()
                            self.is_auto_shifting = False
                        elif key.lower() == b'x':
                            if self.control.accel > 0:
                                self.control.accel = max(self.control.accel - 0.1, 0)
                            self.control.gear -= 1
                            self.last_manual_shift_time = time.time()
                            self.is_auto_shifting = False
                        elif key.lower() == b's':
                            self.logging_enabled = True
                            print("📁 Logging started")
                        elif key.lower() == b'e':
                            self.logging_enabled = False
                            print("📁 Logging stopped")
                        elif key.lower() == b'q':
                            self.should_quit = True
                            print("❌ Quitting...")
                        elif key.lower() == b'm':
                            self.use_model = not self.use_model
                            print(f"🧠 Model control {'enabled' if self.use_model else 'disabled'}")

                if not self.is_auto_shifting and time.time() - self.last_manual_shift_time > self.manual_override_timeout:
                    self.is_auto_shifting = True
                    print("⚙️ Returning to auto gear shifting")

                time.sleep(0.05)
