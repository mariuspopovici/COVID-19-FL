from pymongo import MongoClient
from os import path, environ
from datetime import date, timedelta
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
        self.data = self.read_mongo("florida")

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
    def cum_sum(self):
        count_by_date = self.data.groupby("date_added")["case_number"].count()
        return count_by_date.cumsum()

    # calculate daily growth of case count
    def cum_growth(self, tail = None):
        pct_growth_change = self.cum_sum().pct_change()
        growth_rate = pct_growth_change.apply(lambda x: x + 1)

        if tail:
            return growth_rate.tail(tail)
        else:
            return growth_rate


    # simulate case growth
    def growth_sim(self, count, growth_factor):
        cum_sum = self.cum_sum()        
        prediction_dict = cum_sum.to_dict()
        last_date = list(prediction_dict.keys())[-1]
        last_count = prediction_dict[last_date]
        predict_range = range(count)
        for i in predict_range:
            new_date = last_date + timedelta(days=1)
            predicted_count = last_count * growth_factor
            prediction_dict[new_date] = predicted_count
            last_date = new_date
            last_count = predicted_count
        
        return prediction_dict

    # push stats
    def push_stats(self, recalculate_sim = False):
        
        # rebuild simulation
        self.db.florida_growth.delete_many({"series": "actual"})
        self.db.florida_growth_rates.delete_many({})
        if recalculate_sim:
            self.db.florida_growth.delete_many({"series": "predicted"})

        # get cumulated sums
        current_growth = stats.cum_sum().to_dict()
        data = []
        for date, count in current_growth.items():
            data.append({
                "date": date,
                "count": count,
                "series": "actual"
            })

        # simulate cumulated sums
        if recalculate_sim:
            # get average growth rate for the last 10 days
            average_growth_rate = self.cum_growth(10).mean()
            # simulate 30 days of growth at current growth rate
            simulated_growth = stats.growth_sim(14, average_growth_rate)
            for date, count in simulated_growth.items():
                data.append({
                    "date": date,
                    "count": count,
                    "series": "predicted"
                })
        
        try:
            self.db.florida_growth.insert_many(data)    
        except Exception as e:
            print(str(e))

        # store growth rates
        data = []
        growth_rates = self.cum_growth().to_dict()
        for date, rate in growth_rates.items():
            data.append({
                "date": date,
                "rate": rate
            })
        
        try:
            self.db.florida_growth_rates.insert_many(data)    
        except Exception as e:
            print(str(e))
        

stats = CoronavirusStats()
stats.push_stats()






