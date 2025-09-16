# GPIO LED Wiring Guide for Student Attendance System

## Overview
This guide shows how to connect two LEDs to your Raspberry Pi 5 to indicate student status:
- **Red LED**: Lights up when students are out (bathroom breaks or nurse visits)
- **Green LED**: Lights up when no students are out

## Required Components
- 1x Red LED
- 1x Green LED  
- 2x 220Ω resistors
- Jumper wires
- Breadboard (optional)

## GPIO Pin Configuration
- **GPIO 16**: Green LED (no students out)
- **GPIO 18**: Red LED (students are out)
- **GND**: Common ground for both LEDs

## Wiring Instructions

### Red LED (Students Out Indicator)
1. Connect the **long leg (anode +)** of the red LED to a 220Ω resistor
2. Connect the other end of the resistor to **GPIO Pin 18**
3. Connect the **short leg (cathode -)** of the red LED to a **GND pin**

### Green LED (All Students Present Indicator)
1. Connect the **long leg (anode +)** of the green LED to a 220Ω resistor
2. Connect the other end of the resistor to **GPIO Pin 16**
3. Connect the **short leg (cathode -)** of the green LED to a **GND pin**

## Pin Layout (Raspberry Pi 5)
```
     3V3  (1) (2)  5V
   GPIO2  (3) (4)  5V
   GPIO3  (5) (6)  GND
   GPIO4  (7) (8)  GPIO14
     GND  (9) (10) GPIO15
  GPIO17 (11) (12) GPIO18  <- RED LED
  GPIO27 (13) (14) GND     <- Both LEDs ground
  GPIO22 (15) (16) GPIO23
     3V3 (17) (18) GPIO24
  GPIO10 (19) (20) GND
   GPIO9 (21) (22) GPIO25
  GPIO11 (23) (24) GPIO8
     GND (25) (26) GPIO7
   GPIO0 (27) (28) GPIO1
   GPIO5 (29) (30) GND
   GPIO6 (31) (32) GPIO12
  GPIO13 (33) (34) GND
  GPIO19 (35) (36) GPIO16  <- GREEN LED
  GPIO26 (37) (38) GPIO20
     GND (39) (40) GPIO21
```

## Breadboard Setup (Optional)
1. Place both LEDs on the breadboard
2. Connect resistors in series with each LED
3. Use jumper wires to connect to GPIO pins
4. Connect both LED cathodes to a common ground rail

## How It Works
- **System Startup**: Both LEDs turn off briefly, then green LED turns on (assuming no students out)
- **Student Goes Out**: Red LED turns on, green LED turns off
- **Student Returns**: Green LED turns on, red LED turns off
- **Multiple Students**: As long as ANY student is out, red LED stays on
- **Updates**: LEDs update immediately when students go out/return, plus every 5 seconds automatically

## Testing
1. Run the application
2. Green LED should be on initially
3. Use the bathroom or nurse buttons to send a student out
4. Red LED should turn on, green LED should turn off
5. Process the student's return
6. Green LED should turn on, red LED should turn off

## Troubleshooting
- **No LEDs working**: Check GPIO library installation (`sudo apt install python3-rpi.gpio`)
- **LEDs always off**: Check wiring connections and resistor values
- **Wrong LED behavior**: Verify GPIO pin assignments in code match wiring
- **LEDs too dim**: Try lower resistance values (180Ω or 150Ω)
- **LEDs too bright**: Use higher resistance values (330Ω or 470Ω)

## Safety Notes
- Always use current-limiting resistors with LEDs
- Double-check wiring before powering on
- GPIO pins output 3.3V - don't exceed LED forward voltage ratings
- Use appropriate resistor values for your specific LEDs



