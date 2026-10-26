# CS 350: Emerging Systems Architectures and Technologies

**Acram Kiyingi · Southern New Hampshire University · Fall 2026**

This repository holds two artifacts from CS 350. Both run on a Raspberry Pi 4 Model B with Ubuntu Server 24.04, and both are written in Python with `gpiozero` and `python-statemachine`.

| Artifact | Files |
|---|---|
| **7-1 Final Project: Thermostat Lab** | [`Thermostat.py`](Thermostat.py) · [`Thermostat_State_Machine.pdf`](Thermostat_State_Machine.pdf) (+ [`.drawio`](Thermostat_State_Machine.drawio) source) · [`CS350_Final_Project_Report_Kiyingi.docx`](CS350_Final_Project_Report_Kiyingi.docx), the architecture report comparing Raspberry Pi, Microchip, and NXP hardware for a cloud-connected version |
| **5-1 Milestone Three: Input With Buttons Lab** | [`Milestone3.py`](Milestone3.py) · [`Milestone3_State_Machine.pdf`](Milestone3_State_Machine.pdf) (+ [`.drawio`](Milestone3_State_Machine.drawio) source) |

---

## Artifact 1: Smart Thermostat Prototype

**Hardware:** SHT41 temperature/humidity sensor on I2C, a 16x2 character LCD, red and blue LEDs on PWM (GPIO 18 and 23), three push buttons (green on GPIO 24 cycles modes, red on GPIO 25 raises the set point, blue on GPIO 12 lowers it), and a UART link to a simulated cloud server.

**How it works:** A three-state machine (`off`, `heat`, `cool`) drives the system.
- In **heat**, the red LED fades while the room is below the set point and stays solid once it reaches it.
- In **cool**, the blue LED does the same while the room is above the set point.
- The LCD shows the date and time on line 1. Line 2 alternates between the temperature and the current state with the set point.
- Every 30 seconds the thermostat sends `state,temperature,setpoint` over the serial port.

## Artifact 2: Morse Code State Machine

**Hardware:** red LED (GPIO 18) for dots, blue LED (GPIO 23) for dashes, a button on GPIO 24, and the 16x2 LCD.

**How it works:** A six-state machine (`off`, `dot`, `dash`, `dotDashPause`, `letterPause`, `wordPause`) transmits **SOS** or **OK** in Morse code with exact timing: 500 ms dots, 1500 ms dashes, 250 ms between symbols, 750 ms between letters, and 3000 ms between words. Pressing the button switches the message, and the LCD shows which message is being sent.

---

## Reflection

### Summarize the project and what problem it was solving.

The course project was a prototype smart thermostat for a fictional company, SysTec. It had to read the room temperature, let a user choose heating or cooling and adjust a set point, show its status locally, and report its data to a server, which is the groundwork for connecting it to the cloud. The milestones built that system piece by piece. PWM taught LED control, UART taught serial communication, and Milestone Three taught button input and state machines. Module Six added the I2C sensor, and the final project combined everything into one embedded program. The report then answered the business question of what hardware SysTec should use for production. I recommended the Raspberry Pi Zero 2 W over the Microchip WFI32E01 and NXP RW612 options, based on peripheral support, Wi-Fi, and memory.

### What did you do particularly well?

I'm proudest of the state machine design and the troubleshooting. Both programs keep their behavior inside clearly named states and transitions, so the code matches the diagrams one to one. I also worked through problems the lab guides didn't cover. My Pi runs Ubuntu Server instead of Raspberry Pi OS, so I had to adapt the install steps and permissions. I traced a button that did nothing to both of its wires sitting on ground pins. I also caught a subtle `gpiozero` bug: `blink()` adds a hidden one-second off period unless `off_time=0` is set, which would have stretched every Morse gap. When my AHT20 sensor went missing, I switched the code to an SHT41 and kept the project working.

### Where could you improve?

My biggest lesson was about process, not code. On Milestone Three I uploaded the unmodified template instead of my finished file, and that cost me most of the grade. From now on I will check every submission against the rubric before I turn it in. I also want to start earlier. Several labs were finished under deadline pressure, and some hardware (the LCD, potentiometer, and sensor) arrived late because I didn't check my kit at the start of the course. On the code side, I would add automated tests and move pin numbers and timing values into a single configuration section.

### What tools and/or resources are you adding to your support network?

- **Library documentation:** `gpiozero`, `python-statemachine`, and Adafruit CircuitPython (SHT4x and character LCD)
- **Manufacturer datasheets** from Raspberry Pi, Microchip, and NXP for the hardware comparison
- **Diagnostic tools:** `i2cdetect`, which identified the wrong sensor on my I2C bus, and `gpiozero`'s mock pin factory for testing code without hardware
- **draw.io** for documenting state machines to industry standards
- **VS Code Remote-SSH** for editing directly on the Pi
- **Anthropic's Claude** as a coding and debugging assistant (see the AI acknowledgment below)
- My **instructor** and the course discussion boards

### What skills from this project will be particularly transferable to other projects and/or course work?

- **State machine design.** It applies to games, UI flows, network protocols, and any system with modes.
- **Hardware interface protocols.** I worked hands-on with GPIO, PWM, I2C, and UART, the building blocks of IoT and embedded work.
- **Concurrency.** I used threads to run the display, LED patterns, and serial output at the same time.
- **Testing without the target environment.** I used simulated pins and stand-in modules before deploying to the Pi.
- **Architecture analysis.** I evaluated hardware against business requirements and justified a recommendation with evidence.

These matter directly for my own work building software products.

### How did you make this project maintainable, readable, and adaptable?

- **Self-documenting states.** Each state and transition is named for what it means (`heat`, `cool`, `letterPause`), and entry and exit actions live in clearly labeled callbacks.
- **Diagrams that match the code.** Each program has a state machine diagram that mirrors its structure, so a new developer can read the diagram first.
- **Comments explain the why.** Comments cover the reasons behind non-obvious choices, like the `off_time=0` fix and the sensor substitution.
- **Clear separation of concerns.** The display, LED control, and serial reporting each run in their own function or thread, so one can change without breaking the others.
- **Debug output.** A `DEBUG` flag turns on a trace of every state change for troubleshooting.
- **Graceful recovery.** A failed sensor read shows "Sensor error" for one refresh and then recovers instead of crashing the display thread.
- **Easy hardware swaps.** Changing sensors only meant changing the import and the constructor, which is how I moved from the AHT20 to the SHT41.

---

## Running the code

Both programs run on the Raspberry Pi with `sudo`, because they need direct GPIO and I2C access on Ubuntu Server:

```bash
sudo pip3 install --break-system-packages python-statemachine adafruit-circuitpython-sht4x adafruit-circuitpython-charlcd pyserial
sudo python3 Thermostat.py
sudo python3 Milestone3.py
```

## Acknowledgment of AI use

I used Anthropic's Claude (Opus 5.5) throughout this course, as the assignment guidelines require me to acknowledge. Claude helped me:
- complete the code templates
- test the code against simulated hardware before I deployed it
- diagnose wiring and configuration problems from my photos and terminal output
- generate the state machine diagrams
- draft the written reports and this README

My own work was building and wiring the circuits, sourcing replacement hardware, running and debugging the code on my Raspberry Pi, recording the demonstration videos, and reviewing everything before submission.

> Anthropic. (2026). *Claude* (Opus 5.5) [Large language model]. https://claude.ai
