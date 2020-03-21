import csv
import json
import re
from pymongo import MongoClient
from os import path, environ
from datetime import datetime
import smtplib

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
                }
            }

        # connect to MongoDB/Atlas
        self.client = MongoClient(self.config["mongodb"]["url"])
        self.db = self.client.get_database(self.config["mongodb"]["database"])

    # scrape source data from FLDOH
    def get_data(self, csv_file):
        locations = self.get_county_locations()
        try:
            file = open(csv_file)
            csv_reader = csv.reader(file, delimiter=',')
            # build a collection of cases (dictionaries)
            row_num = 0
            cases = []
            for row in csv_reader:
                case = {
                    "case_number": int(re.sub("[^0-9]", "", row[0])),
                    "county": row[1],
                    "age": int(re.sub("[^0-9]", "", row[2])) if row[2].strip() else 'Unknown',
                    "sex": row[3],
                    "travel": row[4],
                    "travel_detail": row[5],
                    "contact_with_confirmed_case": row[6] if row[6] else 'Unknown',
                    "jurisdiction": row[7],
                    "date_added": datetime.strptime(row[8], '%m/%d/%y'),
                    "deceased": row[9],
                    "location": locations.get(row[1], None)
                }
                cases.append(case)

            # store to database
            store_result = self.store_data(cases)
            self.client.close()

        except Exception as e:
            print(str(e))
            return {
                "success": False,
                "message": str(e)
            }
        
        return {
            "success": True,
            "message": f"{store_result['new_cases']} new cases added"
        }
    
    # store case data to Atlas/MongoDB instance
    def store_data(self, cases):        
        current_count = self.db.florida.estimated_document_count()
        new_cases = len(cases) - current_count
        # remove all cases
        self.db.florida.remove({})
        
        print(f"Adding {new_cases} new cases.")

        try:
            if len(cases) > 0:
                print("Adding cases to database.")
                self.db.florida.insert_many(cases)    
        except Exception as e:
            print(str(e))
            return {
                "success": False,
                "message": str(e)
            }
        
        return {
            "success": True,
            "message": "",
            "new_cases": new_cases
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
result = bot.get_data("./datasets/csv/cases.csv")
bot.send_mail(result['message'])
