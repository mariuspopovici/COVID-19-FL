# COVID-19-FL
Pulls COVID-19 / Coronavirus case data from the Florida Department of Health and stores it to a MongoDb instance.

Check out a working dashboard [here](https://charts.mongodb.com/charts-project-0-gegka/public/dashboards/fbd7f26c-f393-4155-b8f1-6119e72ed843).

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

You need Python3 installed on your machine. You also need the Python package management tool **pip** installed. This should come with Python3 and be installed by default.

## ChromeDriver
Download and install the latest stable release of [ChromeDriver](https://chromedriver.chromium.org/) for your platform.

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
pip install selenium
pip install dnspython
pip install pymongo
```

## Set Up MongoDB

You can download and install MongoDB locally or set up a cloud instance of MongoDB Atlas. See this [video](https://www.youtube.com/watch?v=_d8CBOtadRA) for instructions.

Also view this tutorial [here](https://youtu.be/VQnmcBnguPY).

Create a new database and a collection called *florida*.
Get the cluster URL and use it to create the configuration file below.

## Configure

Edit *sampleconfig.json* and save it as *config.json* in the project folder.

```
{
  "mongodb": {
    "url": "mongodb+srv://your_mongodb_url",
    "database": "your_database_name"
  },
  "other": {
    "chromedriver_binary": "./bin/chromedriver.exe",
    "data_url": "http://www.floridahealth.gov/diseases-and-conditions/COVID-19/"
  }
}
```

## Run

Execute the following command to pull the latest data and store new cases in our MongoDB instance.

```
python cv.py
```