##################
# Import Modules #
##################

import vlc
import time
import random
import serial
import threading
import statistics
import math

from queue import Queue
from os import listdir
from os.path import isfile, join
from sense_hat import SenseHat

####################
# Global Variables #
####################

# Default starting BPM
the_bpm = 60
hat = SenseHat()

# Arrays for loading songs dynamically
songs_slow = []
songs_90_120 = []
songs_120_140 = []
songs_140_160 = []
songs_160_180 = []
songs_fast = []

# Interface for the Arudino
try:
    serial = serial.Serial('/dev/ttyACM0', 9600)
except:
    pass

# Variable to set the LED colour
white = (255,255,255)

# Music queue for the MusicThread
q = Queue(maxsize=1)

# Setup worker threads
songThread = threading.Thread(target=songWorker)
dataThread = threading.Thread(target=dataWorker)
bpmThread = threading.Thread(target=bpmWorker)
lightThread = threading.Thread(target=lightWorker)

####################
# Main Application #
####################

# Import songs into arrays from disk
importSongs()

dataThread.start()
songThread.start()
bpmThread.start()
lightThread.start()

#########################
# Methods and Functions #
#########################

def importSongs():
    songPath = "/home/pi/Music/SongStep"
    files = [f for f in listdir(songPath) if isfile(join(songPath, f))]

    for f in files:
        if f.endswith('.mp3'):
            #print("Importing Song: ", f)
            song_bpm = int(f.split("_")[0])
            songFile = join(songPath,f)
            
            if song_bpm < 90:
                songs_slow.append(songFile)
            elif song_bpm in range(90, 120):
                songs_90_120.append(songFile)
            elif song_bpm in range(120, 140):
                songs_120_140.append(songFile)
            elif song_bpm in range(140, 160):
                songs_140_160.append(songFile)
            elif song_bpm in range(160, 180):
                songs_160_180.append(songFile)
            elif song_bpm > 180:
                songs_fast.append(songFile)

def getBpm():
    steps = 0
    highest = 0
    lowest = 0
    mag_data = []
    gyro_data = []
    mag = []

    t_end = time.time() + 15.0
    while (time.time() < t_end):
        mag_data = hat.get_accelerometer_raw()
        gyro_x = mag_data['x']
        gyro_y = mag_data['y']
        gyro_z = mag_data['z']
        gyro_data = list((gyro_x**2, gyro_y**2, gyro_z**2))
        mag.append(math.sqrt(sum(gyro_data)))

    min_peak_height = statistics.stdev(mag) + statistics.mean(mag)
    for data in mag:
        #print(data)
        if data > min_peak_height:
            steps = steps + 1
        
        if data > highest:
            highest = data
        elif data < lowest:
            lowest = data

    print('BPM calculated: ', steps)
    return steps

def choose(bpm):
    print('BPM used: ', bpm)
    if bpm < 90:
        song = random.choice(songs_slow)
    elif bpm in range(90, 120):
        song = random.choice(songs_90_120)
    elif bpm in range(120, 140):
        song = random.choice(songs_120_140)
    elif bpm in range(140, 160):
        song = random.choice(songs_140_160)
    elif bpm in range(160, 180):
        song = random.choice(songs_160_180)
    elif bpm > 180:
        song = random.choice(songs_fast)
    print("Chosen Song: ", song)
    return song

def play(song):
    vlc_instance = vlc.Instance()
    player = vlc_instance.media_player_new()
    media = vlc_instance.media_new(song)
    player.set_media(media)
    player.play()
    time.sleep(1.5)
    duration = player.get_length() / 1000
    time.sleep(30)
    player.stop()
	
def bpmWorker():
    while True:
        global the_bpm
        the_bpm = getBpm()

def songWorker():
    while True:
        song = q.get()
        print("Playing: ", song)
        play(song)
        q.task_done()

def dataWorker():
    while True:
        if (q.empty()):
            q.put(choose(the_bpm))
            q.join() #stops anything being added until previous processing finished.

def getLightLevel():
    rawInput = serial.readline()
    parsedInput = rawInput.decode("utf-8").rstrip()
	
    try:
        return int(parsedInput)
    except:
        return 0

def lightWorker():
    while True:        
        lightLevel = getLightLevel()
        print("Light Level: ", lightLevel)
        if (lightLevel < 600):
            hat.clear(white)
        else:
            hat.clear()