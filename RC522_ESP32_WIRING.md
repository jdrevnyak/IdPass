# RC522 to ESP32 Wiring Guide

## Hardware Connections

Connect your RC522 RFID module to the ESP32 as follows:

| RC522 Pin | ESP32 Pin | Description |
|-----------|-----------|-------------|
| VCC       | 3.3V      | Power supply (3.3V) |
| GND       | GND       | Ground |
| RST       | GPIO 22   | Reset pin |
| SDA/SS    | GPIO 21   | SPI Slave Select |
| SCK       | GPIO 18   | SPI Clock |
| MOSI      | GPIO 23   | SPI Master Out Slave In |
| MISO      | GPIO 19   | SPI Master In Slave Out |
| IRQ       | Not used  | Interrupt (not connected) |

## Arduino IDE Setup

1. **Install ESP32 Board Support:**
   - Open Arduino IDE
   - Go to File → Preferences
   - Add this URL to "Additional Board Manager URLs":
     ```
     https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
     ```
   - Go to Tools → Board → Boards Manager
   - Search for "ESP32" and install "ESP32 by Espressif Systems"

2. **Install MFRC522 Library:**
   - Go to Tools → Manage Libraries
   - Search for "MFRC522"
   - Install "MFRC522 by GithubCommunity" (latest version)

3. **Board Configuration:**
   - Select your ESP32 board from Tools → Board
   - Select the correct COM port from Tools → Port
   - Set upload speed to 115200

## Code Upload

1. Open the `esp32_nfc_reader.ino` file in Arduino IDE
2. Select your ESP32 board and port
3. Click Upload
4. Open Serial Monitor (115200 baud) to see output

## Expected Output

When working correctly, you should see:
```
ESP32 RC522 NFC Reader Starting...
Initializing SPI...
SPI Initialized
RC522 Initialized
Checking RC522 connection...
[RC522 version info]
RC522 Self-test passed!
System ready!
Waiting for RFID cards...
```

When a card is detected:
```
Found an RFID card
  UID Length: 4 bytes
  UID Value:  0x12 0x34 0x56 0x78
Card Type: MIFARE 1KB
```

## Troubleshooting

### "RC522 Self-test failed!"
- Check all wiring connections
- Ensure RC522 is getting 3.3V power
- Verify SPI connections are secure
- Try different GPIO pins if needed

### "No card detected"
- Hold card closer to RC522 antenna
- Try different cards (MIFARE Classic works best)
- Check for interference from other devices

### "Serial port errors"
- Check USB cable connection
- Verify correct COM port is selected
- Try pressing reset button on ESP32

## Supported Card Types

The RC522 supports:
- MIFARE Classic 1K/4K
- MIFARE Ultralight
- MIFARE DESFire (basic UID reading)
- Most ISO14443A compatible cards

## Notes

- Use 3.3V power only (5V may damage the RC522)
- Keep wires short for reliable SPI communication
- The IRQ pin is optional and not used in this setup
- Cards should be held close (1-3cm) from the RC522 antenna
