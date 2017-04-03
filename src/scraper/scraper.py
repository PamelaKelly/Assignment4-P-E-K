import requests
import json
import time
import datetime
import os
import sqlalchemy
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.mssql.base import TINYINT
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.mysql.types import FLOAT, VARCHAR, TIMESTAMP
#from IPython.display import display - not working

#Need to make connection to db once and store connection in global object? - name of library? 

Base = declarative_base()

class Station(Base):
    __tablename__ = 'bike_stations'
    
    station_number = Column(Integer, primary_key = True, nullable = False)
    station_name = Column(String, nullable = False)
    station_address = Column(String, nullable = False)
    station_loc_lat = Column(FLOAT, nullable = False)
    station_loc_long = Column(FLOAT, nullable = False)
    banking_available = Column(TINYINT, nullable = False)
    bonus = Column(TINYINT, nullable = False)
    
    def __repr__(self):
        return """
        <Station=(station_number=%s, 
        station_name='%s',
        station_address='%s',
        station_loc_lat=%s,
        station_loc_long=%s,
        banking_available=%s,
        bonus=%s)>""" % (self.station_number, self.station_name, 
                         self.station_address, self.station_loc_lat,
                         self.station_loc_long, self.banking_available,
                         self.bonus)
        
class Station_Dynamic(Base):
    __tablename__ = 'availability'
    
    station_number = Column(Integer, primary_key = True, nullable = False)
    bike_stands = Column(Integer, nullable = False)
    bike_stands_available = Column(Integer, nullable = False)
    bikes_available = Column(Integer, nullable = False)
    last_updated = Column(Integer, primary_key = True, nullable = False)
    day = Column(VARCHAR, nullable = False)
    
    def __repr__(self):
        return """
        <Station_Dynamic=(station_number=%s,
        bike_stands=%s, 
        bike_stands_available=%s,
        bikes_available=%s,
        last_updated=%s, 
        day = %s)>""" % (self.station_number, self.bike_stands,
                                self.bike_stands_available, self.bikes_available,
                                self.last_updated, self.day)
        
    
    


def datetime_formatter(info):
    """Takes the current time and returns the date, time and day of the week"""
    if type(info) == float:
        dt = datetime.datetime.fromtimestamp(info).strftime('%Y-%m-%d %H-%M-%S')
        day = datetime.datetime.fromtimestamp(info).strftime('%a')
        return dt, day
    elif type(info) == str:
        return day_from_filename(info)

        
def write_to_file(data):
    """Stores json data in a file with date and time as part of filename"""
    dt = datetime_formatter(time.time())[0]
    with open('db-data-' + dt + '.txt', 'w') as outfile:
        json.dump(data, outfile)
    
def connect_db():
    """Connects to the database"""
    try:
        URI = "DublinBikeProjectDB.cun91scffwzf.eu-west-1.rds.amazonaws.com"
        PORT = "3306"
        DB = "DublinBikeProjectDB"
        USER = "theForkAwakens"
        file = "db_password.txt"
        fh = open(file)
        PASSWORD = fh.readline().strip()
        engine = create_engine("mysql+pymysql://{}:{}@{}:{}/{}".format(USER, PASSWORD, URI, PORT, DB), echo = True)
        return engine
    except Exception as e:
        print("Error Type: ", type(e))
        print("Error Details: ", e)    

def write_to_db(data, id):
    """Creates SQLAlchemy objects from json data and pushes these objects to the db as rows"""
    day = datetime_formatter(id)[1] # approach doesn't work for writing from file to db
    
    engine = connect_db()
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        for i in data:
            banking = 1 if (data[0]['banking']) else 0
            bonus = 1 if (data[0]['bonus']) else 0
                
            #don't actually need to instantiate object here - could use session.add_all directly but choosing
            #to do it this way for readability
            
            station = Station(station_number = i["number"],
                          station_name = i["name"], 
                          station_address = i["address"], 
                          station_loc_lat = i["position"]["lat"],
                          station_loc_long = i["position"]["lng"],
                          banking_available = banking,
                          bonus = bonus)
            
            station_dynamic = Station_Dynamic(station_number = i["number"],
                                              bike_stands = i["bike_stands"], 
                                              bike_stands_available = i["available_bike_stands"],
                                              bikes_available = i["available_bikes"],
                                              last_updated = i["last_update"], 
                                              day = day)
            
            session.add_all([station, station_dynamic])
            session.commit()   
        
    except Exception as e:
        print("Error Type: ", type(e))
        print("Error Details: ", e)  

def file_to_db(file):
    print(file)
    """ Helper function to write data from file to database"""
    try:
        with open(file, 'r') as obj:
            data = json.load(obj)
        write_to_db(data, file)
    except Exception as e:
        print("Error Type: ", type(e))
        print("Error Details: ", e)
      
def multiple_files_to_db():
    try:       
        for file in os.listdir(os.getcwd()):
            if file.endswith(".txt"):
                file_to_db(file)
    except Exception as e:
        print("Error Type: ", type(e))
        print("Error Details: ", e)

def get_data():
    """Sends the request to the Dublin bikes API and returns a json file"""
    file = "db-apikey.txt"
    fh = open(file)
    APIKEY = fh.readline().strip()
    NAME = "Dublin"
    URI = "https://api.jcdecaux.com/vls/v1/stations"
    r = requests.get(URI, params={"apiKey": APIKEY, "contract": NAME})
    data = json.JSONDecoder().decode(r.text)
    return data

def run_scraper():
    """Runs the overall program to scrape the data and store the data"""
    while True:
        data = get_data()
        write_to_file(data)
        write_to_db(data, time.time())
        time.sleep(300)

def day_from_filename(filename):
    word = filename.split()
    date = word[0][7:]
    new_date = ""
    if date[5:7] == '04':
        month = 'April'
    elif date[5:7] == '03':
        month = 'March'
    new_date += (month + " " + date[8:] + ", " + date[:4])
    day = datetime.datetime.strptime(new_date, '%B %d, %Y').strftime('%a')
    return day

