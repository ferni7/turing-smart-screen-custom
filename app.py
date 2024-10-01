#!/usr/bin/env python3
# A simple Python manager for "Turing Smart Screen" 3.5" IPS USB-C display
# https://github.com/mathoudebine/turing-smart-screen-python

import os
import signal
import sys
import time
import bitmath

# Import only the modules for LCD communication
from library.lcd_comm_rev_a import LcdCommRevA, Orientation
from library.lcd_comm_rev_b import LcdCommRevB
from library.lcd_simulated import LcdSimulated
from library.log import logger

import requests
from requests.packages import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Get environment variables for Opnsense API - used for Internet Upload/Download speed
OPNS_API_KEY = os.getenv('OPNS_API_KEY')
OPNS_API_SECRET = os.environ.get('OPNS_API_SECRET')
OPNS_IP_ADDR = os.environ.get('OPNS_IP_ADDR')
OPNS_URL = "https://" + OPNS_IP_ADDR + "/api/diagnostics/traffic/interface"

# Get Prom Server URL from env variable
PROM_SERVER_URL=os.environ.get('PROM_SERVER_URL')

def get_prom_metric(metricname, label):
  query = "last_over_time(" + metricname + "{" + label + "}[1h])"
  response = requests.get(f"{PROM_SERVER_URL}/api/v1/query?query={query}")
  if response.status_code==200:
    if len(response.json()['data']['result'])==1:
      metric = response.json()['data']['result'][0]['value'][1]
      metric = str(round(float(metric)))
    else:
      metric="ERR"
    return(metric)
  else:
    print(response.status_code + ": " + response.reason)

def get_prom_metric_from_query(query):
  response = requests.get(f"{PROM_SERVER_URL}/api/v1/query?query={query}")
  if response.status_code==200:
    if len(response.json()['data']['result'])==1:
      metric = response.json()['data']['result'][0]['value'][1]
    else:
      metric="ERR"
    return(metric)
  else:
    print(response.status_code + ": " + response.reason)

# Initialise some global variables for the network_speed() function
global old_downloaded_bytes
old_downloaded_bytes = 0
global old_uploaded_bytes
old_uploaded_bytes = 0
global last_time
last_time = time.time_ns()

def network_speed():
    global old_downloaded_bytes
    global old_uploaded_bytes
    global last_time

    r = requests.get(OPNS_URL,verify=False, auth=(OPNS_API_KEY, OPNS_API_SECRET))
    if r.status_code == 200:
        # For each call calculate the time difference from when it was last called, needed to calculate per second speed
        now_time = time.time_ns()
        delta_time = now_time - last_time
        last_time = now_time

        # Get the number of bytes the wan interface as uploaded/downloaded
        new_downloaded_bytes = r.json()['interfaces']['wan']['bytes received']
        new_uploaded_bytes = r.json()['interfaces']['wan']['bytes transmitted']

        # Calculate how many bytes have been uploaded/downloaded since last time this function was called
        delta_downloaded_bytes=int(new_downloaded_bytes)-old_downloaded_bytes
        delta_uploaded_bytes=int(new_uploaded_bytes)-old_uploaded_bytes

        # Update the old uploaded/downloaded byte values for next time this is called
        old_downloaded_bytes=int(new_downloaded_bytes)
        old_uploaded_bytes=int(new_uploaded_bytes)

        # Calculate the download and upload speed by dividing the delta bytes by time since last call
        download_speed=bitmath.Byte(delta_downloaded_bytes/(delta_time/1000000000))
        upload_speed=bitmath.Byte(delta_uploaded_bytes/(delta_time/1000000000))

        # return a list with the download and upload speeds
        return(download_speed.Mib.format("{value:.1f} {unit}/s"), upload_speed.Mib.format("{value:.1f} {unit}/s"))
    else:
        return(r.status_code + ": " + r.reason)

# Set your COM port e.g. COM3 for Windows, /dev/ttyACM0 for Linux, etc. or "AUTO" for auto-discovery
# COM_PORT = "/dev/ttyACM0"
# COM_PORT = "COM5"
COM_PORT = "AUTO"

# Display revision: A or B (for "flagship" version, use B) or SIMU for simulated LCD (image written in screencap.png)
# To identify your revision: https://github.com/mathoudebine/turing-smart-screen-python/wiki/Hardware-revisions
REVISION = "A"

stop = False

if __name__ == "__main__":

    def sighandler(signum, frame):
        global stop
        stop = True

    # Set the signal handlers, to send a complete frame to the LCD before exit
    signal.signal(signal.SIGINT, sighandler)
    signal.signal(signal.SIGTERM, sighandler)
    is_posix = os.name == 'posix'
    if is_posix:
        signal.signal(signal.SIGQUIT, sighandler)

    # Build your LcdComm object based on the HW revision
    lcd_comm = None
    if REVISION == "A":
        logger.info("Selected Hardware Revision A (Turing Smart Screen)")
        lcd_comm = LcdCommRevA(com_port="AUTO",
                               display_width=320,
                               display_height=480)
    elif REVISION == "B":
        print("Selected Hardware Revision B (XuanFang screen version B / flagship)")
        lcd_comm = LcdCommRevB(com_port="AUTO",
                               display_width=320,
                               display_height=480)
    elif REVISION == "SIMU":
        print("Selected Simulated LCD")
        lcd_comm = LcdSimulated(display_width=320,
                                display_height=480)
    else:
        print("ERROR: Unknown revision")
        try:
            sys.exit(0)
        except:
            os._exit(0)

    # Reset screen in case it was in an unstable state (screen is also cleared)
    lcd_comm.Reset()

    # Send initialization commands
    lcd_comm.InitializeComm()

    # Set brightness in % (warning: screen can get very hot at high brightness!)
    lcd_comm.SetBrightness(level=15)

    # Set backplate RGB LED color (for supported HW only)
    #lcd_comm.SetBackplateLedColor(led_color=(255, 255, 255))

    # Set orientation (screen starts in Portrait)
    orientation = Orientation.LANDSCAPE
    lcd_comm.SetOrientation(orientation=orientation)

    # Define background picture
    if orientation == Orientation.PORTRAIT or orientation == orientation.REVERSE_PORTRAIT:
        background = "black_portrait.png"
    else:
#        background = "res/backgrounds/example_landscape.png"
        background = "black_landscape.png"

    # Display background picture
    #lcd_comm.DisplayBitmap(background)

    font = "roboto-mono/RobotoMono-Medium.ttf"

    # Display static text
    lcd_comm.DisplayText("Temperature", 10, 10,
                         font="roboto/Roboto-Bold.ttf",
                         font_size=30,
                         font_color=(255, 0, 0),
                         background_color=(0, 0, 0))

    lcd_comm.DisplayText("Office:", 10, 50,
                         font,
                         font_size=25,
                         font_color=(255, 255, 255),
                         background_color=(0, 0, 0))

    lcd_comm.DisplayText("Lounge:", 10, 85,
                         font,
                         font_size=25,
                         font_color=(255, 255, 255),
                         background_color=(0, 0, 0))
    
    lcd_comm.DisplayText("L Room:", 10, 120,
                         font,
                         font_size=25,
                         font_color=(255, 255, 255),
                         background_color=(0, 0, 0))

    lcd_comm.DisplayText("Upstairs:", 10, 155,
                         font,
                         font_size=25,
                         font_color=(255, 255, 255),
                         background_color=(0, 0, 0))
    
    lcd_comm.DisplayText("Bedroom:", 10, 190,
                         font,
                         font_size=25,
                         font_color=(255, 255, 255),
                         background_color=(0, 0, 0))

    lcd_comm.DisplayText("Backyard:", 10, 225,
                         font,
                         font_size=25,
                         font_color=(255, 255, 255),
                         background_color=(0, 0, 0))
    
    lcd_comm.DisplayText("Garage:", 10, 260,
                         font,
                         font_size=25,
                         font_color=(255, 255, 255),
                         background_color=(0, 0, 0))

    lcd_comm.DisplayText("Power", 240, 10,
                         font="roboto/Roboto-Bold.ttf",
                         font_size=30,
                         font_color=(0, 153, 51),
                         background_color=(0, 0, 0))
    
    lcd_comm.DisplayText("PC:", 240, 50,
                         font,
                         font_size=25,
                         font_color=(255, 255, 255),
                         background_color=(0, 0, 0))

    lcd_comm.DisplayText("K PC:", 240, 85,
                         font,
                         font_size=25,
                         font_color=(255, 255, 255),
                         background_color=(0, 0, 0))
    
    lcd_comm.DisplayText("TV:", 240, 120,
                         font,
                         font_size=25,
                         font_color=(255, 255, 255),
                         background_color=(0, 0, 0))
    
    lcd_comm.DisplayText("Chia:", 240, 155,
                         font,
                         font_size=25,
                         font_color=(255, 255, 255),
                         background_color=(0, 0, 0))
    
    lcd_comm.DisplayText("Grid:", 240, 190,
                         font,
                         font_size=25,
                         font_color=(255, 0, 0),
                         background_color=(0, 0, 0))

    #lcd_comm.DisplayText("Solar:", 240, 225,
    #                     font,
    #                     font_size=25,
    #                     font_color=(255, 255, 255),
    #                     background_color=(0, 0, 0))


    # Display the current time and some progress bars as fast as possible
    while not stop:
        lcd_comm.DisplayText(get_prom_metric("thermometer_temperature_celsius","room='Office'") + "º", 150, 50,
                            font=font,
                            font_size=25,
                            font_color=(255, 255, 255),
                            background_color=(0, 0, 0))

        lcd_comm.DisplayText(get_prom_metric("thermometer_temperature_celsius","room='Lounge'") + "º", 150, 85,
                            font,
                            font_size=25,
                            font_color=(255, 255, 255),
                            background_color=(0, 0, 0))
        
        lcd_comm.DisplayText(get_prom_metric("thermometer_temperature_celsius","room='LBedroom'") + "º", 150, 120,
                            font,
                            font_size=25,
                            font_color=(255, 255, 255),
                            background_color=(0, 0, 0))
        
        lcd_comm.DisplayText(get_prom_metric("thermometer_temperature_celsius","room='Upstairs'") + "º", 150, 155,
                            font,
                            font_size=25,
                            font_color=(255, 255, 255),
                            background_color=(0, 0, 0))

        lcd_comm.DisplayText(get_prom_metric("thermometer_temperature_celsius","room='Bedroom'") + "º", 150, 190,
                            font,
                            font_size=25,
                            font_color=(255, 255, 255),
                            background_color=(0, 0, 0))

        lcd_comm.DisplayText(get_prom_metric("thermometer_temperature_celsius","room='Backyard'") + "º", 150, 225,
                            font,
                            font_size=25,
                            font_color=(255, 255, 255),
                            background_color=(0, 0, 0))
        
        lcd_comm.DisplayText(get_prom_metric("thermometer_temperature_celsius","room='Garage'") + "º", 150, 260,
                            font,
                            font_size=25,
                            font_color=(255, 255, 255),
                            background_color=(0, 0, 0))

        computer_watts=get_prom_metric("tasmota_energy_power_active_watts","job='Computer'") + "W"
        lcd_comm.DisplayText(f'{computer_watts:>5}', 405, 50,
                            font,
                            font_size=25,
                            font_color=(255, 255, 255),
                            background_color=(0, 0, 0))

        k_computer_watts=get_prom_metric("tasmota_energy_power_active_watts","job='K Computer'") + "W"
        lcd_comm.DisplayText(f'{k_computer_watts:>5}', 405, 85,
                            font,
                            font_size=25,
                            font_color=(255, 255, 255),
                            background_color=(0, 0, 0))
        
        tv_watts=get_prom_metric("tasmota_energy_power_active_watts","job='TV'") + "W"
        lcd_comm.DisplayText(f'{tv_watts:>5}', 405, 120,
                            font,
                            font_size=25,
                            font_color=(255, 255, 255),
                            background_color=(0, 0, 0))

        chia_watts=get_prom_metric("tasmota_energy_power_active_watts","job='Chia'") + "W"
        lcd_comm.DisplayText(f'{chia_watts:>5}', 405, 155,
                            font,
                            font_size=25,
                            font_color=(255, 255, 255),
                            background_color=(0, 0, 0))

        #purchased_energy=round(float(get_prom_metric_from_query("solaredge_api_purchased_energy/1000")),1)
        value = get_prom_metric_from_query("solaredge_api_purchased_energy/1000")
        try:
            purchased_energy = round(float(value), 1)
        except ValueError:
            purchased_energy = 0  # or handle the error appropriately
        lcd_comm.DisplayText(f'{purchased_energy:>5}kW', 375, 190,
                            font,
                            font_size=25,
                            font_color=(255, 0, 0),
                            background_color=(0, 0, 0))

        current_solar_power=round(float(get_prom_metric_from_query("AC_Power*(10^AC_Power_SF)/1000")),1)
        lcd_comm.DisplayProgressBar(240, 225,
                                    width=140, height=30,
                                    min_value=0, max_value=5, value=current_solar_power,
                                    bar_color=(80,200,120), bar_outline=True,
                                    background_color=(0, 0, 0))
        
        lcd_comm.DisplayText(f'{current_solar_power:>4}kW', 390, 225,
                            font,
                            font_size=25,
                            font_color=(80,200,120),
                            background_color=(0, 0, 0))

        speed = network_speed()
        lcd_comm.DisplayText(f'DL: {speed[0]:>12}', 240, 260,
                            font,
                            font_size=25,
                            font_color=(113, 163, 245),
                            background_color=(0, 0, 0))
        lcd_comm.DisplayText(f'UL: {speed[1]:>12}', 240, 290,
                            font,
                            font_size=25,
                            font_color=(113, 163, 245),
                            background_color=(0, 0, 0))

        time.sleep(5)

    # Close serial connection at exit
    lcd_comm.closeSerial()
