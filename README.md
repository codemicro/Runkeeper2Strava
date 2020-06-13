# Runkeeper2Strava

A tool to migrate all your Runkeeper activities to Strava.

### How does it work?

Runkeeper2Strava (R2S) works by uploading GPX files generated by Runkeeper's activity export option to Strava using its
v3 API.

### Requirements

* Python 3.6+ ([how to install](https://realpython.com/installing-python/))
* `pipenv` installed (see [pypa/pipenv](https://github.com/pypa/pipenv#installation))

### Setup

#### Downloading your Runkeeper data

* Navigate to [https://runkeeper.com/exportData](https://runkeeper.com/exportData).
* Sign into your Runkeeper account.
* Under "export activity data", choose the date range to export your activities from.
* Press "export data" and wait for a moment or two.
* Reload the page and download your data, making note of where you saved it.

#### Creating a Strava API app

* Navigate to [https://www.strava.com/settings/api](https://www.strava.com/settings/api).
* Sign into your Strava account.
* Set the application name to something along the lines of "Runkeeper Importer".
  * Trying to put the word "Strava" in the application name will cause an error.
* Set the category to "data importer".
* Put [https://www.example.com](https://www.example.com) as the website.
* Set "authorization callback domain" to `localhost:8556`.
* Check the box and press "create".
* Upload an image and continue.
* Make a note of your client ID and client secret - you'll need these to run the importer.

#### Setting up this importer

* Clone or otherwise download this repository to your local computer.
* Run `pipenv sync` in the base directory of this repo.
* While that's running, copy `.env.example` to `.env` and replace `<your client id>` with your Strava client ID and 
`<your client secret>` with your Strava client secret.

### Running the importer

* Run `pipenv run app` in the base directory of this repo.
* Follow the on screen instructions.
* To stop the importer at any time, hit CTRL+C.

### Limitations

Due to ratelimits on the Strava API, only 1 activity can be uploaded every 10 seconds. In addition to that, only 1000 
activities can be uploaded in one day, again due to ratelimits.

As a result, only importing less than 1000 activities is supported. If you want to import more than 1000 activities into
 Strava, you should extract the Runkeeper export and batch the GPX files in groups of 1000, with each group being in
 its own ZIP file. You do not need to include the CSV files with these.
 
Currently only cycling, running and walking activities can be processed. If an activity is found that is not of one of 
these types, it will be skipped. If you'd like more activity types to be added, open an issue.

*(Alternatively, you can add activity types by mapping the name used in Runkeeper's GPX files to the name used by Strava. 
Strava's names can be found [here](https://developers.strava.com/docs/uploads/#how-to-upload-an-activity), and the 
names used by Runkeeper can be found in the name section of the track name in any GPX file. The Runkeeper value to name 
can then be mapped into the dictionary named `known_activities` in `main.py`. Feel free to submit a pull request if you 
do this.)*

### FAQs

#### Why did it say a file is corrupt or unreadable?

During testing, it's been found that some GPX files that Runkeeper exports are malformed. It's thought that this is a 
result of the activity being edited after it occurred using Runkeeper's website. If this is the case, you can fix your 
GPX file by doing the following:

* Stop the program using CTRL+C.
* Restart the program and sign into Strava again.
* Select the same Runkeeer export as before.
* **Decline** to continue where you left off when prompted.
* When you're told an estimation of how long it will take and asked if you want to continue, do not press or type 
anything.
* Insead, open the errored file in a text editor (the file path is shown by the program when the error occurs).
* Search for and remove extra `</trkseg>` tags found in the middle of the file.
* Save the file.
* Return to the program and answer `y` to the prompt and continue as normal.

#### Is this secure?

Yep! Access tokens for your Strava account never leave your computer and are not stored in any way.


### Issues and contributing

Got a problem? Open an issue using the issues tab.

Pull requests are accepted if you're so inclined.

___

Lockdown productivity for the win - importer initially written on 10/06/2020
