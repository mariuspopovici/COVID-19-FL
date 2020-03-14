from selenium import webdriver
from pymongo import MongoClient
import json
import re
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
                    "chromedriver_binary": environ.get("CHROMEDRIVER_PATH"),
                    "data_url": environ.get("DATA_URL"),
                    "dashboard_url": environ.get("DASHBOARD_URL")
                },
                "smtp": {
                    "user": environ.get("SMTP_USER"),
                    "password": environ.get("SMTP_PASSWORD"),
                    "email_from": environ.get("EMAIL_FROM"),
                    "email_to": environ.get("EMAIL_TO"),
                }
            }

        # set up chromedriver options
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")

        self.driver = webdriver.Chrome(self.config["other"]["chromedriver_binary"], options=chrome_options)

        self.client = MongoClient(self.config["mongodb"]["url"])
        self.db = self.client.get_database(self.config["mongodb"]["database"])

    # scrape source data from FLDOH
    def get_data(self):
        try:
            self.driver.get(self.config["other"]["data_url"])
            table = self.driver.find_element_by_xpath('/html/body/div[1]/div[3]/div/div[2]/div[3]/div/div[2]/block/table')
            row_num = 0
            cases = []
            for row in table.find_elements_by_css_selector('tr'):
                if row_num >= 2:
                    cells = row.find_elements_by_tag_name('td')
                    case = {
                        "case_number": int(re.sub("[^0-9]", "", cells[0].text)),
                        "county": cells[1].text,
                        "age": int(cells[2].text),
                        "sex": cells[3].text,
                        "travel": cells[4].text,
                        "date_added": datetime.now()
                    }
                    cases.append(case)
                row_num+=1

            store_result = self.store_data(cases)
            self.driver.close()
            self.client.close()

        except Exception as e:
            print(str(e))
            self.driver.quit()
            return {
                "success": False,
                "message": str(e)
            }
        
        return {
            "success": True,
            "message": "{} new cases and {} cases under investigation".format(store_result['new_cases'], 
                store_result['under_investigation'])
        }
    
    # store case data to Atlas/MongoDB instance
    def store_data(self, cases):        
        records = self.db.florida
        cursor = records.aggregate([
            {
                "$group": {
                    "_id": None,
                    "max_case": {"$max": "$case_number"}
                }
            }
        ])
        
        result = list(cursor)

        max_case_number = 0 
        
        if len(result) > 0:
            max_case_number = result[0]['max_case']
        
        new_cases = list(filter(lambda item: item['case_number'] > max_case_number, cases))        

        inv_cursor = records.find({"travel": "Under Investigation"}, {"case_number": 1})
        under_investigation = list(map(lambda item: item['case_number'], list(inv_cursor)))

        update_cases = list(filter(lambda item: item['case_number'] in under_investigation, cases))

        print("Found {} new cases.".format(len(new_cases)))
        print("Found {} cases under investigation.".format(len(under_investigation)))

        
        try:
            if len(new_cases) > 0:
                print("Adding new cases to database.")
                self.db.florida.insert_many(new_cases)    
            if len(update_cases) > 0:
                print("Updating under investigation cases.")
                for case in update_cases:
                    self.db.florida.update_one(
                        {"case_number": case['case_number']}, 
                        {"$set": {"travel": case['travel']}},
                        upsert=False)        
        except Exception as e:
            print(str(e))
            return {
                "success": False,
                "message": str(e)
            }
        
        return {
            "success": True,
            "message": "",
            "new_cases": len(new_cases),
            "under_investigation": len(update_cases)
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

        print('Hey Email has been sent!')
        server.quit()

bot = Coronavirus()
result = bot.get_data()

if result['success']:
    bot.send_mail(result['message'])