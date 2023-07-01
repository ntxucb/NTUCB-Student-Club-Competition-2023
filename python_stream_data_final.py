import numpy as np
import scipy.signal as signal
import pandas as pd
from brainflow.board_shim import BoardIds, BoardShim, BrainFlowInputParams
import socket
import serial
import cv2

# Cargar el clasificador HaarCascade preentrenado para detección de ojos
eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye_tree_eyeglasses.xml') # haarcascade_eye_tree_eyeglasses.xml 

# Iniciar la captura de video desde la cámara
cap = cv2.VideoCapture(1)

flag_counter = 0
flag_color = 0

#Inicio Socket
IP_RASP = "192.168.43.12" #IP de la Rasp
PUERTO = 5000
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((IP_RASP, PUERTO))

# Set the board ID for Cyton/Daisy
board_id = BoardIds.CYTON_BOARD.value

# Set the serial port name or IP address of the device
serial_port = 'COM16'  # Replace with the appropriate serial port on your system

# Define alpha band frequency range
alpha_band = (8, 13)  # Alpha band frequency range (in Hz)

# Sampling frequency (adjust accordingly if different)
fs = 256  # Example: 256 Hz

#funciones
def Socket(datos):
	data=str(datos)
	sock.sendall(data.encode())
# Function to detect alpha waves
def detect_alpha_waves(electrode_data):
    # Apply bandpass filter in the alpha band frequency range
    b, a = signal.butter(4, [alpha_band[0] / (fs / 2), alpha_band[1] / (fs / 2)], btype='bandpass')
    padlen = min(len(electrode_data), 27) - 1  # Adjust padlen to ensure it's smaller than the input data length
    filtered_data = signal.filtfilt(b, a, electrode_data, padlen=padlen)

    #filtered_data = signal.filtfilt(b, a, electrode_data)

    # Compute the power spectral density (PSD) using FFT
    freq, psd = signal.welch(filtered_data, fs=fs)

    # Find the index corresponding to the alpha band frequency range
    alpha_idx = np.where((freq >= alpha_band[0]) & (freq <= alpha_band[1]))[0]

    # Calculate the average power within the alpha band
    alpha_power = np.mean(psd[alpha_idx])

    return alpha_power

# Create an input parameters object
params = BrainFlowInputParams()
params.serial_port = serial_port

# Connect to the board
board = BoardShim(board_id, params)
board.prepare_session()

#electrodes = board.get_eeg_channels(board_id)
electrodes = [1,2,3,4]
alpha_power_arr = []
#print(electrodes)

# Start the data acquisition
board.start_stream()

while True:
    # Leer el fotograma actual de la cámara
    ret, frame = cap.read()

    # Convertir el fotograma a escala de grises
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Realizar la detección de ojos
    eyes = eye_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

    # Variables para determinar la posición de la mirada
    left_eye_found = False
    right_eye_found = False

    # Recorrer los ojos detectados
    for (x, y, w, h) in eyes:
        # Calcular la posición del centro del ojo
        eye_center_x = x + w // 2
        eye_center_y = y + h // 2

        # Dibujar un cuadrado alrededor del ojo
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

        # Determinar si el ojo está en la parte izquierda o derecha de la imagen
        if eye_center_x < frame.shape[1] // 3:
            left_eye_found = True
        elif eye_center_x > 2 * frame.shape[1] // 3:
            right_eye_found = True

    # Determinar la posición de la mirada
    if left_eye_found and right_eye_found:
        gaze_direction = "Frente"  # Ambos ojos detectados
        color = (0, 255, 255)  # Amarillo
    elif left_eye_found:
        gaze_direction = "Izquierda"  # Solo ojo izquierdo detectado
        color = (255, 0, 0)  # Azul
        if (flag_color == 1):
            Socket(2)
        flag_color = 0
    elif right_eye_found:
        gaze_direction = "Derecha"  # Solo ojo derecho detectado
        color = (0, 0, 255)  # Rosado
        if (flag_color == 0):
            Socket(1)
        flag_color = 1
    else:
        gaze_direction = "Desconocida"  # No se detectaron ojos
        color = (0, 0, 0)  # Negro

    # Mostrar el texto con la posición de la mirada en la imagen
    cv2.putText(frame, f"Mirada: {gaze_direction}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)

    # Mostrar el fotograma con las detecciones en una ventana
    cv2.imshow('Detección de mirada', frame)

    # Salir del bucle si se presiona la tecla 'q'
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
    
    # Retrieve data from the board
    data = board.get_board_data()

    # Check if there is any data available
    if data.shape[1] > 0:
        # Process and print the EEG data from all channels
        eeg_data = data[0:4, :]  # Assuming 4 channels, adjust accordingly
        #print(eeg_data)
        # Loop through each electrode and detect alpha waves
        for electrode in electrodes:
            electrode_data = data[electrode]  # Get the data for the electrode as a float array
            #print(electrode_data)
            alpha_power_arr.append(detect_alpha_waves(electrode_data))
        alpha_power = max(alpha_power_arr)
        for electrode in electrodes:
            if(alpha_power_arr[electrode-1] > 800000000):
                flag_counter = flag_counter + 1
            if (flag_counter == 2):
                Socket(3)
                print(3)
                flag_counter = 0;
        print(f'Alpha power: {alpha_power}')
        alpha_power_arr = []

sock.close()
# Stop the data acquisition and release the resources
board.stop_stream()
board.release_session()

# Liberar los recursos
cap.release()
cv2.destroyAllWindows()
