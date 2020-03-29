# COVID-19-FL
Pulls COVID-19 / Coronavirus case data from the Florida Department of Health and stores it to a MongoDb instance.

Check out a working dashboard [here](https://charts.mongodb.com/charts-project-0-gegka/public/dashboards/fbd7f26c-f393-4155-b8f1-6119e72ed843).

Currently publishing embedded chart data at [https://www.covid19florida.info/](https://www.covid19florida.info/)

![Screenshot](images/screenshot.png "Screenshot")

# Installation

The following instructions are for Windows 10. 

Clone this repository:

```git clone https://github.com/mariuspopovici/COVID-19-FL.git```

Switch directory to the ```COVID-19-FL``` folder.

```
cd COVID-19-FL
```

## Prerequisites

## Virtualenv

Install **virtualenv**:
``` 
pip install virtualenv
```

Create a new virtual environment:
```
virtualenv env
```

Activate the virtual environment:
```
.\env\Scripts\activate
```

## Install Packages
```
pip install -r requirements.txt
```

## Set Up MongoDB

You can download and install MongoDB locally or set up a cloud instance of MongoDB Atlas. See this [video](https://www.youtube.com/watch?v=_d8CBOtadRA) for instructions.

Also view this tutorial [here](https://youtu.be/VQnmcBnguPY).

Create a new database and two collections: *florida* and *other_stats*.
Get the cluster URL and use it to create the configuration file below.

## Configure

Edit *sampleconfig.json* and save it as *config.json* in the project folder.

```
{
  "mongodb": {
    "url": "mongodb+srv://<enter_your_mongodb_URL_here>",
    "database": "<database_name>"
  },
  "other": {
    "data_url": "http://www.floridahealth.gov/diseases-and-conditions/COVID-19/",
    "dashboard_url": "<analytics_dasboard_url>"
  },
  "smtp": {
    "user": "<your_email_address>",
    "password": "<your_email_password>",
    "email_from": "<from_email_address>",
    "email_to": "<to_email_address>"
  },
  "api": {
    "url": "https://services1.arcgis.com/CY1LXxl9zlJeBuRZ/ArcGIS/rest/services/Florida_COVID19_Case_Line_Data/FeatureServer/0/query",
    "daily_url": "https://covidtracking.com/api/states/daily"
  }
}
```
Alternatively, you can define these configuration settings as environment variables:
```
DATABASE_URL
DATABASE_NAME
DASHBOARD_URL
SMTP_USER
SMTP_PASSWORD
EMAIL_FROM
EMAIL_TO
API_URL
DAILY_STATS_API_URL
```

## Run

Execute the following command to pull the latest data and store new cases in our MongoDB instance.

```
python cv-api.py
```

## Credits

* [Florida Health](https://floridahealthcovid19.gov/) for collecting detailed data and making it publicly available.
* The [Covid Tracking Project](https://covidtracking.com/) for providing the API for daily test counts.

## API

Case line data can be obtained from [here](https://services1.arcgis.com/CY1LXxl9zlJeBuRZ/ArcGIS/rest/services/Florida_COVID19_Case_Line_Data/FeatureServer/0).
