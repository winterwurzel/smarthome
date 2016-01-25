#gpio-output
#for writing gpios

import RPi.GPIO as GPIO

class dev:
    def __init__(self, pin):
        self.pin = pin
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin, GPIO.OUT)
    def write_value(self, value):
        print "writing " + str(value) + " to pin " + str(self.pin)
        return GPIO.output(self.pin, value)
    def gpio_exit(self):
        GPIO.cleanup(self.pin)

def get_form():
    return "module-templates/gpio.html"
def get_dtype():
    return "output"
