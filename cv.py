from selenium import webdriver
from pymongo import MongoClient
import json
import re
from datetime import datetime

class Coronavirus():
    def __init__(self):
        with open('config.json') as config_file:
            self.config = json.load(config_file)
        self.driver = webdriver.Chrome(self.config["other"]["chromedriver_binary"])
        self.client = MongoClient(self.config["mongodb"]["url"])
        self.db = self.client.get_database(self.config["mongodb"]["database"])
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

            self.store_data(cases)
            self.driver.close()
            self.client.close()

        except Exception as e:
            print(str(e))
            self.driver.quit()
    
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
        
        print("Found {} new cases.".format(len(new_cases)))

        if len(new_cases) > 0:
            try:
                print("Updating database.")
                self.db.florida.insert_many(new_cases)    
            except Exception as e:
                print(str(e))

bot = Coronavirus()
bot.get_data()