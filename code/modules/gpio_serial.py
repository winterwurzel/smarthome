#gpio-serial
#for writing/reading serial

import serial

class dev:
    def __init__(self, port, baudrate):
        self.ser = serial.Serial(
               port=port,                       #'/dev/ttyAMA0'
               baudrate = baudrate,             #9600
               parity=serial.PARITY_NONE,
               stopbits=serial.STOPBITS_ONE,
               bytesize=serial.EIGHTBITS,
               timeout=1
           )
    def write_value(self, value):
        print "writing " + str(value) + " to serial " + str(self.ser.port)
        return self.ser.write(value)
    def get_value(self):
        print "reading serial " + str(self.ser.port)
        return self.ser.readline()
    def gpio_exit(self):
        pass
