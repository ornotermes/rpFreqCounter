from machine import I2C, Pin
from ssd1306 import SSD1306_I2C
from FreqPIO import FreqPIO

machine.freq(200_000_000) # Set the CPU frequency, will also be used by the counter State Machine, needs to be at least 4x the measured freq
PPM = 0 # PPM error between clocks
offsetIF = 0 # Frequency offset

def refreshDisplay():
    freq = counter.read()*(1+PPM/1000000.0)+offsetIF # Read frequency from counter, do PPM compensation, and add offset
    oled.fill(0) # Clear framebuffer
    oled.text("%f MHz" %(freq/(1000000.0)), 0, 0) # Print frequency to framebuffer
    oled.show() # Send framebuffer to display
    
def pioInt(pio): # PIO interrupt handler
    flags = pio.irq().flags() # Store IRQ flags
    refreshDisplay() # Update the display
    counter.restart() # Restart the frequency counter to clear it
    counter.run() # Start counting again

i2c = I2C(0) # Initialize I2C
oled = SSD1306_I2C(128, 64, i2c) # Initialize display
counter = FreqPIO(pioID=0, InputPin=Pin(15, Pin.IN, Pin.PULL_UP)) # Initialize frequency counter
counter.irq(pioInt) # Setup IRQ callback to catch the PIO interrupt
counter.run() # Start the counter

while True:
    machine.lightsleep(1) # Take a power nap