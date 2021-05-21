#include "Wire.h"
#include "DHT.h" // libraria senzorului DHT11
#include "Adafruit_BMP085.h" // libraria senzorului BMP180
#include "SPI.h"
#include "RF24.h"
#include "printf.h"
#include "RF24_config.h"
#include "math.h"

#define Type DHT11 // constanta
int DHT11DataPin=2; // conectare pin
int BMP180SCLPin=A5;
int BMP180SDAPin=A4;
DHT HT(DHT11DataPin,Type); // creare obiect
RF24 radio(7,8); // CE,CSN
Adafruit_BMP085 BMP;

int id = 1;
int idx;
int e;
long int N;
long int masuratoare;
long int x;
long int numar_criptat;
int timp;
int setTime = 500; // 0.5 s  
int dt = 3000; // 3 s

char sendMessage[32];
char receivedMessage[32];
char *pch;

// Realizez o structura in care voi scrie masuratorile
struct package{
  long int humidity; // umiditate
  long int tempC; // tenperatura in grade Celsius
  long int pressure_KPa; // presiune
  long int altitude; // altitudine
  long int timp; // timp
};
typedef struct package Package;
Package data;
String humidity_string, tempC_string, pressure_string, altitude_string, timp_string;

// Algoritmul de criptare asimetrica RSA
long int RSA_criptare(long int masuratoare, int e, long int N){
  // realizez (masuratoare^e) mod N
  long int base = masuratoare;
  for (int i = 1; i < e; i++){
    masuratoare = masuratoare * base;
  }
  x = N;
  while (N < (masuratoare - x)){
    x = x + N;
  }
  numar_criptat = masuratoare - x;
  return numar_criptat;
}

void setup() {
  while (!Serial);
  Serial.begin(9600); // monitor virtual cu rata de biti 9600
  pinMode(DHT11DataPin,INPUT); // setez pinul ca fiind input
  HT.begin(); // start senzor 
  delay(setTime); // delay pentru setarea senzorului
  BMP.begin(); 
  delay(setTime);
  printf_begin();
  radio.begin();
  delay(setTime);
  radio.setChannel(0x76); // setari pentru nrf
  radio.setPALevel(RF24_PA_MAX);
  radio.openWritingPipe(0xF0F0F0F0E1LL);
  const uint64_t pipe = 0xE8E8F0F0E1LL;
  radio.openReadingPipe(1, pipe);
  radio.enableDynamicPayloads();
  radio.powerUp();
  delay(setTime);
}

void loop() { // loop infinit
  
  // Citirea si afisarea masuratorilor
  data.humidity=abs(HT.readHumidity()); // citeste umiditatea
  data.tempC=abs(HT.readTemperature()); // citeste temperatura in grade Celsius
  data.pressure_KPa=abs(BMP.readPressure()/1000); // citeste presiunea
  data.altitude=abs(BMP.readAltitude()); // citeste altitudinea
  data.timp = millis()/1000; // timpul in secunde
  
  // primesc cheia publica de la Raspberry Pi
  radio.startListening();
  char receivedMessage[32] = {0};
  if (radio.available()){
    radio.read(receivedMessage, sizeof(receivedMessage));
    radio.stopListening();

    // Daca mesajul nu este null --> continui procesul
    if (receivedMessage != NULL){

      // Afisez pe monitorul serial masuratorile in format .csv
      Serial.print(id);
      Serial.print(", ");
      Serial.print(data.humidity);
      Serial.print(", ");
      Serial.print(data.tempC);
      Serial.print(", ");
      Serial.print(data.pressure_KPa);
      Serial.print(", ");
      Serial.print(data.altitude);
      Serial.print(", ");
      Serial.print(data.timp);
      Serial.println();
      
      id = id + 1; 
      
      // Decodez cheia publica
      pch = strtok(receivedMessage," ");
      idx = 1;
      while (pch != NULL){
        if (idx == 1) N = atoi(pch);
        else if (idx == 2) e = atoi(pch);
        pch = strtok(NULL, " ");
        idx += 1; 
      }
      
      // Cifrez masuratorile cu algoritmul de criptare asimetrica RSA
      data.humidity = RSA_criptare(data.humidity, e, N);
      data.tempC = RSA_criptare(data.tempC, e, N);
      data.pressure_KPa = RSA_criptare(data.pressure_KPa, e, N);
      data.altitude = RSA_criptare(data.altitude, e, N);
      data.timp = RSA_criptare(data.timp, e, N);
      
      // Introduc valorile intr-un char []
      humidity_string = String(data.humidity);
      tempC_string = String(data.tempC);
      pressure_string = String(data.pressure_KPa);
      altitude_string = String(data.altitude);
      timp_string = String(data.timp);
      String data_string = humidity_string + " " + tempC_string + " " + pressure_string + " " + altitude_string + " " + timp_string + " ";
      strcpy(sendMessage, data_string.c_str());

      // trimit masuratorile cifrate catre Raspberry Pi
      radio.write(&sendMessage, sizeof(sendMessage)); 
      delay(dt);
    }
  }  
}