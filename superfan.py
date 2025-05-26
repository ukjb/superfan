#!/usr/bin/python3

import RPi.GPIO as GPIO
import time
import subprocess
import logging
import sys
import signal

# Configuration
FAN_PIN = 14
PWM_FREQ = 100

# Temperature thresholds and corresponding fan speeds (duty cycle %)
TEMP_THRESHOLDS = [
    (65, 100, 300),  # temp >= 65°C: 100% speed, check every 5 min
    (55, 90, 180),   # temp >= 55°C: 90% speed, check every 3 min
    (50, 80, 120),   # temp >= 50°C: 80% speed, check every 2 min
    (45, 70, 90),    # temp >= 45°C: 70% speed, check every 1.5 min
    (40, 60, 60),    # temp >= 40°C: 60% speed, check every 1 min
    (35, 40, 60),    # temp >= 35°C: 40% speed, check every 1 min
    (0, 25, 60)      # temp < 35°C: 25% speed, check every 1 min
]

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/pi-fan-controller.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

class FanController:
    def __init__(self):
        self.pwm = None
        self.running = True
        
        # Setup GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(FAN_PIN, GPIO.OUT)
        self.pwm = GPIO.PWM(FAN_PIN, PWM_FREQ)
        self.pwm.start(0)
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)
        
        logging.info("Fan controller initialized")
    
    def signal_handler(self, signum, frame):
        logging.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False
    
    def get_cpu_temp(self):
        """Get CPU temperature from vcgencmd"""
        try:
            temp_str = subprocess.getoutput("vcgencmd measure_temp")
            # Extract temperature value (format: temp=XX.X'C)
            temp = float(temp_str.split('=')[1].split('\'')[0])
            return temp
        except Exception as e:
            logging.error(f"Error reading temperature: {e}")
            return 40.0  # Default safe temperature
    
    def get_fan_speed_and_interval(self, temp):
        """Determine fan speed and check interval based on temperature"""
        for threshold_temp, duty_cycle, interval in TEMP_THRESHOLDS:
            if temp >= threshold_temp:
                return duty_cycle, interval
        
        # Fallback (should never reach here due to last threshold being 0)
        return 25, 60
    
    def run(self):
        """Main control loop"""
        logging.info("Starting fan control loop")
        
        try:
            while self.running:
                temp = self.get_cpu_temp()
                duty_cycle, sleep_interval = self.get_fan_speed_and_interval(temp)
                
                self.pwm.ChangeDutyCycle(duty_cycle)
                logging.info(f"CPU Temp: {temp:.1f}°C | Fan Speed: {duty_cycle}% | Next check: {sleep_interval}s")
                
                # Sleep in small intervals to allow for graceful shutdown
                for _ in range(sleep_interval):
                    if not self.running:
                        break
                    time.sleep(1)
                    
        except Exception as e:
            logging.error(f"Error in main loop: {e}")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up GPIO resources"""
        if self.pwm:
            self.pwm.stop()
        GPIO.cleanup()
        logging.info("Fan controller stopped and cleaned up")

def main():
    controller = FanController()
    controller.run()

if __name__ == "__main__":
    main()
