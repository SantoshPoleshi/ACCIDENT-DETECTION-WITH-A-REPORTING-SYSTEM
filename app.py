import flask
from flask import render_template, request, jsonify
import pandas as pd
import pickle
from datetime import datetime
from sklearn.ensemble import GradientBoostingClassifier
import requests, json
from flask_mysqldb import MySQL
import MySQLdb.cursors

app = flask.Flask(__name__, template_folder='Templates')

#code for connection
app.config['MYSQL_HOST'] = 'localhost'#hostname
app.config['MYSQL_USER'] = 'root'#username
app.config['MYSQL_PASSWORD'] = ''#password
#in my case password is null so i am keeping empty
app.config['MYSQL_DB'] = 'accident_severity'#database name

mysql = MySQL(app)
@app.route('/')


@app.route('/main', methods=['GET', 'POST'])
def main():
    if flask.request.method == 'GET':
        return(flask.render_template('main.html'))

#Prediction
model = pickle.load(open('Model/accidentSeverityPredictor.pkl', 'rb'))

@app.route('/anotherlocation', methods=['GET', 'POST'])
def another():
    if flask.request.method == 'POST':    
        roveg1    = request.form['roveh']
        roadsurf1 = request.form['roadsurf']
        light1    = request.form['light']
        weather1  = request.form['weather']
        cclass1   = request.form['cclass']
        typeveg1  = request.form['typeveh']
      

        input_variables = pd.DataFrame([[roveg1, roadsurf1, light1, weather1, cclass1,  typeveg1]],
                                       columns=['1st Road Class', 'Road Surface','Lighting Conditions','Weather Conditions','Casualty Class','Type of Vehicle'], dtype=float)
        prediction = model.predict(input_variables)[0]
                
        
        if prediction==1:
            prediction="Serious Accident"
        else:
            prediction="Slight Accident"
        
        pred = {"prediction":prediction}
    return jsonify(pred)

@app.route('/desitinationfound', methods=['GET', 'POST'])
def destination():
    if flask.request.method == 'POST':    
        
        dest1     = request.form['dest']
        src_long  = request.form['longtitude']
        src_lat   = request.form['latitude']
        roveg     = int(request.form['liveroad'])
        typeveg   = int(request.form['livevehicle'])
        cclass    = int(request.form['livecasuality'])
        return_data = []
        
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM indian_cities_database WHERE city = %s', (dest1, ))
        result = cursor.fetchone();
    
        if(result is None):
            src_data =  getpred(src_long, src_lat, roveg, typeveg, cclass)
            return_data.append(src_data)
        else:
            dest_long  = result["longt"]
            dest_lat   = result["lat"]
            dest_state = result["state"]
            
            
            cursor.execute('SELECT * FROM indian_cities_database WHERE longt >= %s AND longt <= %s  AND state = %s LIMIT 4' , (src_long, dest_long,  dest_state,))
            result1 = cursor.fetchall();
            
            #print(result1)
            
            src_data =  getpred(src_long, src_lat, roveg, typeveg, cclass)
            return_data.append(src_data)
            
            if len(result1) >= 1:
               for i in range(len(result1)):
                   dest_data =  getpred(result1[i]["longt"], result1[i]["lat"], roveg, typeveg, cclass)
                   return_data.append(dest_data)
            else:
                dest_data =  getpred(dest_long, dest_lat, roveg, typeveg, cclass)
                return_data.append(dest_data)
       
    return jsonify(return_data)


@app.route('/detectlive', methods=['GET', 'POST'])
def detect():
    if flask.request.method == 'POST':
       longtitude       = request.form['longitude']
       latitude        = request.form['latitude']
       roveg           = int(request.form['liveroad'])
       typeveg         = int(request.form['livevehicle'])
       cclass          = int(request.form['livecasuality'])
       
       pred = getpred(longtitude, latitude, roveg, typeveg, cclass)
       
    return jsonify(pred)

def getpred(longtitude, latitude, roveg, typeveg, cclass):
    
    #accesskey = "4760ff014bc58270f85ed56767ca215e"
    accesskey = "992405b6d4fbbd002fce6982883a4c17"
    base_url = "http://api.weatherstack.com/current?"
    full_url = base_url+"access_key="+accesskey+"&query="+latitude+","+longtitude
    response = requests.get(full_url) 
    x = response.json()
    
    roadsurf        = "0"
    light           = ""
    weather         = ""
    basicroadsurf  = x['current']['weather_code']
    wind_speed     = x['current']['wind_speed']
    is_day         =  x['current']['is_day']
    
    if basicroadsurf in [389, 353, 176, 302, 299, 296, 386, 284, 281, 266, 263]:
        roadsurf = 4  #Wet
        if wind_speed > 24:
            weather = 5  #Raining with high winds
        else:
            weather = 4  #Raining without high winds
    elif basicroadsurf in [143, 179, 182, 185, 248, 260, 395, 338, 335, 260]:
        roadsurf = 1  #Frost
        weather = 1  #Fog or mist – if hazard
    elif basicroadsurf in [359, 356, 308, 305, 320, 314, 311, 293, 317]:
        roadsurf = 2  #Flood
    elif basicroadsurf in [200, 227, 230, 263, 392, 377, 374, 371, 368, 365, 362, 350, 332, 329, 326, 323]:
        roadsurf = 3  #Snow
        if wind_speed > 24:
            weather = 7  #Snow with high winds
        else:
            weather = 6  #Snow without high winds
    else:
        roadsurf = 0  #Dry
        if wind_speed > 24:
            weather = 2  #Fine with high winds
        else:
            weather = 0  #Fine without high winds
            
    
    if is_day == "no":
        light = 3
    else:
        light = 0
 
    input_variables = pd.DataFrame([[roveg, roadsurf, light, weather, cclass,  typeveg]],
                                  columns=['1st Road Class', 'Road Surface','Lighting Conditions','Weather Conditions','Casualty Class','Type of Vehicle'], dtype=float)
    prediction = model.predict(input_variables)[0]
           
   
    if prediction == 1:
       prediction="Serious Accident"
    else:
       prediction="Slight Accident"
    roveg1 = roadsurf1 = light1 = weather1 = cclass1 = typeveg1 = ''
    if roveg == 0:
       roveg1 = 'A - Type'
    elif roveg == 1:
       roveg1 = 'A(M) - Type'
    elif roveg == 2:
       roveg1 = 'B - Type'
    elif roveg == 3:
       roveg1 = 'Motor way - Type'
    elif roveg == 4:
       roveg1 = 'Unclassified - Type'
          
    if roadsurf == 0:
       roadsurf1 = 'Dry'
    elif roadsurf == 1:
       roadsurf1 = 'Frost'
    elif roadsurf == 2:
       roadsurf1 = 'Flood'
    elif roadsurf == 3:
       roadsurf1 = 'Snow'
    elif roadsurf == 4:
       roadsurf1 = 'Wet'
          
          
    if light == 0:
        light1 = 'No street lighting'
    elif light == 1:
        light1 = 'Street lighting unknown'
    elif light == 2:
        light1 = 'Street lights present and lit'
    elif light == 3:
        light1 = 'Darkness'
         
    if weather == 0:
        weather1 = 'Fine without high winds'
    elif weather == 1:
        weather1 = 'Fog or mist – if hazardn'
    #elif weather == 2:
       # weather1 = 'Street lights present and lit'
    elif weather == 3:
        weather1 = 'Other'
    elif weather == 4:
        weather1 = 'Raining without high winds'
    elif weather == 5:
        weather1 = 'Raining with high winds'
    elif weather == 6:
        weather1 = 'Snowing without high winds'
    elif weather == 7:
        weather1 = 'Snowing with high winds'
    elif weather == 8:
        weather1 = 'Unknown'
         
    if cclass == 0:
        cclass1 = 'Driver'
    elif cclass == 1:
        cclass1 = 'Passenger'
    elif cclass == 2:
        cclass1 = 'Pedestrian'
          
    
    if typeveg == 0:
        typeveg1 = 'Agri vehicle'
    elif typeveg == 1:
        typeveg1 = 'Bus'
    elif typeveg == 2:
        typeveg1 = 'Car'
    elif typeveg == 3:
        typeveg1 = 'Goods Vehicle'
    elif typeveg == 4:
        typeveg1 = 'Motorcycle'
    elif typeveg == 5:
        typeveg1 = 'Pedal cycle'
    elif typeveg == 6:
        typeveg1 = 'Other vehicle'
     

    pred = {"prediction":prediction,
            "curlocation":x["location"]["name"],
            "region":x["location"]["region"],
            "temperature":x["current"]["temperature"],
            "localtime":x["location"]["localtime"],
            "sroveg":roveg1,
            "basicroadsurf":roadsurf1,
            "light":light1,
            "weather":weather1,
            "scclass":cclass1,
            "stypeveg":typeveg1}
    
    return pred
    
if __name__ == '__main__':
    app.run()
