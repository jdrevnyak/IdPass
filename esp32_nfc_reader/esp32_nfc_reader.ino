/*
 * ESP32 NFC Reader with UART Communication
 * 
 * WIRING CONNECTIONS:
 * 
 * RC522 NFC Module -> ESP32:
 * VCC   -> 3.3V
 * GND   -> GND
 * RST   -> GPIO 22
 * SDA   -> GPIO 21
 * SCK   -> GPIO 18
 * MOSI  -> GPIO 23
 * MISO  -> GPIO 19
 * IRQ   -> Not connected
 * 
 * ESP32 -> Raspberry Pi UART:
 * GPIO 16 (RXD2) -> GPIO 14 (TXD) on RPi
 * GPIO 17 (TXD2) -> GPIO 15 (RXD) on RPi
 * GND             -> GND on RPi
 * 
 * Note: Make sure to enable UART on Raspberry Pi:
 * 1. sudo raspi-config -> Interface Options -> Serial Port
 * 2. Disable login shell over serial: NO
 * 3. Enable serial port hardware: YES
 * 4. Add 'enable_uart=1' to /boot/config.txt
 * 5. Reboot Raspberry Pi
 */

#include <SPI.h>
#include <MFRC522.h>

// Define the pins for the RC522
#define RST_PIN     22    // Reset pin
#define SS_PIN      21    // Slave Select pin

// UART pins for communication with Raspberry Pi
#define RXD2 16
#define TXD2 17

// Create MFRC522 instance
MFRC522 mfrc522(SS_PIN, RST_PIN);

void setup() {
  // Initialize USB Serial for debugging (optional - can be removed for production)
  Serial.begin(115200);
  
  // Initialize UART Serial for communication with Raspberry Pi
  Serial2.begin(115200, SERIAL_8N1, RXD2, TXD2);
  
  Serial.println("\n\nESP32 RC522 NFC Reader Starting...");
  Serial.println("Initializing SPI...");
  Serial2.println("ESP32 NFC Reader Ready");
  
  // Initialize SPI bus
  SPI.begin();
  Serial.println("SPI Initialized");
  
  // Initialize MFRC522
  mfrc522.PCD_Init();
  Serial.println("RC522 Initialized");
  
  // Check if RC522 is connected
  Serial.println("Checking RC522 connection...");
  
  // Show details of PCD - MFRC522 Card Reader details
  mfrc522.PCD_DumpVersionToSerial();
  
  // Check if we can communicate with the RC522
  if (mfrc522.PCD_PerformSelfTest()) {
    Serial.println("RC522 Self-test passed!");
    mfrc522.PCD_Init(); // Re-initialize after self-test
  } else {
    Serial.println("ERROR: RC522 Self-test failed!");
    Serial.println("Please check your wiring:");
    Serial.println("RC522 -> ESP32");
    Serial.println("VCC   -> 3.3V");
    Serial.println("GND   -> GND");
    Serial.println("RST   -> GPIO 22");
    Serial.println("SDA   -> GPIO 21");
    Serial.println("SCK   -> GPIO 18");
    Serial.println("MOSI  -> GPIO 23");
    Serial.println("MISO  -> GPIO 19");
    Serial.println("IRQ   -> Not connected");
    while (1); // halt
  }
  
  Serial.println("System ready!");
  Serial.println("Waiting for RFID cards...");
}

void printCardType(MFRC522::PICC_Type piccType) {
  String typeName = mfrc522.PICC_GetTypeName(piccType);
  Serial.print("Card Type: ");
  Serial.println(typeName);
  Serial2.print("Card Type: ");
  Serial2.println(typeName);
}

void readCardData() {
  // Check if we can read card data
  if (mfrc522.PICC_IsNewCardPresent()) {
    // Try to read additional card information
    Serial.println("Attempting to read card data...");
    
    // Show card type
    MFRC522::PICC_Type piccType = mfrc522.PICC_GetType(mfrc522.uid.sak);
    printCardType(piccType);
    
    // For MIFARE Classic cards, try to read some data
    if (piccType == MFRC522::PICC_TYPE_MIFARE_MINI ||
        piccType == MFRC522::PICC_TYPE_MIFARE_1K ||
        piccType == MFRC522::PICC_TYPE_MIFARE_4K) {
      
      // Try to authenticate and read block 1
      MFRC522::MIFARE_Key key;
      for (byte i = 0; i < 6; i++) {
        key.keyByte[i] = 0xFF; // Default key
      }
      
      byte block = 1;
      byte buffer[18];
      byte size = sizeof(buffer);
      
      // Authenticate
      MFRC522::StatusCode status = mfrc522.PCD_Authenticate(
        MFRC522::PICC_CMD_MF_AUTH_KEY_A, block, &key, &(mfrc522.uid));
      
      if (status == MFRC522::STATUS_OK) {
        // Read block
        status = mfrc522.MIFARE_Read(block, buffer, &size);
        if (status == MFRC522::STATUS_OK) {
          Serial.print("Data in block "); Serial.print(block); Serial.print(": ");
          for (byte i = 0; i < 16; i++) {
            if (buffer[i] < 0x10) Serial.print("0");
            Serial.print(buffer[i], HEX);
            Serial.print(" ");
          }
          Serial.println();
        } else {
          Serial.print("Failed to read block: ");
          Serial.println(mfrc522.GetStatusCodeName(status));
        }
      } else {
        Serial.print("Authentication failed: ");
        Serial.println(mfrc522.GetStatusCodeName(status));
      }
    }
    
    // Halt PICC
    mfrc522.PICC_HaltA();
    // Stop encryption on PCD
    mfrc522.PCD_StopCrypto1();
  }
}

void loop() {
  // Reset the loop if no new card present on the sensor/reader
  if (!mfrc522.PICC_IsNewCardPresent()) {
    return;
  }

  // Select one of the cards
  if (!mfrc522.PICC_ReadCardSerial()) {
    return;
  }

  // Card detected!
  Serial.println("\nFound an RFID card");
  Serial.print("  UID Length: "); 
  Serial.print(mfrc522.uid.size, DEC); 
  Serial.println(" bytes");
  
  // Send to Raspberry Pi via UART
  Serial2.println("\nFound an RFID card");
  Serial2.print("  UID Length: "); 
  Serial2.print(mfrc522.uid.size, DEC); 
  Serial2.println(" bytes");
  
  Serial.print("  UID Value: ");
  Serial2.print("  UID Value: ");
  for (byte i = 0; i < mfrc522.uid.size; i++) {
    Serial.print(" 0x");
    Serial2.print(" 0x");
    if (mfrc522.uid.uidByte[i] < 0x10) {
      Serial.print("0");
      Serial2.print("0");
    }
    Serial.print(mfrc522.uid.uidByte[i], HEX);
    Serial2.print(mfrc522.uid.uidByte[i], HEX);
  }
  Serial.println("");
  Serial2.println("");
  
  // Print card type
  MFRC522::PICC_Type piccType = mfrc522.PICC_GetType(mfrc522.uid.sak);
  printCardType(piccType);
  
  // Try to read additional card data (optional)
  readCardData();
  
  // Halt PICC
  mfrc522.PICC_HaltA();
  // Stop encryption on PCD
  mfrc522.PCD_StopCrypto1();
  
  // Wait 200ms before continuing to avoid multiple reads
  delay(200);
} 