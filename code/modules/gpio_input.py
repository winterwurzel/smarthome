#gpio-input
#for reading gpios

import RPi.GPIO as GPIO

class gpio:
    def __init__(self, pin):
        self.pin = pin
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin, GPIO.IN)
    def get_value(self):
        print "reading pin " + str(self.pin)
        return GPIO.input(self.pin)
    def gpio_exit(self):
        GPIO.cleanup(self.pin)
