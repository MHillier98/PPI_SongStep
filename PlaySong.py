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



########################
# Methods and Functions
########################

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
    duration = player.get_length()
    loop = True
    skip = False

    while loop:
        timeout_time = 0.2
        global bpm_changed
        			
        if player.get_time() < duration and skip == False and bpm_changed == False:
            timer = time.time() + timeout_time
            for event in hat.stick.get_events():
                if time.time() > timer:
                    print('break song: out of time (finished)')
                    break
                else:
                    if event.action == 'pressed':
                        if event.direction == 'down':
                            player.stop()
                            skip = True
                            break
                            print('break song: skip button pressed')
                        elif event.direction == 'left': #volume up
                            vol = player.audio_get_volume()
                            vol += 10
                            player.audio_set_volume(vol)
                            print('volume up')
                        elif event.direction == 'right': #volume down
                            vol = player.audio_get_volume()
                            vol -= 10
                            player.audio_set_volume(vol)
                            print('volume down')
                        elif event.direction == 'up': #toggle light?
                            global light_bool
                            if light_bool == True:
                                light_bool = False
                            else:
                                light_bool = True
                            print("light_bool", light_bool)
                        elif event.direction == 'middle': #play/pause
                            global song_paused
                            if player.is_playing():
                                song_paused = True
                                player.pause()
                                print('pause')
                            else:
                                song_paused = False
                                player.play()
                                print('play')
        else:
            bpm_changed = False
            loop = False
            #print('loop = False')
            player.stop()
            break

def songWorker():
    while True:
        song = q.get()
        print("Playing: ", song)
        
        global song_paused
        if song_paused == True:
            for event in hat.stick.get_events():
                if event.action == 'pressed' and event.direction == 'middle':
                    song_paused = False
        else:
            play(song)
        q.task_done()

def getLightLevel():
    rawInput = serial.readline()
    parsedInput = rawInput.decode("utf-8").rstrip()

    try:
        return int(parsedInput)
    except:
        return 0

def dataWorker():
    while True:
        if (q.empty()):
            q.put(choose(the_bpm))
            q.join() # stops anything being added until previous processing finished.

def lightWorker():
    while True:        
        lightLevel = getLightLevel()
        print("Light Level: ", lightLevel)
        global light_bool
        if light_bool == True:
            if lightLevel < 600:
                hat.clear(white)
            else:
                hat.clear()
        else:
            hat.clear()

def bpmWorker():
    while True:
        global the_bpm
        global last_bpm
        global bpm_changed

        if the_bpm > (last_bpm + 20):
            bpm_changed = True
            #print("the_bpm > (last_bpm + 20)")
        elif the_bpm < (last_bpm - 20):
            bpm_changed = True
            #print("the_bpm < (last_bpm - 20)")
        else:
            bpm_changed = False

        #print("bpm_changed = ", bpm_changed)
        #print("last = ", last_bpm)
        last_bpm = the_bpm
        #print("new last = ", last_bpm)
        
        the_bpm = getBpm()

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



####################
# Global Variables #
####################

# light sensor + the interface for the Arudino
light_bool = True
white = (255,255,255) # variable to set the LED colour

try: # setup Arduino via usb
    serial = serial.Serial('/dev/ttyACM0', 9600)
except:
    pass

# music queue for the MusicThread
q = Queue(maxsize=1)

# bpm data
the_bpm = 60
last_bpm = 60
hat = SenseHat()
bpm_changed = False
song_paused = False

# arrays for loading songs dynamically
songs_slow = []
songs_90_120 = []
songs_120_140 = []
songs_140_160 = []
songs_160_180 = []
songs_fast = []

# setup worker threads
songThread = threading.Thread(target=songWorker)
dataThread = threading.Thread(target=dataWorker)
bpmThread = threading.Thread(target=bpmWorker)
lightThread = threading.Thread(target=lightWorker)



########################
# Main Application
########################

# import Songs into arrays from disk
importSongs()

dataThread.start()
songThread.start()
bpmThread.start()
lightThread.start()