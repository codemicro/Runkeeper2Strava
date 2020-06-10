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

### Issues and contributing

Got a problem? Open an issue using the issues tab.

Pull requests are accepted if you're so inclined.

___

Lockdown productivity for the win - importer initially written on 10/06/2020
