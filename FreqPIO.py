from machine import Pin, freq
from rp2 import PIO, asm_pio, StateMachine

# Set clock to at least 4x the frequency you are measuring with machine.freq(i)
# Bind function to PIO IRQ 0 callback with FreqPIO.irq(func)

@asm_pio()    
def PIO_COUNTER():
    set(x,0) # Set X to 0
    irq(7) # Raise IRQ 7
    wrap_target()
    label('loop')
    wait(0,pin,0) # Wait for pin to fall
    wait(0,irq,7) # Wait for IRQ 7 to clear (by the timer)
    wait(1,pin,0) # Wait for pin to rise
    jmp(x_dec,'loop') # Decrease X and loop back
    wrap()
    
@asm_pio()
def PIO_TIMER(): # Timer to start and stop the counter very precisely
    set(x, 31) # Set x to 31
    irq(clear,7) # Clear IRQ 7 to start the counter
    wrap_target()
    label('loop')
    nop() [31] # Keep busy for a while
    nop() [28]
    jmp(x_dec,'loop') # Decrease X by 1 and go back to the loop label if X is not 0
    nop() [14] # Fine tuning of the time
    irq(7) # Raise IRQ 7 to stop the counter
    irq(block,0) # Raise IRQ 0 and stop
    wrap() # A wrap that shouldn't happen
    
class FreqPIO:
    
    def __init__(self, pioID, InputPin):
        self.counter = 0
        self.pin = InputPin
        
        self.pio = PIO(pioID) # Initiate a PIO
        self.irq = self.pio.irq
        
        self.smc = self.pio.state_machine(0) # Prep State Machine 0 on PIO for the timer
        self.smc.init(PIO_COUNTER,freq=freq(),in_base=self.pin) # Initiate the counter SM at full CPU speed
        
        self.smt = self.pio.state_machine(1) # Prep SM1 on PIO for the timer
        self.smt.init(PIO_TIMER,freq=10_000) # Initiate the timer SM at 10kHz, was 2kHz and took 1 second
        self.multiplier = 5 # So now we need a multiplier applied to the counter to compensat, but we get faster refresh
        
    def restart(self): # Restart State Machines, clears everything and makes then ready for a re-run
        self.smc.restart()
        self.smt.restart()
        
    def run(self): # Run the State Machines, activate the counter first so it can raise the IRQ before the timer lowers it
        self.smc.active(1)
        self.smt.active(1)
        
    def read(self):
        self.smc.exec('mov(isr,x)') # Move the value of X in the State Machine in to the Input Shift Register
        self.smc.exec('push()') # Push the ISR in to the RX FIFO
        # The counter returns a negative number, but python don't get the negative and takes it as a large number.
        # We subtract that from the largest possible number (2³²-1) and multiply with the multiplier to get the actual frequency (as positive).
        self.counter = self.multiplier * (2**32-1 - self.smc.get()) 
        return self.counter # Return the value while we're at it
    
    def __del__(self):
        self.smc.active(0)
        self.smt.active(0)
