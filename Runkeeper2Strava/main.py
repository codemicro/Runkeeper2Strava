print("Runkeeper2Strava version 0.1.0b\n")

import csv
import datetime
import json
import os
import shutil
import sys
import time
import webbrowser
import zipfile

import easygui
from loguru import logger
import gpxpy
import requests
from tqdm import tqdm

import helpers
import webserver

PORT = 8556

temp_dir = os.path.join(os.path.expandvars("%temp%"), "Runkeeper2Strava")
logger.add(os.path.join(temp_dir, "error.log"), level="ERROR")

if "R2S_STRAVA_CLIENT_ID" not in os.environ:
    logger.error("Strava client ID not in environment variables")
    sys.exit()

if "R2S_STRAVA_CLIENT_SECRET" not in os.environ:
    logger.error("Strava client secret not in environment variables")
    sys.exit()

STRAVA_CLIENT_ID = os.environ["R2S_STRAVA_CLIENT_ID"]
STRAVA_CLIENT_SECRET = os.environ["R2S_STRAVA_CLIENT_SECRET"]

API_ADDR = "https://www.strava.com/api/v3"
OAUTH_ADDR = f"http://www.strava.com/oauth/authorize?client_id={STRAVA_CLIENT_ID}&response_type=code&redirect_uri=http://localhost:8556/exchange_token&scope=activity:write"


def cleanTempDir(directory):
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        if os.path.isfile(file_path) or os.path.islink(file_path):
            try:
                os.unlink(file_path)
            except PermissionError:
                # Cannot delete the file because it's currently in use, in which case just skip it
                pass
        elif os.path.isdir(file_path):
            shutil.rmtree(file_path)


# oAuth time!
print("When prompted, please sign in with Strava and authorise the app")
time.sleep(0.5)
print("Opening web browser...")
webbrowser.open_new_tab(OAUTH_ADDR)

resp = webserver.get_auth(PORT)

if "error" in resp:
    if resp["error"] == "access_denied":
        logger.error("You need to allow access to Strava for the app to work")
        sys.exit()
elif "activity:write" not in resp["scope"]:
    logger.error("activity:write permission missing")
    sys.exit()

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
    logger.error(f"unable to obtain access token, HTTP {r.status_code}.")
    sys.exit()

print("\nWelcome", ATHLETE_INFO["firstname"], ATHLETE_INFO["lastname"] + "!")

print("Please select your Runkeeper activity export file.")
time.sleep(1)

runkeeper_activity_export_path = easygui.fileopenbox(msg="Please select your Runkeeper activity export",
                                                     title="Select Runkeeper activity export", default="*.zip")

if runkeeper_activity_export_path is None:
    logger.error("No export selected")
    sys.exit()

if not zipfile.is_zipfile(runkeeper_activity_export_path):
    logger.error("Supplied file is not a valid ZIP file")
    sys.exit()

export_dir = os.path.join(temp_dir, "export")
if not os.path.exists(export_dir):
    os.makedirs(export_dir)

progress_file = os.path.join(temp_dir, "progress.json")


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
        logger.error(f"Unable to extract ZIP file.\n{e}")
        sys.exit()




print("Discovering all activities...")

with open(os.path.join(export_dir, "cardioActivities.csv")) as f:
    csv_contents = f.read().split("\n")[1:]

activity_reader = csv.reader(csv_contents)

activities = [a for a in activity_reader][resume_from:]


if len(activities) == 0:
    logger.error("no activities found in the specified file")
    sys.exit()

if len(activities) > 1000:
    logger.error(f"only a maximum of 1000 activities can be uploaded at once. The file you specified contained "
             f"{len(activities)} activities.")
    sys.exit()

continue_flag = input(f"Found {len(activities)} files to upload. This will take about "
                      f"{int((len(activities)*10)/60)} minutes. Continue? (Y/n) ")

if continue_flag.lower() not in ["", "y"]:
    cleanTempDir(activities)
    logger.error("user abort")
    sys.exit()

print("Beginning upload")

for i, row in tqdm(enumerate(activities), total=len(activities)):  # enumerate doesn't give a length

    if row[-1] == "":
        # No GPX file avail

        date_and_time = helpers.time_to_iso(row[1])
        type = helpers.convert_activity_type(row[2])
        distance = helpers.miles_to_meters(float(row[4]))
        duration = helpers.duration_to_seconds(row[5])

        activity_name = ("Afternoon" if datetime.datetime.fromisoformat(date_and_time).hour > 11 else "Morning") + " " \
                        + type

        request_args = {
            "name": activity_name,
            "type": type,
            "start_date_local": date_and_time,
            "elapsed_time": duration,
            "distance": distance,
            "trainer": False,
            "commute": False,
            "description": "Uploaded by R2S - https://www.github.com/codemicro/Runkeeper2Strava",
        }

        r = requests.post(f"{API_ADDR}/activities", data=request_args,
                          headers={"Authorization": f"Bearer {STRAVA_ACCESS_CODE}"})

    else:
        # There is a GPX file to be read from

        file = os.path.join(export_dir, row[-1])

        try:
            gpxp = gpxpy.parse(open(file))
        except gpxpy.gpx.GPXXMLSyntaxException as e:
            print(f"\nError: {file} is corrupt or unreadable. Skipping this file.")
            continue

        gpx_activity = gpxp.tracks[0].name.lower().split(" ")[0]

        if gpx_activity not in helpers.known_activities:
            print(f"Error: unknown activity: {gpx_activity} - skipping {file}")
            continue

        upload_params = {
            "name": ("Afternoon" if int(file.split(os.path.sep)[-1].split(".")[0][11:13]) > 11 else "Morning") + " " +
                    helpers.convert_activity_type(gpx_activity),
            "description": "Uploaded by R2S - https://www.github.com/codemicro/Runkeeper2Strava",
            "trainer": False,
            "commute": False,
            "data_type": "gpx",
            "external_id": f"uploaded_{i}",
            "activity_type": helpers.convert_activity_type(gpx_activity)
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
            logger.error(f"Upload failed. HTTP {r.status_code} returned.")
            sys.exit()
    elif r.status_code != 201:
        print(resp_json)
        logger.error(f"Upload failed. HTTP {r.status_code} returned.")
        sys.exit()

    record_progress(resume_from + i)

    time.sleep(10)  # ratelimit :(

print("\nCleaning up...")

cleanTempDir(export_dir)

print("\nDone!")
