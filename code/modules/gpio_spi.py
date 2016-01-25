#gpio-serial
#for writing/reading spi

#source
#https://github.com/doceme/py-spidev

import spidev

class dev:
    def __init__(self, bus, sdevice):
        self.bus = bus
        self.sdevice = sdevice
        self.spi = spidev.SpiDev()
        self.spi.open(bus, sdevice)  #Connects to the specified SPI device, opening /dev/spidev-bus.device
    def write_value(self, valuelist):
        #Writes a list of values to SPI device.
        print "writing " + str(valuelist) + " to spi " + str(self.bus) + ", " + str(self.sdevice)
        return self.spi.writebytes(valuelist)
    def get_value(self, n):
        #Read n bytes from SPI device.
        print "reading spi " + str(self.bus) + ", " + str(self.sdevice)
        return self.spi.readbytes(n)          #n is number of bytes to read
    def xfer(self, valuelist):
        #Performs an SPI transaction. Chip-select should be released and reactivated between blocks. Delay specifies the delay in usec between blocks.
        return self.spi.xfer(valuelist)
    def xfer2(self, valuelist):
        #Performs an SPI transaction. Chip-select should be held active between blocks.
        return self.spi.xfer2(valuelist)
    def gpio_exit(self):
        self.spi.close()

def get_form():
    return "module-templates/gpio_spi.html"
def get_dtype():
    return "spi"
