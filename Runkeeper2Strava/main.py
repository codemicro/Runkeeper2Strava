import os
import shutil
import sys
import time
import webbrowser
import zipfile

import easygui
import gpxpy
import requests
from tqdm import tqdm

import webserver

print("Runkeeper2Strava version 0.1.0b\n")

PORT = 8556

if "R2S_STRAVA_CLIENT_ID" not in os.environ:
    sys.exit("Error: Strava client ID not in environment variables")

if "R2S_STRAVA_CLIENT_SECRET" not in os.environ:
    sys.exit("Error: Strava client secret not in environment variables")

STRAVA_CLIENT_ID = os.environ["R2S_STRAVA_CLIENT_ID"]
STRAVA_CLIENT_SECRET = os.environ["R2S_STRAVA_CLIENT_SECRET"]

API_ADDR = "https://www.strava.com/api/v3"
OAUTH_ADDR = f"http://www.strava.com/oauth/authorize?client_id={STRAVA_CLIENT_ID}&response_type=code&redirect_uri=http://localhost:8556/exchange_token&scope=activity:write"

# oAuth time!
print("When prompted, please sign in with Strava and authorise the app")
time.sleep(0.5)
print("Opening web browser...")
webbrowser.open_new_tab(OAUTH_ADDR)

resp = webserver.get_auth(PORT)

if "error" in resp:
    if resp["error"] == "access_denied":
        sys.exit("Error: You need to allow access to Strava for the app to work")
elif "activity:write" not in resp["scope"]:
    sys.exit("Error: activity:write permission missing")

print("Code received, obtaining access token...")

token_params = {
    "client_id": STRAVA_CLIENT_ID,
    "client_secret": STRAVA_CLIENT_SECRET,
    "code": resp["code"],
    "grant_type":"authorization_code"
}

r = requests.post(f"{API_ADDR}/oauth/token", params=token_params)
if r.status_code == 200:
    r_json = r.json()
    ATHLETE_INFO = r_json["athlete"]
    STRAVA_ACCESS_CODE = r_json["access_token"]
else:
    sys.exit(f"Error: unable to obtain access token, HTTP {r.status_code}.")

print("\nWelcome", ATHLETE_INFO["firstname"], ATHLETE_INFO["lastname"] + "!")

print("Please select your Runkeeper activity export file.")
time.sleep(1)

runkeeper_activity_export_path = easygui.fileopenbox(msg="Please select your Runkeeper activity export",
                                                     title="Select Runkeeper activity export", default="*.zip")

if runkeeper_activity_export_path is None:
    sys.exit("Error: No export selected")

if not zipfile.is_zipfile(runkeeper_activity_export_path):
    sys.exit("Error: Supplied file is not a valid ZIP file")

temp_dir = os.path.expandvars("%temp%/Runkeeper2Strava/")
if not os.path.exists(temp_dir):
    os.makedirs(temp_dir)

print("Extracting ZIP file...")

with zipfile.ZipFile(runkeeper_activity_export_path) as zf:
    zf.extractall(path=temp_dir)

print("Discovering all GPX files...")

gpx_files = []

for file in os.listdir(temp_dir):
    if file.lower().endswith(".gpx"):
        gpx_files.append(os.path.join(temp_dir, file))

continue_flag = input(f"Found {len(gpx_files)} files to upload. This will take about "
                      f"{int((len(gpx_files)*10)/60)} minutes. Continue? (Y/n) ")

if continue_flag.lower() not in ["", "y"]:
    sys.exit("Error: user abort")

print("Beginning upload")

for i, file in tqdm(enumerate(gpx_files), total=len(gpx_files)):

    gpxp = gpxpy.parse(open(file))

    gpx_activity = gpxp.tracks[0].name.lower().split(" ")[0]

    known_activities = {
        "cycling": "ride",
        "walking": "walk",
        "running": "run"
    }

    if gpx_activity not in known_activities:
        sys.exit(f"Error: unknown activity: {gpx_activity}")

    upload_params = {
        "name": file.split(os.path.sep)[-1].split(".")[0],
        "description": "Uploaded by R2S",
        "trainer": False,
        "commute": False,
        "data_type": "gpx",
        "external_id": f"uploaded_{i}",
        "activity_type": known_activities[gpx_activity]
    }

    files = {"file": open(file, "rb")}

    r = requests.post(f"{API_ADDR}/uploads", data=upload_params, files=files,
                      headers={"Authorization": f"Bearer {STRAVA_ACCESS_CODE}"})

    resp_json = r.json()

    if r.status_code == 400:
        if "duplicate" not in resp_json["error"]:
            print(resp_json)
            sys.exit(f"Error: Upload failed. HTTP {r.status_code} returned.")
    elif r.status_code != 201:
        print(resp_json)
        sys.exit(f"Error: Upload failed. HTTP {r.status_code} returned.")

    time.sleep(10)  # ratelimit :(

print("\nCleaning up...")

for filename in os.listdir(temp_dir):
    file_path = os.path.join(temp_dir, filename)
    if os.path.isfile(file_path) or os.path.islink(file_path):
        os.unlink(file_path)
    elif os.path.isdir(file_path):
        shutil.rmtree(file_path)

print("\nDone!")
