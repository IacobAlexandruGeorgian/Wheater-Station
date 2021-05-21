import RPi.GPIO as GPIO
from lib_nrf24 import NRF24
import time
import spidev
import numpy as np
import struct
from struct import *
import pylab
import matplotlib.pyplot as plt
import math
from sympy import randprime
import random

GPIO.setmode(GPIO.BCM) # ma refer la pini dupa GPIO

ID: int = 1
idx: int = 0

# Realizez o clasa in care voi scrie masuratorile
class Package:
    def __init__(self, humidity, tempC, pressure_KPa, altitude, timp):
        self.humidity = humidity
        self.tempC = tempC
        self.pressure_KPa = pressure_KPa
        self.altitude = altitude
        self.timp = timp
               
    def afisare(self):
        print("Umiditate: {} ".format(self.humidity))
        print("Temperatura: {} C".format(self.tempC))
        print("Presiune: {} KPa".format(self.pressure_KPa))
        print("Altitudine: {} m".format(self.altitude))
        print("Timp: {} s".format(self.timp))
        print("")
        
data = Package(0, 0, 0, 0, 0)

plt.title('Grafic') # creez graficul
plt.xlabel('Time [s]')
plt.ylabel('Umid & Temp [C] & Pres [KPa] & Alt [m]')
plt.ion()
plt.show() 
file = open("Output.txt", "w") # creez un fisier pentru a memora mesajul

# Realizez functia "Cel mai mic multiplu comun"    
def compute_lcm(x,y):
    if x > y:
        greater = x
    else:
        greater = y
    while(True):
        if((greater % x == 0) and (greater % y == 0)):
            lcm = greater
            break
        greater += 1
    return lcm

# Realizez functia "Invers multiplicativ modular"
def modInverse(a,m):
    m0 = m
    x = 1
    y = 0
    if (m == 1):
        return 0
    while (a > 1):
        q = a // m # coeficient
        t = m # reminder
        m = a % m
        a = t
        t = y
        y = x - q * y # modific x & y dupa fiecare iteratie
        x = t
    if (x < 0): # fac x pozitiv
        x = x + m0
    return x

# Realizez functia de decriptare asimetrica RSA       
def RSA_decriptare(numar_criptat, cheie_privata, N):
    numar_decriptat = pow(numar_criptat, cheie_privata) % N
    return numar_decriptat

pipes = [[0xE8, 0xE8, 0xF0, 0xF0, 0xE1], [0xF0, 0xF0, 0xF0, 0xF0, 0xE1]] # adresele canalului
radio = NRF24(GPIO, spidev.SpiDev()) # folosesc GPIO pins
radio.begin(0, 25) # pinii (GPIO) conectati la CE si CSN
# setari pentru nrf
radio.setPayloadSize(32) 
radio.setChannel(0x76)
radio.setDataRate(NRF24.BR_1MBPS)
radio.setPALevel(NRF24.PA_MIN)
 
radio.setAutoAck(True)
radio.enableDynamicPayloads()
radio.enableAckPayload()

radio.openWritingPipe(pipes[0]) 
radio.openReadingPipe(1, pipes[1])
radio.printDetails()

while(1): # loop infinit

    # creez o  cheie publica random si o convertesc intr-un char
    e = 3
    p = randprime(1,100)
    q = randprime(100,150)
    FI = compute_lcm(p-1,q-1)
    while p % e == 1:
        p = randprime(1,100)
    while q % e == 1:
        q = randprime(100,150)
    N = p * q
    FI = compute_lcm(p-1,q-1)
    cheie_publica_string = str(N) + " " + str(e) + " "
    cheie_publica = list(cheie_publica_string)

    # trimit cheia publica catre Arduino
    start = time.time()
    radio.write(cheie_publica)
    
    # primesc mesajul cifrat de la Arduino
    radio.startListening()
    while not radio.available(0): # mesajul nu a fost transmis --> sleep
        time.sleep(1 / 100)
        if time.time() - start > 2:
            break

    # citesc mesajul sa il afisez
    receivedMessage = []
    radio.read(receivedMessage, radio.getDynamicPayloadSize())
    radio.stopListening()

    # Daca mesajul nu este null --> continui procesul
    if receivedMessage[0] != 0:
        print("Send: {}".format(cheie_publica))
        print("")
        print("Received: {}".format(receivedMessage))
        print("")
        # Decodez mesajul cifrat
        message_string = "0"
        message_vector = [0,0,0,0,0]
        idx = 0
        for n in receivedMessage:
            if n >= 32 and n <= 126:
                if n == 32 and idx <= 4:
                    message_vector[idx] = int(message_string)
                    message_string = ""
                    idx += 1
                message_string += chr(n)
        
        # Stochez datele intr-o structura si le afisez in consola
        data = Package(message_vector[0], message_vector[1], message_vector[2], message_vector[3], message_vector[4])
        print("ID: {}".format(ID))
        print("Umiditate cifrata: {}".format(data.humidity))
        print("Temperatura cifrata: {} C".format(data.tempC))
        print("Presiune cifrata: {} KPa".format(data.pressure_KPa))
        print("Altitudine cifrata: {} m".format(data.altitude))
        print("Timp cifrat: {} s".format(data.timp)) 
        print("")

        # Descifrez masuratorile cu algoritmul de decriptare asimetrica RSA
        cheie_privata = modInverse(e,FI) # d reprezinta cheia privata
        data.humidity = RSA_decriptare(data.humidity, cheie_privata, N)
        data.tempC = RSA_decriptare(data.tempC, cheie_privata, N)
        data.pressure_KPa = RSA_decriptare(data.pressure_KPa, cheie_privata, N)
        data.altitude = RSA_decriptare(data.altitude, cheie_privata, N)
        data.timp = RSA_decriptare(data.timp, cheie_privata, N)
        print("Package: ")
        data.afisare()
        
        # Memorez mesajul intr-un fisier
        file.write("Package:\n")
        file.write("ID: {}\n".format(ID))
        file.write("Umiditate: {}\n".format(data.humidity))
        file.write("Temperatura: {} C\n".format(data.tempC))
        file.write("Presiune: {} KPa\n".format(data.pressure_KPa))
        file.write("Altitudine: {} m\n".format(data.altitude))
        file.write("Timp: {} s\n".format(data.timp))
        file.write("\n")
        file.flush()
        
        # Generez graficul
        plt.scatter(data.timp,data.humidity, label = 'Umiditate', color = 'b')
        plt.pause(0.01)
        plt.scatter(data.timp,data.tempC, label = 'Temperatura [c]', color = 'r')
        plt.pause(0.01)
        plt.scatter(data.timp,data.pressure_KPa, label = 'Presiune [KPa]', color = 'y')
        plt.pause(0.01)
        plt.scatter(data.timp,data.altitude, label = 'Altitudine [m]', color = 'g')
        plt.pause(0.01)
        if ID == 1:
            plt.legend()
            
        ID += 1
        time.sleep(3)