#!/usr/bin/env python
"""
"elropi.py" for switching Elro devices using Python on Raspberry Pi
by Heiko H. 2012

This file uses RPi.GPIO to output a bit train to a 433.92 MHz transmitter, allowing you
to control light switches from the Elro brand.

Credits:
This file is mostly a port from C++ and Wiring to Python and the RPi.GPIO library, based on
C++ source code written by J. Lukas:
	http://www.jer00n.nl/433send.cpp
and Arduino source code written by Piepersnijder:
	http://gathering.tweakers.net/forum/view_message/34919677
Some parts have been rewritten and/or translated.

This code uses the Broadcom GPIO pin naming by default, which can be changed in the
"GPIOMode" class variable below.
For more on pin naming see: http://elinux.org/RPi_Low-level_peripherals

Version 1.0
"""

import time
import RPi.GPIO as GPIO

class dev:
    def __init__(self, pin, default_key, devNr):
        self.pin = pin  # GPIO Pin number
        # default key of the power plug, config DIP switches -> first 5 DIPs,
        # ON=1, OFF=0, as array, e.g. [1,1,1,1,1]
        self.default_key = default_key
        # individual number of the power plug, config DIP switches, only
        # one DIP of the second 5, DIP A = 1, B = 2, C = 3, ...
        self.devNr = devNr
        # init the remoteswitch class
        self.device = RemoteSwitch(device=devNr, key=default_key, pin=pin)
    def write_value(self, value):
        if value == 1:
        	self.device.switchOn()
        else:
        	self.device.switchOff()
    def gpio_exit(self):
        self.device.switchExit()

def get_form():
    return "module-templates/gpio_funk.html"
def get_dtype():
    return "output"


class RemoteSwitch(object):
	repeat = 10 # Number of transmissions
	pulselength = 300 # microseconds
	GPIOMode = GPIO.BCM

	def __init__(self, device, key=[1,1,1,1,1], pin=4):
		'''
		devices: A = 1, B = 2, C = 4, D = 8, E = 16
		key: according to dipswitches on your Elro receivers
		pin: according to Broadcom pin naming
		'''
		self.pin = pin
		self.key = key
		self.device = device
		GPIO.setmode(self.GPIOMode)
		GPIO.setup(self.pin, GPIO.OUT)

	def switchOn(self):
		self._switch(GPIO.HIGH)

	def switchOff(self):
		self._switch(GPIO.LOW)

	def _switch(self, switch):
		self.bit = [142, 142, 142, 142, 142, 142, 142, 142, 142, 142, 142, 136, 128, 0, 0, 0]

		for t in range(5):
			if self.key[t]:
				self.bit[t]=136
		x=1
		for i in range(1,6):
			if self.device & x > 0:
				self.bit[4+i] = 136
			x = x<<1

		if switch == GPIO.HIGH:
			self.bit[10] = 136
			self.bit[11] = 142

		bangs = []
		for y in range(16):
			x = 128
			for i in range(1,9):
				b = (self.bit[y] & x > 0) and GPIO.HIGH or GPIO.LOW
				bangs.append(b)
				x = x>>1

		GPIO.output(self.pin, GPIO.LOW)
		for z in range(self.repeat):
			for b in bangs:
				GPIO.output(self.pin, b)
				time.sleep(self.pulselength/1000000.)


if __name__ == '__main__':
	import sys
	GPIO.setwarnings(False)

	if len(sys.argv) < 3:
		print "usage:sudo python %s int_device int_state (e.g. '%s 2 1' switches device 2 on)" % \
			(sys.argv[0], sys.argv[0])
		sys.exit(1)


	# Change the key[] variable below according to the dipswitches on your Elro receivers.
	default_key = [1,1,1,1,1]

	# change the pin accpording to your wiring
	default_pin = 4 # GPIO 4
	devi = dev(default_pin, default_key, int(sys.argv[1]))
	#device = RemoteSwitch(  device= int(sys.argv[1]),
	#						key=default_key,
	#						pin=default_pin)

	if int(sys.argv[2]):
		#device.switchOn()
		devi.switchOn()
	else:
		#device.switchOff()
		devi.switchOff()
