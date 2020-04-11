from pymongo import MongoClient
from os import path, environ
from datetime import datetime, date, timedelta
import json
import pandas as pd

class CoronavirusStats():
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
        today = datetime.today() - timedelta(days=1)
        self.data = self.read_mongo("florida", {"date_added": {"$lt": today}})

    # Convert MongoDB cursor to Pandas dataframe
    def read_mongo(self, collection, query={}, no_id=True):
        """ Read from Mongo and Store into DataFrame """

        # Make a query to the specific DB and Collection
        cursor = self.db[collection].find(query)

        # Expand the cursor and construct the DataFrame
        df =  pd.DataFrame(list(cursor))

        # Delete the _id
        if no_id:
            del df['_id']

        return df

    # get case count cumulative sum by date
    def cum_sum_by_county(self, counties):
        count_by_date_county = self.data.set_index(['county', 'date_added']).groupby(level=[0,1]).case_number.count()
        data = []
        county_info = self.get_county_info()
        for county in counties:
            population = county_info[county]["population"]
            cum_sum = count_by_date_county[county].cumsum().to_dict()
            for date, count in cum_sum.items():
                data.append({
                    "county": county,
                    "date": date,
                    "count": count,
                    "normalized_count": round(count / (population / 1000), 2)
                })
        
        return data

    def get_top_five_counties(self):
        largest_five = self.data.groupby(['county'])['case_number'].count().nlargest(5)
        return largest_five.to_dict().keys()

    def get_county_info(self):
        counties_file = open('./datasets/json/florida_counties.json')
        counties = json.load(counties_file)
        counties_dict = {}
        for county in counties:
            counties_dict[county["county"]] = {
                "name": county["county"],
                "location": county["location"],
                "population": county["population"]
            }

        return counties_dict

    def push_stats(self, data):
        
        # rebuild data
        self.db.top_five_counties.delete_many({})

        try:
            self.db.top_five_counties.insert_many(data)    
        except Exception as e:
            print(str(e))

stats = CoronavirusStats()
data = stats.cum_sum_by_county(stats.get_top_five_counties())
stats.push_stats(data)








