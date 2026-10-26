#
# Thermostat - This is the Python code used to demonstrate
# the functionality of the thermostat that we have prototyped throughout
# the course. 
#
# This code works with the test circuit that was built for module 7.
#
# Functionality:
#
# The thermostat has three states: off, heat, cool
#
# The lights will represent the state that the thermostat is in.
#
# If the thermostat is set to off, the lights will both be off.
#
# If the thermostat is set to heat, the Red LED will be fading in 
# and out if the current temperature is below the set temperature;
# otherwise, the Red LED will be on solid.
#
# If the thermostat is set to cool, the Blue LED will be fading in 
# and out if the current temperature is above the set temperature;
# otherwise, the Blue LED will be on solid.
#
# One button will cycle through the three states of the thermostat.
#
# One button will raise the setpoint by a degree.
#
# One button will lower the setpoint by a degree.
#
# The LCD display will display the date and time on one line and
# alternate the second line between the current temperature and 
# the state of the thermostat along with its set temperature.
#
# The Thermostat will send a status update to the TemperatureServer
# over the serial port every 30 seconds in a comma delimited string
# including the state of the thermostat, the current temperature
# in degrees Fahrenheit, and the setpoint of the thermostat.
#
#------------------------------------------------------------------
# Change History
#------------------------------------------------------------------
# Version   |   Description
#------------------------------------------------------------------
#    1          Initial Development
#    2          Completed the template (Acram Kiyingi):
#               - Uses an Adafruit SHT41 sensor (I2C address 0x44)
#                 through adafruit_sht4x in place of the AHT20
#               - State machine entry/exit actions, the three button
#                 handlers, LED logic, LCD lines and UART output
#               - Sensor reads are locked (the display thread and the
#                 button threads both read the sensor) and fall back
#                 to the last good reading if one read fails
#               - LEDs only change when the required pattern changes,
#                 so the fade is not restarted every 10 seconds
#               - Reads the state with current_state_value, because
#                 current_state is deprecated in python-statemachine 3
#------------------------------------------------------------------

##
## Import necessary to provide timing in the main loop
##
from time import sleep
from datetime import datetime

##
## Imports required to allow us to build a fully functional state machine
##
from statemachine import StateMachine, State

##
## Imports necessary to provide connectivity to the 
## thermostat sensor and the I2C bus
##
import board
import adafruit_sht4x

##
## These are the packages that we need to pull in so that we can work
## with the GPIO interface on the Raspberry Pi board and work with
## the 16x2 LCD display
##
# import board - already imported for I2C connectivity
import digitalio
import adafruit_character_lcd.character_lcd as characterlcd

## This imports the Python serial package to handle communications over the
## Raspberry Pi's serial port. 
import serial

##
## Imports required to handle our Button, and our PWMLED devices
##
from gpiozero import Button, PWMLED

##
## This package is necessary so that we can delegate the blinking
## lights to their own thread so that more work can be done at the
## same time
##
from threading import Thread, Lock

##
## This is needed to get coherent matching of temperatures.
##
from math import floor

##
## DEBUG flag - boolean value to indicate whether or not to print 
## status messages on the console of the program
## 
DEBUG = True

##
## Create an I2C instance so that we can communicate with
## devices on the I2C bus.
##
i2c = board.I2C()

##
## Initialize our Temperature and Humidity sensor. This build uses an
## Adafruit SHT41 (I2C address 0x44) in place of the AHT20 (0x38)
## named in the lab guide; both report temperature in Celsius.
##
thSensor = adafruit_sht4x.SHT4x(i2c)

##
## The display thread and the button handlers run on different
## threads and both read the sensor, so reads are serialized with
## this lock to keep two I2C transactions from interleaving.
##
sensorLock = Lock()

##
## Initialize our serial connection
##
## Because we imported the entire package instead of just importing Serial and
## some of the other flags from the serial package, we need to reference those
## objects with dot notation.
##
## e.g. ser = serial.Serial
##
ser = serial.Serial(
        port='/dev/ttyS0', # This would be /dev/ttyAM0 prior to Raspberry Pi 3
        baudrate = 115200, # This sets the speed of the serial interface in
                           # bits/second
        parity=serial.PARITY_NONE,      # Disable parity
        stopbits=serial.STOPBITS_ONE,   # Serial protocol will use one stop bit
        bytesize=serial.EIGHTBITS,      # We are using 8-bit bytes 
        timeout=1          # Configure a 1-second timeout
)

##
## Our two LEDs, utilizing GPIO 18, and GPIO 23
##
redLight = PWMLED(18)
blueLight = PWMLED(23)


##
## ManagedDisplay - Class intended to manage the 16x2 
## Display
##
## This code is largely taken from the work done in module 4, and
## converted into a class so that we can more easily consume the 
## operational capabilities.
##
class ManagedDisplay():
    ##
    ## Class Initialization method to setup the display
    ##
    def __init__(self):
        ##
        ## Setup the six GPIO lines to communicate with the display.
        ## This leverages the digitalio class to handle digital 
        ## outputs on the GPIO lines. There is also an analagous
        ## class for analog IO.
        ##
        ## You need to make sure that the port mappings match the
        ## physical wiring of the display interface to the 
        ## GPIO interface.
        ##
        ## compatible with all versions of RPI as of Jan. 2019
        ##
        self.lcd_rs = digitalio.DigitalInOut(board.D17)
        self.lcd_en = digitalio.DigitalInOut(board.D27)
        self.lcd_d4 = digitalio.DigitalInOut(board.D5)
        self.lcd_d5 = digitalio.DigitalInOut(board.D6)
        self.lcd_d6 = digitalio.DigitalInOut(board.D13)
        self.lcd_d7 = digitalio.DigitalInOut(board.D26)

        # Modify this if you have a different sized character LCD
        self.lcd_columns = 16
        self.lcd_rows = 2 

        # Initialise the lcd class
        self.lcd = characterlcd.Character_LCD_Mono(self.lcd_rs, self.lcd_en, 
                    self.lcd_d4, self.lcd_d5, self.lcd_d6, self.lcd_d7, 
                    self.lcd_columns, self.lcd_rows)

        # wipe LCD screen before we start
        self.lcd.clear()

    ##
    ## cleanupDisplay - Method used to cleanup the digitalIO lines that
    ## are used to run the display.
    ##
    def cleanupDisplay(self):
        # Clear the LCD first - otherwise we won't be abe to update it.
        self.lcd.clear()
        self.lcd_rs.deinit()
        self.lcd_en.deinit()
        self.lcd_d4.deinit()
        self.lcd_d5.deinit()
        self.lcd_d6.deinit()
        self.lcd_d7.deinit()
        
    ##
    ## clear - Convenience method used to clear the display
    ##
    def clear(self):
        self.lcd.clear()

    ##
    ## updateScreen - Convenience method used to update the message.
    ##
    def updateScreen(self, message):
        self.lcd.clear()
        self.lcd.message = message

    ## End class ManagedDisplay definition  

##
## Initialize our display
##
screen = ManagedDisplay()

##
## TemperatureMachine - This is our StateMachine implementation class.
## The purpose of this state machine is to manage the three states
## handled by our thermostat:
##
##  off
##  heat
##  cool
##
##
class TemperatureMachine(StateMachine):
    "A state machine designed to manage our thermostat"

    ##
    ## Define the three states for our machine.
    ##
    ##  off  - both LEDs off
    ##  heat - red LED fades below the set point, solid at or above it
    ##  cool - blue LED fades above the set point, solid at or below it
    ##
    off = State(initial = True)
    heat = State()
    cool = State()

    ##
    ## Default temperature setPoint is 72 degrees Fahrenheit
    ##
    setPoint = 72

    ##
    ## cycle - event that provides the state machine behavior
    ## of transitioning between the three states of our 
    ## thermostat
    ##
    cycle = (
        off.to(heat) |
        heat.to(cool) |
        cool.to(off)
    )

    ##
    ## on_enter_heat - Action performed when the state machine transitions
    ## into the 'heat' state
    ##
    def on_enter_heat(self):
        ## Set the red LED for the new state (fading or solid)
        self.updateLights()

        if(DEBUG):
            print("* Changing state to heat")

    ##
    ## on_exit_heat - Action performed when the statemachine transitions
    ## out of the 'heat' state.
    ##
    def on_exit_heat(self):
        ## The red LED only indicates heating, so turn it off
        redLight.off()

    ##
    ## on_enter_cool - Action performed when the state machine transitions
    ## into the 'cool' state
    ##
    def on_enter_cool(self):
        ## Set the blue LED for the new state (fading or solid)
        self.updateLights()

        if(DEBUG):
            print("* Changing state to cool")
    
    ##
    ## on_exit_cool - Action performed when the statemachine transitions
    ## out of the 'cool' state.
    ##
    def on_exit_cool(self):
        ## The blue LED only indicates cooling, so turn it off
        blueLight.off()

    ##
    ## on_enter_off - Action performed when the state machine transitions
    ## into the 'off' state
    ##
    def on_enter_off(self):
        ## Neither heating nor cooling, so both LEDs are off
        redLight.off()
        blueLight.off()

        if(DEBUG):
            print("* Changing state to off")
    
    ##
    ## processTempStateButton - Utility method used to send events to the 
    ## state machine. This is triggered by the button_pressed event
    ## handler for our first button
    ##
    def processTempStateButton(self):
        if(DEBUG):
            print("Cycling Temperature State")

        ## off -> heat -> cool -> off
        self.send("cycle")

    ##
    ## processTempIncButton - Utility method used to update the 
    ## setPoint for the temperature. This will increase the setPoint
    ## by a single degree. This is triggered by the button_pressed event
    ## handler for our second button
    ##
    def processTempIncButton(self):
        if(DEBUG):
            print("Increasing Set Point")

        ## Raise the target by one degree, then re-check the LEDs
        ## because the room may now be below or at the new target
        self.setPoint += 1
        self.updateLights()

    ##
    ## processTempDecButton - Utility method used to update the 
    ## setPoint for the temperature. This will decrease the setPoint
    ## by a single degree. This is triggered by the button_pressed event
    ## handler for our third button
    ##
    def processTempDecButton(self):
        if(DEBUG):
            print("Decreasing Set Point")

        ## Lower the target by one degree, then re-check the LEDs
        self.setPoint -= 1
        self.updateLights()

    ##
    ## updateLights - Utility method to update the LED indicators on the 
    ## Thermostat
    ##
    ## Last LED pattern applied, so a pattern that is already running
    ## (a fade in particular) is not restarted on every refresh
    ledPattern = None

    def updateLights(self):
        ## Make sure we are comparing temperatures in the correct scale
        temp = floor(self.getFahrenheit())
        state = self.current_state_value
    
        ## Verify values for debug purposes
        if(DEBUG):
            print(f"State: {state}")
            print(f"SetPoint: {self.setPoint}")
            print(f"Temp: {temp}")

        # Determine visual identifiers
        ##
        ## heat: red fades while the room is below the set point and
        ##       is solid once it is at or above the set point
        ## cool: blue fades while the room is above the set point and
        ##       is solid once it is at or below the set point
        ## off:  both LEDs off
        ##
        if state == "heat":
            pattern = "red-fade" if temp < self.setPoint else "red-solid"
        elif state == "cool":
            pattern = "blue-fade" if temp > self.setPoint else "blue-solid"
        else:
            pattern = "off"

        ## Only touch the LEDs when the required pattern changes
        if pattern == self.ledPattern:
            return
        self.ledPattern = pattern

        redLight.off()
        blueLight.off()
        if pattern == "red-fade":
            redLight.pulse()
        elif pattern == "red-solid":
            redLight.on()
        elif pattern == "blue-fade":
            blueLight.pulse()
        elif pattern == "blue-solid":
            blueLight.on()

        if(DEBUG):
            print(f"* LEDs: {pattern}")

    ##
    ## run - kickoff the display management functionality of the thermostat
    ##
    def run(self):
        myThread = Thread(target=self.manageMyDisplay)
        myThread.start()

    ##
    ## Get the temperature in Fahrenheit
    ##
    ## Last good reading, used if a single sensor read fails
    lastFahrenheit = None

    def getFahrenheit(self):
        try:
            with sensorLock:
                t = thSensor.temperature
            self.lastFahrenheit = ((9/5) * t) + 32
        except (OSError, RuntimeError) as error:
            ## A failed I2C read (or a bad CRC) should not stop the
            ## thermostat; keep using the previous reading if we have one
            if self.lastFahrenheit is None:
                raise
            if(DEBUG):
                print(f"* Sensor read failed, using last reading: {error}")
        return self.lastFahrenheit
    
    ##
    ##  Configure output string for the Thermostat Server
    ##
    def setupSerialOutput(self):
        ##
        ## One comma delimited line: state, current temperature (F),
        ## set point (F), e.g. "heat,71.42,72". The newline ends the
        ## line so the server's readline() returns it.
        ##
        output = f"{self.current_state_value},{self.getFahrenheit():0.2f},{self.setPoint}\n"
        
        return output
    
    ## Continue display output
    endDisplay = False

    ##
    ##  This function is designed to manage the LCD Display
    ##
    def manageMyDisplay(self):
        counter = 1
        altCounter = 1
        while not self.endDisplay:
            ## Only display if the DEBUG flag is set
            if(DEBUG):
                print("Processing Display Info...")
    
            ## Grab the current time        
            current_time = datetime.now()
    
            ## Setup display line 1: date and time, exactly 16
            ## characters, e.g. "Oct 19  10:49:03"
            lcd_line_1 = current_time.strftime("%b %d  %H:%M:%S") + "\n"
    
            ## Setup Display Line 2
            if(altCounter < 6):
                ## Seconds 1-5: current temperature, e.g. "Temp: 71.4F"
                lcd_line_2 = f"Temp: {self.getFahrenheit():0.1f}F"
    
                altCounter = altCounter + 1
            else:
                ## Seconds 6-10: state and set point, e.g. "HEAT Set: 72F"
                lcd_line_2 = f"{self.current_state_value.upper()} Set: {self.setPoint}F"
    
                altCounter = altCounter + 1
                if(altCounter >= 11):
                    # Run the routine to update the lights every 10 seconds
                    # to keep operations smooth
                    self.updateLights()
                    altCounter = 1
    
            ## Update Display
            screen.updateScreen(lcd_line_1 + lcd_line_2)
    
            ## Update server every 30 seconds
            if(DEBUG):
               print(f"Counter: {counter}")
            if((counter % 30) == 0):
                ## Send "state,temperature,setpoint" to the server
                ser.write(self.setupSerialOutput().encode("utf-8"))

                counter = 1
            else:
                counter = counter + 1
            sleep(1)

        ## Cleanup display
        screen.cleanupDisplay()

    ## End class TemperatureMachine definition


##
## Setup our State Machine
##
tsm = TemperatureMachine()
tsm.run()


##
## Configure our green button to use GPIO 24 and to execute
## the method to cycle the thermostat when pressed.
##
greenButton = Button(24)
greenButton.when_pressed = tsm.processTempStateButton

##
## Configure our Red button to use GPIO 25 and to execute
## the function to increase the setpoint by a degree.
##
redButton = Button(25)
redButton.when_pressed = tsm.processTempIncButton

##
## Configure our Blue button to use GPIO 12 and to execute
## the function to decrease the setpoint by a degree.
##
blueButton = Button(12)
blueButton.when_pressed = tsm.processTempDecButton

##
## Setup loop variable
##
repeat = True

##
## Repeat until the user creates a keyboard interrupt (CTRL-C)
##
while repeat:
    try:
        ## wait
        sleep(30)

    except KeyboardInterrupt:
        ## Catch the keyboard interrupt (CTRL-C) and exit cleanly
        ## we do not need to manually clean up the GPIO pins, the 
        ## gpiozero library handles that process.
        print("Cleaning up. Exiting...")

        ## Stop the loop
        repeat = False
        
        ## Close down the display
        tsm.endDisplay = True
        sleep(1)