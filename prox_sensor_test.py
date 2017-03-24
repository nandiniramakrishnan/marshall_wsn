import time

# Import SPI library (for hardware SPI) and MCP3008 library.
import Adafruit_GPIO.SPI as SPI
import Adafruit_MCP3008


# Software SPI configuration:
CLK  = 8#13#5
MISO = 11#19#6
MOSI = 20#24  
CS   = 21#25
mcp = Adafruit_MCP3008.MCP3008(clk=CLK, cs=CS, miso=MISO, mosi=MOSI)

# Main program loop.
while True:
    #read prox sensor value
    #prox sensor is on adc input 0
    time.sleep(0.001)
    raw_val = mcp.read_adc(0)
    if (raw_val > 11):
        true_val = 2076/(raw_val-11)
    else:
	    true_val = 0
    print(true_val)
#    time.sleep(0.5)
