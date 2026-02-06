#include "esp_camera.h"
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include "soc/soc.h"           // Added for brownout fixing
#include "soc/rtc_cntl_reg.h"  // Added for brownout fixing

// I2C LCD settings
const int I2C_SDA = 14;
const int I2C_SCL = 15;
LiquidCrystal_I2C lcd(0x27, 16, 2); // Default address. We will scan in setup.
bool lcdFound = false;

// -----------------------------------------------------------------------------
// CONFIGURATION - CHANGE AS NEEDED
// -----------------------------------------------------------------------------
const char* WIFI_SSID = "Shashank";
const char* WIFI_PASS = "12345678";

// Server settings
// Automatically detected your computer's IP: 10.23.172.39
const char* SERVER_URL = "http://10.23.172.39:5000/recognize_face";
const char* API_TOKEN  = "esp32-cam-api-token-change-in-production";
const char* DEVICE_ID  = "esp32-room-1";

// Trigger settings
const int TRIGGER_BUTTON_PIN = 13;  // Push button pin (active LOW with pullup)
const int PIR_SENSOR_PIN = 12;      // PIR motion sensor pin (optional, set to -1 to disable)
const int LED_STATUS_PIN = 33;      // Small red LED on back (active LOW, inverted)
const int LED_SUCCESS_PIN = 2;      // Green LED (Active HIGH)
const int LED_FAILURE_PIN = 4;      // Flash LED (Active HIGH)
const int LED_RED_PIN = 12;         // External Red LED (Active HIGH) - Moved from 16
const int LED_BLUE_PIN = 3;         // Blue LED (Active HIGH) - Connected to RX pin

// Timing and retry settings
unsigned long lastCaptureTime = 0;
const unsigned long captureInterval = 5000; // 5 seconds between captures (Continuous Mode)
const int MAX_WIFI_RETRIES = 20;
const int MAX_HTTP_RETRIES = 3;
const unsigned long WIFI_RETRY_DELAY = 500; // ms
const unsigned long HTTP_RETRY_DELAY = 1000; // ms

// -----------------------------------------------------------------------------
// CAMERA PIN CONFIG (AI-THINKER V2)
// -----------------------------------------------------------------------------
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

// -----------------------------------------------------------------------------
// INITIALIZATION
// -----------------------------------------------------------------------------
bool initCamera() {
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 5000000;
  config.pixel_format = PIXFORMAT_JPEG;

  if (psramFound()) {
    config.frame_size = FRAMESIZE_VGA;
    config.jpeg_quality = 12; // Slightly lower quality (higher number) to save space
    config.fb_count = 1;      // Force single buffer to avoid overflow
  } else {
    config.frame_size = FRAMESIZE_CIF;
    config.jpeg_quality = 12;
    config.fb_count = 1;
  }

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed with error 0x%x\n", err);
    return false;
  }
  return true;
}

bool initWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.print("Connecting to WiFi");
  
  if (lcdFound) {
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("Connecting to");
    lcd.setCursor(0, 1);
    lcd.print("WiFi...");
  }
  digitalWrite(LED_BLUE_PIN, HIGH); // Turn on Blue LED while connecting

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < MAX_WIFI_RETRIES) {
    delay(WIFI_RETRY_DELAY);
    Serial.printf("Connecting... Status: %d, Attempt: %d/%d\n", WiFi.status(), attempts + 1, MAX_WIFI_RETRIES);
    digitalWrite(LED_STATUS_PIN, !digitalRead(LED_STATUS_PIN)); // Blink during connection
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi connected");
    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());
    
    if (lcdFound) {
      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print("WiFi Connected");
      lcd.setCursor(0, 1);
      lcd.print(WIFI_SSID);
      delay(2000);
    }

    digitalWrite(LED_BLUE_PIN, HIGH); // On
    digitalWrite(LED_STATUS_PIN, HIGH); // Off (active low)
    return true;
  } else {
    Serial.println("\nWiFi connection failed!");
    digitalWrite(LED_BLUE_PIN, LOW); // Off
    digitalWrite(LED_STATUS_PIN, HIGH); // Off
    return false;
  }
}

bool reconnectWiFi() {
  if (WiFi.status() == WL_CONNECTED) {
    return true;
  }
  Serial.println("WiFi disconnected, attempting reconnect...");
  return initWiFi();
}

void blinkLED(int times, int duration = 200) {
  for (int i = 0; i < times; i++) {
    digitalWrite(LED_STATUS_PIN, LOW);  // ON (active LOW)
    delay(duration);
    digitalWrite(LED_STATUS_PIN, HIGH); // OFF
    if (i < times - 1) delay(duration); // Gap between blinks
  }
}

bool captureAndRecognize() {
  // Ensure WiFi is connected
  if (!reconnectWiFi()) {
    return false;
  }
  
  digitalWrite(LED_BLUE_PIN, LOW);   // Off while processing
  digitalWrite(LED_STATUS_PIN, LOW); // On (Behind LED) during processing

  camera_fb_t * fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("Camera capture failed");
    blinkLED(3, 100); // Error indication
    return false;
  }

  Serial.printf("Captured image: %d bytes\n", fb->len);

  // Retry logic for HTTP request
  bool success = false;
  for (int retry = 0; retry < MAX_HTTP_RETRIES && !success; retry++) {
    if (retry > 0) {
      Serial.printf("Retry %d/%d\n", retry, MAX_HTTP_RETRIES);
      delay(HTTP_RETRY_DELAY * retry); // Exponential backoff
      reconnectWiFi(); // Reconnect before retry
    }

    HTTPClient http;
    http.begin(SERVER_URL);
    http.setTimeout(15000); // 15 second timeout for image upload
    
    // Set headers
    String authHeader = "Bearer ";
    authHeader += API_TOKEN;
    http.addHeader("Authorization", authHeader);
    http.addHeader("X-Device-ID", DEVICE_ID);
    
    // Build multipart/form-data body
    String boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW";
    String headerPart = "--" + boundary + "\r\n";
    headerPart += "Content-Disposition: form-data; name=\"image\"; filename=\"capture.jpg\"\r\n";
    headerPart += "Content-Type: image/jpeg\r\n\r\n";
    String footerPart = "\r\n--" + boundary + "--\r\n";
    
    // Calculate total size
    int headerLen = headerPart.length();
    int footerLen = footerPart.length();
    int totalLen = headerLen + fb->len + footerLen;
    
    // Allocate buffer for multipart body
    uint8_t* multipartBody = (uint8_t*)malloc(totalLen);
    if (!multipartBody) {
      Serial.println("Failed to allocate memory for multipart body");
      http.end();
      continue;
    }
    
    // Construct multipart body
    memcpy(multipartBody, headerPart.c_str(), headerLen);
    memcpy(multipartBody + headerLen, fb->buf, fb->len);
    memcpy(multipartBody + headerLen + fb->len, footerPart.c_str(), footerLen);
    
    http.addHeader("Content-Type", "multipart/form-data; boundary=" + boundary);
    
    // Send multipart body
    int httpCode = http.POST(multipartBody, totalLen);
    
    // Free allocated memory
    free(multipartBody);
    
    if (httpCode == HTTP_CODE_OK || httpCode == HTTP_CODE_CREATED) {
      String response = http.getString();
      Serial.printf("Response: %s\n", response.c_str());
      
      JsonDocument doc;
      DeserializationError error = deserializeJson(doc, response);
      
      if (!error) {
        String status = doc["status"] | "unknown";
        String name = doc["name"] | "unknown";
        
        Serial.printf("Recognition result: %s (%s)\n", name.c_str(), status.c_str());
        
        if (status == "recognized") {
          if (lcdFound) {
            lcd.clear();
            lcd.setCursor(0, 0);
            lcd.print("Welcome");
            lcd.setCursor(0, 1);
            lcd.print(name);
          }
          digitalWrite(LED_SUCCESS_PIN, HIGH);
          delay(1000);
          digitalWrite(LED_SUCCESS_PIN, LOW);
        } else if (status == "already_marked") {
          if (lcdFound) {
            lcd.clear();
            lcd.setCursor(0, 0);
            lcd.print("Already Marked");
            lcd.setCursor(0, 1);
            lcd.print(name);
          }
          digitalWrite(LED_SUCCESS_PIN, HIGH);
          delay(500);
          digitalWrite(LED_SUCCESS_PIN, LOW);
        } else if (status == "not_clear") {
          if (lcdFound) {
            lcd.clear();
            lcd.setCursor(0, 0);
            lcd.print("Not Clear");
            lcd.setCursor(0, 1);
            lcd.print("Try Again");
          }
          // Flash disabled by user request
          // digitalWrite(LED_FAILURE_PIN, HIGH);
          // delay(500);
          // digitalWrite(LED_FAILURE_PIN, LOW);
        } else if (status == "unknown") {
          if (lcdFound) {
            lcd.clear();
            lcd.setCursor(0, 0);
            lcd.print("Face Unknown");
          }
          digitalWrite(LED_RED_PIN, HIGH);
          delay(1000);
          digitalWrite(LED_RED_PIN, LOW);
        } else if (status == "no_face") {
          if (lcdFound) {
            lcd.clear();
            lcd.setCursor(0, 0);
            lcd.print("No Face Seen");
          }
          // Blue LED will turn back on at the end of function
        }
        success = true;
      } else {
        Serial.printf("JSON parse error: %s\n", error.c_str());
      }
    } else {
      Serial.printf("HTTP error: %d\n", httpCode);
      if (httpCode < 0) {
        Serial.printf("Error: %s\n", http.errorToString(httpCode).c_str());
      } else {
        String response = http.getString();
        Serial.printf("Response: %s\n", response.c_str());
      }
    }
    
    http.end();
  }
  
  digitalWrite(LED_STATUS_PIN, HIGH); // Off (active low) - Finished processing
  digitalWrite(LED_BLUE_PIN, HIGH);   // On - Back to Idle
  
  esp_camera_fb_return(fb);
  return success;
}

void setup() {
  WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0); // Disable brownout detector
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n\nESP32-CAM Face Recognition Attendance System");
  Serial.println("==============================================");
  
  // Initialize pins
  pinMode(LED_STATUS_PIN, OUTPUT);
  digitalWrite(LED_STATUS_PIN, HIGH); // Off initially
  
  pinMode(LED_SUCCESS_PIN, OUTPUT);
  digitalWrite(LED_SUCCESS_PIN, LOW); // Off
  
  pinMode(LED_FAILURE_PIN, OUTPUT);
  digitalWrite(LED_FAILURE_PIN, LOW); // Off (Onboard Flash)
  
  pinMode(LED_RED_PIN, OUTPUT);
  digitalWrite(LED_RED_PIN, LOW); // Off (External Red LED)
  
  pinMode(LED_BLUE_PIN, OUTPUT);
  digitalWrite(LED_BLUE_PIN, HIGH); // ON initially
  
  // Initialize I2C
  Wire.begin(I2C_SDA, I2C_SCL);
  
  // SCAN I2C for LCD Address
  Serial.println("Scanning I2C...");
  byte address = 0;
  for (byte i = 1; i < 127; i++) {
    Wire.beginTransmission(i);
    if (Wire.endTransmission() == 0) {
      Serial.printf("I2C device found at 0x%02X\n", i);
      address = i;
    }
  }
  
  if (address == 0) {
    Serial.println("No I2C devices found! Check wiring (SDA/SCL).");
    // Removed: digitalWrite(LED_FAILURE_PIN, HIGH); // Don't turn on flash if LCD is missing
    lcdFound = false;
  } else {
    lcdFound = true;
    lcd = LiquidCrystal_I2C(address, 16, 2);
    lcd.init();
    lcd.backlight();
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("Welcome");
    Serial.println("LCD Initialized with text 'Welcome'");
    delay(2000);
  }
  
  pinMode(TRIGGER_BUTTON_PIN, INPUT_PULLUP);
  if (PIR_SENSOR_PIN >= 0) {
    pinMode(PIR_SENSOR_PIN, INPUT);
  }
  
  // Initialize camera
  Serial.println("Initializing camera...");
  if (!initCamera()) {
    Serial.println("Camera initialization failed!");
    while (true) {
      blinkLED(5, 100); // Rapid blinking indicates camera failure
      delay(1000);
    }
  }
  Serial.println("Camera initialized successfully");
  
  // Initialize WiFi
  Serial.println("Initializing WiFi...");
  if (!initWiFi()) {
    Serial.println("WiFi initialization failed - device will work offline");
    blinkLED(2, 300); // 2 blinks for WiFi failure
  }
  
  Serial.println("System ready!");
  blinkLED(1, 100); // Quick blink to indicate ready
}

void loop() {
  unsigned long now = millis();
  
  // Continuous recognition trigger
  if (now - lastCaptureTime >= captureInterval) {
    lastCaptureTime = now;
    Serial.println("Auto-trigger: Starting continuous recognition...");
    captureAndRecognize();
  }
  
  // Periodic WiFi health check (every 30 seconds)
  static unsigned long lastWiFiCheck = 0;
  if (millis() - lastWiFiCheck > 30000) {
    lastWiFiCheck = millis();
    if (WiFi.status() != WL_CONNECTED) {
      Serial.println("WiFi disconnected, attempting reconnect...");
      reconnectWiFi();
    }
  }
  
  delay(50); // Small delay to prevent tight loop
}
