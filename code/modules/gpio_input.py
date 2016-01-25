#gpio-input
#for reading gpios

import RPi.GPIO as GPIO

class dev:
    def __init__(self, pin, callback):
        self.pin = pin
        self.callback = callback
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin, GPIO.IN)
        GPIO.add_event_detect(pin, GPIO.BOTH, callback = self.call)
    def call(self, channel):
        self.callback(self.pin, self.get_value())
    def get_value(self):
        print "reading pin " + str(self.pin)
        return GPIO.input(self.pin)
    def gpio_exit(self):
        GPIO.cleanup(self.pin)

def get_form():
    return "module-templates/gpio.html"
def get_dtype():
    return "input"
