import csv
import json
import re
from pymongo import MongoClient
from os import path, environ
from datetime import datetime
import smtplib
import requests
import math
import time

class Coronavirus():
    # constructor
    def __init__(self):
        # read config, if config.json file is not available then try OS environment vars
        if path.exists('config.json'):
            with open('config.json') as config_file:
                self.config = json.load(config_file)
        else:
            self.config = {
                "mongodb": {
                    "url": environ.get("DATABASE_URL"),
                    "database": environ.get("DATABASE_NAME")
                },
                "other": {
                    "dashboard_url": environ.get("DASHBOARD_URL")
                },
                "smtp": {
                    "user": environ.get("SMTP_USER"),
                    "password": environ.get("SMTP_PASSWORD"),
                    "email_from": environ.get("EMAIL_FROM"),
                    "email_to": environ.get("EMAIL_TO"),
                },
                "api": {
                    "url": environ.get("API_URL"),
                    "daily_url": environ.get("DAILY_STATS_API_URL"),
                }
            }

        # connect to MongoDB/Atlas
        self.client = MongoClient(self.config["mongodb"]["url"])
        self.db = self.client.get_database(self.config["mongodb"]["database"])
        self.api_url = self.config["api"]["url"]
        self.api_daily_url = self.config["api"]["daily_url"]

    # scrape source data from FLDOH
    def get_case_data(self):
        locations = self.get_county_locations()
        try:
            request_params = {
                "where": "1>0",
                "returnCountOnly": "true",
                "f": "pjson"                
            }    

            response = requests.get(self.api_url, params=request_params)
            data = response.json()
 
            if data["count"] == 0:
                print("No data.")
                return {
                    "success": False,
                    "message": "No data"
                }

            records_per_page = 2000
            pages = math.ceil(data["count"] / records_per_page)
            page_range = range(pages)
            offset = 0
            dataset = []
            
            for page_no in page_range:
                request_params = {
                    "outFields": "Case_, ObjectId, County, Age, Gender, Travel_Related, Origin, EDVisit, Hospitalized, Died, Contact, EventDate",
                    "where": "Case_ not like 'NA%'",
                    "returnCountOnly": "false",
                    "resultOffset": offset,
                    "resultRecordCount": records_per_page,
                    "f": "pjson",
                    "orderByFields": "Case_"
                }    
                print(f"Requesting page {page_no + 1} of {pages}")
                response = requests.get(self.api_url, params=request_params)
                offset = (page_no + 1) * records_per_page
                data = response.json()
                dataset = dataset + data["features"]
                
                # wait loop
                num_seconds = 5
                print("Next call in: ", end = '')
                for countdown in reversed(range(num_seconds + 1)):
                    if countdown > 0:
                        print(countdown, end = ' ')
                        time.sleep(1)
                    else:
                        print('Done!')

            # build a collection of cases (dictionaries)
            row_num = 0
            cases = []
            for row in dataset:
                attributes = row["attributes"]
                travel_string = attributes["Origin"]
                travel_list = [ item.strip().title() if len(item.strip()) > 2 else item.strip() for item in travel_string.split(";") ] if travel_string != "NA" else None
                case = {
                    "case_number": attributes["ObjectId"],
                    "county": attributes["County"],
                    "age": int(attributes["Age"]) if (attributes["Age"] != "NA" and attributes["Age"] != None) else None,
                    "sex": attributes["Gender"],
                    "travel": attributes["Travel_related"],
                    "travel_detail": travel_list,
                    "contact_with_confirmed_case": attributes["Contact"].title() if attributes["Contact"] != "NA" else "No",
                    "date_added": datetime.fromtimestamp(attributes["Case_"] / 1000.0).replace(hour=0, minute=0, second=0, microsecond=0), 
                    "deceased": attributes["Died"] if attributes["Died"] != "NA" else "No",
                    "location": locations.get(attributes["County"], None),
                    "hospitalized": attributes["Hospitalized"].title() if attributes["Hospitalized"] != "NA" else None,
                    "ed_visit": attributes["EDvisit"].title() if attributes["EDvisit"] != "NA" else None,
                }
                cases.append(case)

            # store to database
            store_result = self.store_data(cases, "florida")
            

        except Exception as e:
            print(str(e))
            print(attributes)
            return {
                "success": False,
                "message": str(e)
            }
        
        return {
            "success": True,
            "message": f"{store_result['new_records']} new cases added",
            "new_cases": store_result['new_records']
        }
    
    def get_other_data(self):
        try:
            request_params = {
                "state": "FL"                
            }    

            response = requests.get(self.api_daily_url, params=request_params)
            data = response.json()

            # build a collection of records (dictionaries)
            row_num = 0
            stats = [] 
            for item in data:
                prev_deaths = item["death"] - item["deathIncrease"] if ("death" in item and item["death"] != None and item["deathIncrease"] != None) else 0
                prev_hospitalized = item["hospitalized"] - item["hospitalizedIncrease"] if ("hospitalized" in item and item["hospitalized"] != None and "hospitalizedIncrease" in item and item["hospitalizedIncrease"] != None) else 0
                record = {
                    "date": datetime.strptime(str(item["date"]), '%Y%m%d'),
                    "tests": item["totalTestResults"] if "totalTestResults" in item else 0,
                    "new_tests": item["totalTestResultsIncrease"],
                    "deaths": item["death"] if "death" in item else 0,
                    "new_deaths": item["deathIncrease"],
                    "deaths_growth": (item["death"] / prev_deaths) if prev_deaths > 0 else 0,
                    "hospitalized": item["hospitalized"] if "hospitalized" in item else 0,
                    "new_hospitalized": item["hospitalizedIncrease"],
                    "hospitalized_growth": (item["hospitalized"] / prev_hospitalized) if prev_hospitalized > 0 else 0
                }
                stats.append(record)

            # store to database
            store_result = self.store_data(stats, "other_stats")

        except Exception as e:
            print(str(e))
            return {
                "success": False,
                "message": str(e)
            }
        
        return {
            "success": True,
            "message": f"{store_result['new_records']} new records added"
        }

    # store records to Atlas/MongoDB instance
    def store_data(self, records, collection):        
        current_count = self.db.get_collection(collection).estimated_document_count()
        new_records = len(records) - current_count
        # remove all records
        self.db.get_collection(collection).delete_many({})
        
        print(f"Adding {new_records} new records to collection {collection}.")

        try:
            if len(records) > 0:
                print("Adding records to database.")
                self.db.get_collection(collection).insert_many(records)    
        except Exception as e:
            print(str(e))
            return {
                "success": False,
                "message": str(e)
            }
        
        return {
            "success": True,
            "message": "",
            "new_records": new_records
        }
    
    # sends email notification with the specified message and analytics dashboard URL
    def send_mail(self, message):
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.ehlo()
        server.starttls()
        server.ehlo()

        server.login(self.config["smtp"]["user"], self.config["smtp"]["password"])

        subject = 'Florida COVID-19 Status'
        dashboard_url = self.config["other"]["dashboard_url"]
        body = f"{message}\nCheck out the analytics dashboard: {dashboard_url}"

        msg = f"Subject: {subject}\n\n{body}"

        server.sendmail(
            self.config["smtp"]["email_from"],
            self.config["smtp"]["email_to"],
            msg
        )

        print('Sent email notification')
        server.quit()

    def get_county_locations(self):
        counties_file = open('./datasets/json/florida_counties.json')
        counties = json.load(counties_file)
        locations_hash = {}
        for county in counties:
            locations_hash[county["county"]] = county["location"]

        return locations_hash
        
bot = Coronavirus()
case_result = bot.get_case_data()

if case_result["success"] and case_result["new_cases"] > 0:
    other_result = bot.get_other_data()
    bot.send_mail(case_result['message'])

