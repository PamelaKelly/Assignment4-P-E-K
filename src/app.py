# This will be for flask
import flask
import functools
from flask import Flask, render_template, request
from flask import jsonify
from scraper import scraper
from weather import weather_scraper
from main import Main
from flask_cors import CORS, cross_origin
import json
import urllib
import pandas as pd

app = flask.Flask(__name__)

app.add_url_rule('/',
                 view_func=Main.as_view('main'),
                 methods=["GET"])
app.add_url_rule('/<page>/',
                 view_func=Main.as_view('page'),
                 methods=["GET"])

     
@app.errorhandler(404)
@cross_origin()
def page_not_found(error):
    return flask.render_template('404.html'), 404

@app.route("/stations")
@cross_origin()
def get_stations():
    engine = scraper.connect_db("DublinBikeProjectDB.cun91scffwzf.eu-west-1.rds.amazonaws.com", "3306", "DublinBikeProjectDB", "theForkAwakens", "db_password.txt")
    sql = "select * from bike_stations;"
    rows = engine.execute(sql).fetchall()
    print("#found {} stations", len(rows))
    stations = jsonify(stations=[dict(row) for row in rows])    
    engine.dispose()
    return stations

@app.route("/weather")
@cross_origin()
def get_weather():
    engine = weather_scraper.connect_weather_db()
    sql = "select * from weather_data"
    rows = engine.execute(sql).fetchall()
    print("#found {} data points", len(rows))
    weather = jsonify(weather=[dict(row) for row in rows])
    engine.dispose()
    return weather

@app.route("/availability")
@cross_origin()
def availability():
    engine = scraper.connect_db("DublinBikeProjectDB.cun91scffwzf.eu-west-1.rds.amazonaws.com", "3306", "DublinBikeProjectDB", "theForkAwakens", "db_password.txt")
    # change this to suit what queries we will be using
    sql = "SELECT * from availability;"
    #sql = "SELECT bike_stands_available, bikes_available FROM availability where day='Wed' and station_number='1';"
    #sql = "SELECT bike_stations.station_number, bike_stations.station_name, bike_stations.station_address, bike_stations.banking_available, availability.bike_stands, availability.bike_stands_available, availability.bikes_available FROM bike_stations INNER JOIN availability ON bike_stations.station_number=availability.station_number where availability.station_number='1';"
    rows = engine.execute(sql).fetchall()
    print("#found {} availability", len(rows))
    availability = jsonify(stations=[dict(row) for row in rows])
    engine.dispose()
    return availability

@app.route('/station_details', methods=['GET', 'POST'])
@cross_origin()
def station_details():
    """Function to get dyanmic details for stations"""
    #Info will be pulled from a javascript function on the home page
    station_number = request.args.get('station_number')
    engine = scraper.connect_db("DublinBikeProjectDB.cun91scffwzf.eu-west-1.rds.amazonaws.com", "3306", "DublinBikeProjectDB", "theForkAwakens", "db_password.txt")
    sql = "SELECT * FROM availability WHERE station_number = %s ORDER BY last_updated DESC LIMIT 1;"
    details = engine.execute(sql, station_number).fetchall()
    print("#found {} stations", len(details))
    details = jsonify(stations=[dict(detail) for detail in details])
    engine.dispose()
    return details

@app.route('/charts', methods=['GET', 'POST'])
@cross_origin()
def get_charts():
    station_number = request.args.get('station_number')
    daily_averages = station_daily(station_number)
    daily = jsonify(daily_averages=daily_averages)
    hourly_averages = station_hourly(station_number)
    hourly = jsonify(hours=[dict(hour) for hour in hourly_averages])
    #bikes_hourly = jsonify(hourly_days=[dict(day) for day in hourly_averages])
    return daily, hourly

# For Google Charts: 
def get_avg_bikes(station_number, day):
    """Returns the average number of bike per day"""
    engine = scraper.connect_db("DublinBikeProjectDB.cun91scffwzf.eu-west-1.rds.amazonaws.com", "3306", "DublinBikeProjectDB", "theForkAwakens", "db_password.txt")
    sql = "select bikes_available, bike_stands_available from availability where station_number = %s and day = %s;"
    results = engine.execute(sql,station_number,day).fetchall()
    sum_bikes_available = 0
    sum_bike_stands_available = 0
    count_rows = 0
    
    for row in results:
        sum_bikes_available += row["bikes_available"]
        sum_bike_stands_available += row["bike_stands_available"]
        count_rows += 1
     
    if count_rows > 0:    
        avg_bikes = sum_bikes_available/count_rows
        avg_bike_stands = sum_bike_stands_available/count_rows
        
    engine.dispose()
    return avg_bikes, avg_bike_stands

def station_daily(station_number):
    """Returns the average number of bikes per day for a particular bike station
    Does this need to be a dictionary to be able to be used in a jsonify?"""
    averages = []
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    for i in range(len(days)):
        avg_this_day = get_avg_bikes(station_number, days[i])[0]
        averages.append(int(round(avg_this_day, 0)))
    return averages
 
def station_hourly(station_number):
    """Returns the average number of bikes per hour for a particular station
    on a particular day
    Does this need to be a dictionary to be able to be used with jsonify?"""
    #hourly_averages = dict()
    averages = []
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    for i in range(len(days)):
        bikes_perhour = get_bikes_per_hour(station_number, days[i])
        averages.append(bikes_perhour)
    return averages
 
def get_bikes_per_hour(station_number, day):
    """Getting the hourly average bikes for a particular station on a particular day"""
    sql = "select * from availability where station_number = %s;"
    engine = scraper.connect_db("DublinBikeProjectDB.cun91scffwzf.eu-west-1.rds.amazonaws.com", "3306", "DublinBikeProjectDB", "theForkAwakens", "db_password.txt")
    station_details = engine.execute(sql, station_number).fetchall()
    engine.dispose()
    #station_details = jsonify(stations=[dict(result) for result in results]) 
    # Every index in hours will represent it's corresponding hour - going by a 24hr clock we can have 0 up to 24 indices
    # A list of lists containing the sum of bikes so far and the counter for calculating the average? 
    hours = []
    avgs = []
    for i in range(25):
        # initialise default values
        hours.append([0, 0])
        
    for station in station_details:
        num_bikes = station["bikes_available"]
        last_update = station["last_updated"]
        dtime = scraper.datetime_formatter(last_update)
        hour = int(dtime[1][11:13])
        hours[hour][0] += num_bikes
        hours[hour][1] += 1
 
    for hour in hours:
        if hour[0] > 0 and hour[1] > 0:
            avg_bikes = hour[0]/hour[1]
            avgs.append(int(round(avg_bikes, 0)))
         
    return avgs


if __name__ == "__main__":
    app.run(debug=True)
