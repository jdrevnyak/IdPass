# This script runs on a Raspberry Pi 5.
# It continuously listens for incoming data on the serial port (UART).
# When it receives a message, it prints it and sends a reply back.
#
# Before running:
# 1. Enable the serial port in `raspi-config`:
#    - Run `sudo raspi-config`
#    - Go to `3 Interface Options` -> `I6 Serial Port`
#    - Say "No" to the login shell over serial.
#    - Say "Yes" to enabling the hardware serial port.
#    - Reboot the Raspberry Pi.
# 2. Install the PySerial library:
#    - Run `pip install pyserial` in your terminal.
#
# Wiring to ESP32:
# - Raspberry Pi GND <--> ESP32 GND
# - Raspberry Pi TX (GPIO 14) <--> ESP32 RX2 (GPIO 16)
# - Raspberry Pi RX (GPIO 15) <--> ESP32 TX2 (GPIO 17)

import serial
import time

def main():
    # Configure the serial port.
    # The port is typically '/dev/ttyAMA0' for Raspberry Pi hardware UART.
    # Baud rate must match the ESP32's rate.
    try:
        ser = serial.Serial(
            port='/dev/ttyAMA0',
            baudrate=115200,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
            timeout=1  # a timeout of 1 second
        )
        print("Raspberry Pi UART Listener Initialized.")
        print(f"Listening on {ser.name}...")

        while True:
            # Check if there is data in the buffer
            if ser.in_waiting > 0:
                # Read a line from the serial port (waits until a newline is received)
                line = ser.readline()
                
                # Decode the bytes into a string and strip whitespace
                message = line.decode('utf-8').strip()
                print(f"Message received from ESP32: {message}")

                # Send a reply back to the ESP32
                reply = "Hello from Raspberry Pi"
                ser.write(reply.encode('utf-8'))
                print(f"Sent reply: {reply}")
            
            # A small delay to prevent the loop from running too fast
            time.sleep(0.1)

    except serial.SerialException as e:
        print(f"Error opening serial port: {e}")
        print("Please ensure the serial port is enabled and the correct device is used.")
    except KeyboardInterrupt:
        print("\nProgram interrupted. Closing serial port.")
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()
            print("Serial port closed.")

if __name__ == '__main__':
    main()
