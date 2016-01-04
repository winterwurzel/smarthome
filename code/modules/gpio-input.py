#gpio-input
#for reading gpios

import RPi.GPIO as GPIO

# Pin Setup:
GPIO.setmode(GPIO.BCM)          # Broadcom pin-numbering scheme
GPIO.setup(ledPin, GPIO.OUT)    # LED pin set as output
GPIO.setup(pwmPin, GPIO.OUT)    # PWM pin set as output
pwm = GPIO.PWM(pwmPin, 50)      # Initialize PWM on pwmPin 100Hz frequency
GPIO.setup(butPin, GPIO.IN, pull_up_down=GPIO.PUD_UP) # Button pin set as input w/ pull-up

class gpio_in:
    def __init__(self, pin)
        
