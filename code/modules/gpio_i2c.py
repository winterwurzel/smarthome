#gpio-i2c
#for writing to i2c as master and recieve data

import smbus

def writeNumber(address, value, bus):
    bus.write_byte(address, value)
    # bus.write_byte_data(address, 0, value)
    return -1

def readNumber(address, bus):
    number = bus.read_byte(address)
    # number = bus.read_byte_data(address, 1)
    return number


class dev:
    def __init__(self, address):
        # for RPI version 1, use "bus = smbus.SMBus(0)"
        self.bus = smbus.SMBus(1)
        # This is the address we setup in the Arduino Program
        self.address = address  #0x04
    def write_value(self, value):
        print "writing " + str(value) + " to i2c " + str(self.address)
        return writeNumber(self.address, int(value), self.bus)
    def get_value(self):
        result = readNumber(self.address, self.bus)
        print "reading i2c " + str(self.address) + ", result: " + str(result)
        return result
    def gpio_exit(self):
        pass

def get_form():
    return "module-templates/gpio_i2c.html"
def get_dtype():
    return "i2c"
