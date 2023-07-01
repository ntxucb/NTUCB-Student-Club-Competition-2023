#my 
import sys
import RPi.GPIO as GPIO
import socket
import threading
from time import sleep, strftime
import time
import smbus
from smbus2 import SMBus
import cv2
import requests
import datetime
from RPi_GPIO_i2c_LCD import lcd
from mlx90614 import MLX90614
GPIO.setwarnings(False)
TOKEN = "6089538491:AAH6XI0Utv_psjgg9OYwpOstKBvPn0Kut04"
CHAT_ID = "1015352132"

#lcd pantalla and temperature config
i2c_address = 0x27
bus = SMBus(1)
sensor = MLX90614(bus, address=0x5A)
#outputs
led_pin = 5
alarma = 6
ledMet=13

#inputs
pres=17
#door=27
touchPin = 27

GPIO.setmode(GPIO.BCM)
GPIO.setup(pres, GPIO.IN)
GPIO.setup(touchPin, GPIO.IN)
GPIO.setup(led_pin, GPIO.OUT)
GPIO.setup(ledMet, GPIO.OUT)
GPIO.setup(alarma, GPIO.OUT)
#-------------------------------------------------------------------
#Sensors functions
def leer_sensores():
    while True:
        if alarma_activada:
            if GPIO.input(pres) == GPIO.HIGH:
                print(f'Presence sensor detected, alarm activated')
                texto="Movement detected in the room"
                bot_send_text(texto)
                GPIO.output(alarma, GPIO.HIGH)
                sleep(1)
                GPIO.output(alarma, GPIO.LOW)
                print("---")               
            sleep(1)      
def temperature():
    while True:
        temp=round(sensor.get_amb_temp())
#       print(round(sensor.get_amb_temp()))
        if (temp>25):
            print(f'Temperature sensor detected, alarm activated')
            texto="Irregular temperature, danger of fire"
            bot_send_text(texto)
            GPIO.output(alarma, GPIO.HIGH)
            sleep(2)
            GPIO.output(alarma, GPIO.LOW)
            #print(round(sensor.get_obj_temp()))
        sleep(2)
def metal():
    # Almacenar el tiempo cuando ocurrió el último evento
    lastEvent = 0
    # Almacenar el estado del LED
    ledOn = False
    GPIO.output(ledMet, GPIO.LOW)
    c=0
    while True:
        if alarma_activada:
            touchState = read_sensor()
            if touchState == GPIO.HIGH:
                if time.time() - lastEvent > 0.1:
                    ledOn = not ledOn
                    GPIO.output(ledMet, GPIO.HIGH if ledOn else GPIO.LOW)
                    c+=1
                    print(f'Window sensor detected, alarm activated')
                    texto="Movement detected in the kitchen"
                    bot_send_text(texto)
                    GPIO.output(alarma, GPIO.HIGH)
                    sleep(1)
                    GPIO.output(alarma, GPIO.LOW)
                lastEvent = time.time()
def camara_vi1():
    show_frame = True
    while True:
        if alarma_activada:
            ret, frame = cap.read()
            gray = cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
            for (x, y, w, h) in faces:
                if (x>=150 and y>=20 and w>=100 and h>=100):  
                    cv2.rectangle(frame,(x,y),(x+w,y+h),(0,255,0),2)
                    print("-----")
                    texto="Body detected"
                    bot_send_text(texto)
                    GPIO.output(alarma,GPIO.HIGH)
                    sleep(0.7)
                else:
                    GPIO.output(alarma,GPIO.LOW)
            #cv2.imshow('Body Detection', frame)
# -------------------------------------------------------------
#Comunication with PC
def manejar_comunicacion(client_socket):
    global cap
    global alarma_activada
    while True:
        numero = client_socket.recv(1024).decode()
#         print(numero)
        if numero == '1' and not alarma_activada:
            lcdDisplay.backlight("on") 
            print('Alarm system activated')
            lcdDisplay.set("Alarm activated ",1)
            GPIO.output(led_pin, GPIO.HIGH)
            sleep(1)
            GPIO.output(led_pin, GPIO.LOW)
            alarma_activada = True
        elif numero == '2' and alarma_activada:
            print('Alarm system desactivated')
            lcdDisplay.set(" Alarm Disarmed ",1)
            GPIO.output(led_pin, GPIO.HIGH)
            sleep(2)
            GPIO.output(led_pin, GPIO.LOW)
            lcdDisplay.backlight("off")            
            alarma_activada = False
        elif numero == '3' and alarma_activada:
            print('Emergence')
            lcdDisplay.backlight("on") 
            lcdDisplay.set("  Emergence ON  ",1)
            GPIO.output(alarma, GPIO.HIGH)
            sleep(1)
            GPIO.output(alarma, GPIO.LOW)
            texto="Alarm activated emergence"
            bot_send_text(texto)
            alarma_activada = False  
#--------------------------------------------------------------------------------------
#AUXILIAR FUNCTIONS
#def lcd_date(self):
    #self.lcd.display_string(str(strftime("%d/%m %H:%M:%S").center(15,' ')),2) 
def Init_Webcam():
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT,480)

def bot_send_text(ses):
    bot_token = TOKEN
    bot_chatID = CHAT_ID
    D = [1, 0, 1, 0]
    fecha_actual = datetime.date.today().strftime("%d-%m-%Y")
    texto = f'''\
    \n\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\tEmergencia \

    \n\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\tFecha: {fecha_actual}\
    \n🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨\
    \n House Alarm\t\t\t\t\t\t\t\t\t\t\t\t
    \n🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨\
    \n{ses}\
    '''
    send_text = 'https://api.telegram.org/bot' + bot_token + '/sendMessage?chat_id=' + bot_chatID + '&parse_mode=Markdown&text=' + texto
    requests.get(send_text)
    
def read_sensor():
    touchState = GPIO.input(touchPin)
    return touchState

#----------------------------------------------------------------------------------------
#MAIN PRINCIPAL
HOST = ''  # accept all networks
PORT = 5000  # Port
face_cascade = cv2.CascadeClassifier('haarcascade_upperbody.xml')
cap = cv2.VideoCapture(0)
#lcdDisplay = lcd.HD44780(i2c_address,lcd_date)
lcdDisplay = lcd.HD44780(i2c_address)

lcdDisplay.set("Time:",1)
Init_Webcam()
# Create the socket and configure threads
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
    server_socket.bind((HOST, PORT))
    server_socket.listen()  # listen connections
    print('Esperando conexión...')
    client_socket, address = server_socket.accept()
    print('Conexión establecida:', address)
    alarma_activada = False
    
    sensor_thread = threading.Thread(target=leer_sensores)
    comunicacion_thread = threading.Thread(target=manejar_comunicacion, args=(client_socket,))
    metal_thread = threading.Thread(target=metal)
    camara_thread = threading.Thread(target=camara_vi1)
    temp_thread= threading.Thread(target=temperature)
    
    metal_thread.start()
    sensor_thread.start()
    comunicacion_thread.start()
    camara_thread.start()
    temp_thread.start()
    
    sensor_thread.join()
    comunicacion_thread.join()
    camara_thread.join()
    metal_thread.join()
    temp_thread.join()
    
    client_socket.close()