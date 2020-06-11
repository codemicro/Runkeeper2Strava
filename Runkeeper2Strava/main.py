import json
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

export_dir = os.path.join(os.path.expandvars("%temp%"), "Runkeeper2Strava", "export")
if not os.path.exists(export_dir):
    os.makedirs(export_dir)

progress_file = os.path.join(os.path.expandvars("%temp%"), "Runkeeper2Strava", "progress.json")


def record_progress(num:int):
    num = int(num)

    if os.path.exists(progress_file):
        cur_prog = json.load(open(progress_file))

        cur_prog[runkeeper_activity_export_path] = num

        json.dump(cur_prog, open(progress_file, "w"))

    else:
        json.dump({runkeeper_activity_export_path: num}, open(progress_file, "w"))


def get_progress(fname:str):
    if os.path.exists(progress_file):
        saved_prog = json.load(open(progress_file))
        if fname in saved_prog:
            return int(saved_prog[fname])
        else:
            return 0
    else:
        return 0


current_progress = get_progress(runkeeper_activity_export_path)
if current_progress != 0:
    choice = input("It looks like you already started uploading activities from this export. Would you like to continue "
                   "from where you left off? (Y/n) ")

    if choice.lower() not in ["y", ""]:
        resume_from = 0
    else:
        resume_from = current_progress - 1  # just to make sure everything is uploaded
else:
    resume_from = 0

print("Extracting ZIP file...")

with zipfile.ZipFile(runkeeper_activity_export_path) as zf:
    try:
        zf.extractall(path=export_dir)
    except FileNotFoundError as e:
        sys.exit(f"Error: Unable to extract ZIP file.\n{e}")

print("Discovering all GPX files...")

gpx_files = []

for file in os.listdir(export_dir):
    if file.lower().endswith(".gpx"):
        gpx_files.append(os.path.join(export_dir, file))

gpx_files = gpx_files[resume_from:]

if len(gpx_files) == 0:
    sys.exit("Error: no activities found in the specified file")

if len(gpx_files) > 1000:
    sys.exit(f"Error: only a maximum of 1000 activities can be uploaded at once. The file you specified contained "
             f"{len(gpx_files)} activities.")

continue_flag = input(f"Found {len(gpx_files)} files to upload. This will take about "
                      f"{int((len(gpx_files)*10)/60)} minutes. Continue? (Y/n) ")

if continue_flag.lower() not in ["", "y"]:
    sys.exit("Error: user abort")

print("Beginning upload")

for i, file in tqdm(enumerate(gpx_files), total=len(gpx_files)):

    try:
        gpxp = gpxpy.parse(open(file))
    except gpxpy.gpx.GPXXMLSyntaxException as e:
        print(f"\nError: {file} is corrupt or unreadable. Skipping this file.")
        continue

    gpx_activity = gpxp.tracks[0].name.lower().split(" ")[0]

    known_activities = {
        "cycling": "ride",
        "walking": "walk",
        "running": "run"
    }

    if gpx_activity not in known_activities:
        print(f"Error: unknown activity: {gpx_activity} - skipping {file}")
        continue

    upload_params = {
        "name": ("Afternoon" if int(file.split(os.path.sep)[-1].split(".")[0][11:13]) > 11 else "Morning") + " " +
                known_activities[gpx_activity],
        "description": "Uploaded by R2S - https://www.github.com/codemicro/Runkeeper2Strava",
        "trainer": False,
        "commute": False,
        "data_type": "gpx",
        "external_id": f"uploaded_{i}",
        "activity_type": known_activities[gpx_activity]
    }

    gpx_file_object = open(file, "rb")

    files = {"file": gpx_file_object}

    r = requests.post(f"{API_ADDR}/uploads", data=upload_params, files=files,
                     headers={"Authorization": f"Bearer {STRAVA_ACCESS_CODE}"})

    gpx_file_object.close()

    resp_json = r.json()

    if r.status_code == 400:
        if "duplicate" not in resp_json["error"]:
            print(resp_json)
            sys.exit(f"Error: Upload failed. HTTP {r.status_code} returned.")
    elif r.status_code != 201:
        print(resp_json)
        sys.exit(f"Error: Upload failed. HTTP {r.status_code} returned.")

    record_progress(resume_from + i)

    time.sleep(10)  # ratelimit :(

print("\nCleaning up...")

for filename in os.listdir(export_dir):
    file_path = os.path.join(export_dir, filename)
    if os.path.isfile(file_path) or os.path.islink(file_path):
        try:
            os.unlink(file_path)
        except PermissionError:
            # Cannot delete the file because it's currently in use, in which case just skip it
            pass
    elif os.path.isdir(file_path):
        shutil.rmtree(file_path)

print("\nDone!")
