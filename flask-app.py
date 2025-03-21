from flask import Flask, jsonify, request, send_from_directory
import os
from werkzeug.utils import secure_filename
import uuid as uuid
from flask_cors import CORS
from datetime import datetime, timedelta
import mysql.connector
from flask_socketio import SocketIO, send, emit
from datetime import datetime
from pyngrok import ngrok
import pytz

app = Flask(__name__)
CORS(app)
# socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet", logger=True, engineio_logger=True, ping_timeout=60, ping_interval=25, max_http_buffer_size=1000000)  # or async_mode="gevent"
socketio = SocketIO(app, cors_allowed_origins="*")  # Allow all origins for WebSocket

db_name = "mediminder457$mediminder_db"
number_of_sched_ahead = 10

# Enable CORS for all routes

# Set up Ngrok
# ngrok.set_auth_token("2u7ndFgxshQX6UHvFUFtbfCeidx_5G3fLxfQWyQ41g7PnRBmj")
# public_url = ngrok.connect(5000).public_url
# print(f"Ngrok Tunnel: {public_url}")

# Configure MySQL connection
# app.config['MYSQL_HOST'] = "mediminder457.mysql.pythonanywhere-services.com"
# app.config['MYSQL_USER'] = "mediminder457"
# app.config['MYSQL_PASSWORD'] = "mediMINDERmySQLdb!!"
# app.config['MYSQL_DB'] = "mediminder457$mediminder_db"

# Configure upload folder and allowed file types
app.config['UPLOAD_FOLDER'] = './uploads'

# mysql = mysql.connector.connect(host="localhost", user="root", password="", database="medtrackdb")


def strip_seconds():
    Mysql = mysql.connector.connect(host="localhost", user="root", password="", database="medtrackdb")    
    cursor = Mysql.cursor()

    cursor.execute("SELECT uid, start FROM pockets")
    records = cursor.fetchall()

    for record in records:
        uid, start = record  # Destructure the tuple

        # Convert to datetime and strip seconds
        original_datetime = datetime.strptime(str(start), "%Y-%m-%d %H:%M:%S")
        formatted_datetime = original_datetime.replace(second=0).strftime("%Y-%m-%d %H:%M:%S")

        # Update the database
        cursor.execute(
            "UPDATE pockets SET start = %s WHERE uid = %s",
            (formatted_datetime, uid)
        )

    Mysql.commit()
    cursor.close()

def initialize_database():
    """Ensure the database and table exist."""
    Mysql = mysql.connector.connect(host="localhost", user="root", password="", database="medtrackdb")
    cursor = Mysql.cursor()

    try:
        # Ensure database exists
        cursor.execute("CREATE DATABASE IF NOT EXISTS medtrackdb")
        print("Database 'medtrackdb' ensured.")

        # Use the 'medtrackdb' database
        cursor.execute("USE medtrackdb")

        # Ensure the 'user' table exists
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(50),
                img_name VARCHAR(255),
                status VARCHAR(10)
            )
            """
        )
        Mysql.commit()
        print("Table 'users' ensured.")

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS pockets (
                uid INT AUTO_INCREMENT PRIMARY KEY,
                id INT,
                legend VARCHAR(1),
                label VARCHAR(50),
                start DATETIME DEFAULT NULL,
                hour INT NOT NULL DEFAULT 0,
                min INT NOT NULL DEFAULT 0,
                status VARCHAR(20) NOT NULL DEFAULT 'Deactivated',
                FOREIGN KEY (id) REFERENCES users(id)
            )
            """
        )
        Mysql.commit()
        print("Table 'pockets' ensured.")

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS records (
                uuid INT AUTO_INCREMENT PRIMARY KEY,
                uid INT,
                legend VARCHAR(1),
                label VARCHAR(50),
                sched DATETIME,
                taken DATETIME,
                status VARCHAR(100),
                FOREIGN KEY (uid) REFERENCES pockets(uid)
            )
            """
        )
        Mysql.commit()
        print("Table 'records' ensured.")

    except Exception as e:
        print(f"Error during database initialization: {e}")
    finally:
        cursor.close()


with app.app_context():
    initialize_database()


def save_image(image):
    if image:
        # grab the image filename
        img_filename = secure_filename(image.filename)

        # make the image filename unique
        img_name = str(uuid.uuid1()) + "_" + img_filename

        # save the image with the set filepath + unique filename
        image.save(os.path.join(app.config['UPLOAD_FOLDER'], img_name))
    else:
        img_name = "empty.jpg"

    return img_name

def delete_image(image_name):
    if image_name != "empty.jpg":
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_name)

        if os.path.exists(image_path):
            os.remove(image_path)


# App Routing
@socketio.on('connect')
def handle_connect():
    print('Client connected')

@app.route('/show_databases')
def show_databases():
    Mysql = mysql.connector.connect(host="localhost", user="root", password="", database="medtrackdb")
    cursor = Mysql.cursor()

    try:
        cursor.execute("SHOW DATABASES")
        databases = []
        for db in cursor:
            databases.append(db[0])
        return databases
    except Exception as e:
        return f"Error fetching databases: {e}"
    finally:
        cursor.close()

@app.route('/show_tables')
def show_tables():
    Mysql = mysql.connector.connect(host="localhost", user="root", password="", database="medtrackdb")
    cursor = Mysql.cursor()

    try:
        cursor.execute("USE medtrackdb")
        cursor.execute("SHOW TABLES")
        tables = [table[0] for table in cursor.fetchall()]  # Fetch all tables
        return jsonify(tables)
    except Exception as e:
        return f"Error fetching tables: {e}"
    finally:
        cursor.close()

@app.route('/')
def index():
    return "Hello, Flask! Database and table setup is automatic."

@app.route('/fetch_users', methods=['GET'])
def fetch_users():
    Mysql = mysql.connector.connect(host="localhost", user="root", password="", database="medtrackdb")
    cursor = Mysql.cursor()
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()

    user_list = []
    if users:
        for user in users:
            user_list.append({
                "id": user[0],
                "name": user[1],
                "img_name": user[2],
                "status": user[3]
            })

    cursor.close()
    # strip_seconds()
    return jsonify(user_list)

@app.route('/create_user', methods=['POST'])
def create_user():
    name = request.form['username']
    image = request.files['user_image']

    if not name:
        return "Username is required.", 400

    img_name = save_image(image)

    Mysql = mysql.connector.connect(host="localhost", user="root", password="", database="medtrackdb")
    cursor = Mysql.cursor()
    cursor.execute("SELECT name FROM users WHERE status = 'Active'")
    n_active = cursor.fetchone()

    if not n_active:  # if there are no active user
        status = "Active"
    else:
        status = "Inactive"

    cursor.execute("INSERT INTO users (name, img_name, status) VALUES (%s, %s, %s)", (name, img_name, status,))
    Mysql.commit()

    user_id = cursor.lastrowid  # Get the ID of the last inserted user
    pocket_data = [
        (user_id, 'A', 'A'),
        (user_id, 'B', 'B'),
        (user_id, 'C', 'C'),
        (user_id, 'D', 'D'),
        (user_id, 'E', 'E'),
    ]

    cursor.executemany("INSERT INTO pockets (id, legend, label) VALUES (%s, %s, %s)", pocket_data)
    Mysql.commit()

    cursor.close()

    return "User and Pockets created successfully!"

@app.route('/update_user/<int:id>', methods=['PATCH'])
def update_user(id):
    name = request.form['updatedUserName']
    image = request.files['updatedUserImg']

    Mysql = mysql.connector.connect(host="localhost", user="root", password="", database="medtrackdb")
    cursor = Mysql.cursor()
    cursor.execute("SELECT name, img_name FROM users WHERE id = %s", (id,))
    user = cursor.fetchone()

    if image:
        img_name = save_image(image)
        delete_image(user[1])
    else:
        img_name = user[1]

    cursor.execute("UPDATE users SET name = %s, img_name = %s WHERE id = %s", (name, img_name, id,))
    Mysql.commit()
    cursor.close()
    return "User updated successfully!"

@app.route('/delete_user/<int:id>', methods=['DELETE'])
def delete_user(id):
    Mysql = mysql.connector.connect(host="localhost", user="root", password="", database="medtrackdb")
    cursor = Mysql.cursor()

    cursor.execute("SELECT uid FROM pockets WHERE id = %s", (id,))
    pockets_uid = cursor.fetchall()
    for uid in pockets_uid:
        cursor.execute("DELETE FROM records WHERE uid = %s", (uid[0],))
    
    cursor.execute("DELETE FROM pockets WHERE id = %s", (id,))

    # Fetch the user to get the image name before deletion
    cursor.execute("SELECT img_name FROM users WHERE id = %s", (id,))
    user_img = cursor.fetchone()

    if user_img:
        delete_image(user_img[0])

    cursor.execute("DELETE FROM users WHERE id = %s", (id,))
    Mysql.commit()
    cursor.close()
    return "User deleted successfully!"

@app.route('/set_active/<int:id>', methods=['PATCH'])
def set_active(id):
    Mysql = mysql.connector.connect(host="localhost", user="root", password="", database="medtrackdb")
    cursor = Mysql.cursor()
    cursor.execute("SELECT id FROM users WHERE status = 'Active' AND id != %s", (id,))
    active_ID = cursor.fetchone()

    if active_ID:
        cursor.execute("UPDATE users SET status = 'Inactive' WHERE id = %s", (active_ID[0],))
        cursor.execute("UPDATE pockets SET status = 'Deactivated' WHERE id = %s", (active_ID[0],))
        cursor.execute("UPDATE users SET status = 'Active' WHERE id = %s", (id,))
        Mysql.commit()
        cursor.close()
        return "User updated successfully!"

    return "Failed to update user!", 400

@app.route('/fetch_pockets/<int:id>', methods=['GET'])
def fetch_pockets(id):
    Mysql = mysql.connector.connect(host="localhost", user="root", password="", database="medtrackdb")
    cursor = Mysql.cursor()
    cursor.execute("SELECT uid, legend, label, start, hour, min, status FROM pockets WHERE id = %s", (id,))
    pockets = cursor.fetchall()

    if not pockets:
        return jsonify({"error": "No pockets found"}), 404  # Respond with a 404 error

    # Convert to a list of dictionaries
    columns = ["uid", "legend", "label", "start", "hour", "min", "status"]
    pocket_list = []

    for row in pockets:
        pocket_data = dict(zip(columns, row))

        # Handle NULL start time safely
        try:
            pocket_data["start"] = pocket_data["start"].strftime('%Y-%m-%d %H:%M')
            strip_seconds
        except AttributeError:  # If start is None, set it to an empty string
            pocket_data["start"] = ""

        pocket_list.append(pocket_data)

    return jsonify(pocket_list)

@app.route('/rename_label/<int:uid>', methods=['PATCH'])
def rename_label(uid):
    label = request.form['renameLabel']

    Mysql = mysql.connector.connect(host="localhost", user="root", password="", database="medtrackdb")
    cursor = Mysql.cursor()
    cursor.execute("SELECT label FROM pockets WHERE uid = %s", (uid,))
    labelQuery = cursor.fetchone()[0]

    cursor.execute("UPDATE pockets SET label = %s WHERE uid = %s", (label, uid,))

    Mysql.commit()
    cursor.close()
    
    if labelQuery.upper() != label.upper():
        deactivate_sched(uid)

    return "Label renamed successfully!"

@app.route('/set_sched/<int:uid>', methods=['PATCH'])
def set_sched(uid):
    date = request.form['setDate']
    time = request.form['setTime']
    step_hour = abs(int(request.form['setHour']))
    step_min = abs(int(request.form['setMin']))

    start = " ".join([date, time])

    Mysql = mysql.connector.connect(host="localhost", user="root", password="", database="medtrackdb")
    cursor = Mysql.cursor()
    cursor.execute("SELECT start, hour, min FROM pockets WHERE uid = %s", (uid,))
    oldQuery = cursor.fetchone()

    cursor.execute("UPDATE pockets SET start = %s, hour = %s, min = %s WHERE uid = %s", (start, step_hour, step_min, uid,))
    cursor.execute("SELECT start, hour, min FROM pockets WHERE uid = %s", (uid,))
    newQuery = cursor.fetchone()

    Mysql.commit()
    cursor.close()
    
    if oldQuery != newQuery:
        deactivate_sched(uid)

    return "Label renamed successfully!"

@app.route('/toggle_sched/<int:uid>/<int:stat>', methods=['PATCH'])
def toggle_sched(uid, stat):
    if stat == 1:
        activate_sched(uid)
    else:
        deactivate_sched(uid)

    # Mysql = mysql.connector.connect(host="localhost", user="root", password="", database="medtrackdb")
    # cursor = Mysql.cursor()

    # cursor.execute("SELECT status FROM pockets WHERE uid = %s", (uid,))
    # pocket_status = cursor.fetchone()[0]
    # cursor.close()
    # if pocket_status == "Activated":
    #     create_schedule(uid)
    #     step_schedule(uid)
    # else:
    #     remove_null_schedule(uid)

    return "Schedule activated/deactivated successfully!"

def activate_sched(uid):
    Mysql = mysql.connector.connect(host="localhost", user="root", password="", database="medtrackdb")
    cursor = Mysql.cursor()
    cursor.execute("UPDATE pockets SET status = 'Activated' WHERE uid = %s", (uid,))
    Mysql.commit()
    cursor.close()

    create_schedule(uid)
    step_schedule(uid)
    # socketio.emit('message', {'message': 'Hello from server!'})

def deactivate_sched(uid):
    Mysql = mysql.connector.connect(host="localhost", user="root", password="", database="medtrackdb")
    cursor = Mysql.cursor()
    cursor.execute("UPDATE pockets SET status = 'Deactivated' WHERE uid = %s", (uid,))
    Mysql.commit()
    cursor.close()

    remove_null_schedule(uid)
    # socketio.emit('message', {'message': 'Hello from server!'})

def create_schedule(uid):
    Mysql = mysql.connector.connect(host="localhost", user="root", password="", database="medtrackdb")
    cursor = Mysql.cursor()

    # Fetch the latest schedule from the 'pockets' table for the given UID
    cursor.execute("SELECT legend, label, start FROM pockets WHERE uid = %s", (uid,))
    pocket_data = cursor.fetchone()
    
    if not pocket_data:
        cursor.close()
        print("No pocket data found")
        return "No pocket data found"

    legend, label, new_sched = pocket_data

    # Ensure new_sched is a valid datetime and is not in the past
    if new_sched and new_sched < datetime.now():
        cursor.close()
        print("Schedule time is in the past, not inserting")
        return "Schedule time is in the past"

    # Fetch all existing schedules from the 'records' table for the given UID
    cursor.execute("SELECT legend, label, sched FROM records WHERE uid = %s", (uid,))
    sched_data = cursor.fetchall()
    cursor.close()

    # If no schedule exists, insert the new one
    if len(sched_data) < 1:
        Mysql = mysql.connector.connect(host="localhost", user="root", password="", database="medtrackdb")
        cursor = Mysql.cursor()
        cursor.execute("INSERT INTO records (uid, legend, label, sched) VALUES (%s, %s, %s, %s)", 
                       (uid, legend, label, new_sched))
        Mysql.commit()
        cursor.close()
        print("Inserted a new schedule")
        return "Inserted a new schedule"

    # Ensure the new schedule is different from the last one before inserting
    last_sched = sched_data[-1]  # Get the most recent schedule
    if (legend, label, new_sched) != last_sched:
        Mysql = mysql.connector.connect(host="localhost", user="root", password="", database="medtrackdb")
        cursor = Mysql.cursor()
        cursor.execute("INSERT INTO records (uid, legend, label, sched) VALUES (%s, %s, %s, %s)", 
                       (uid, legend, label, new_sched))
        Mysql.commit()
        cursor.close()
        print("Inserted a new schedule (updated)")
        return "Inserted a new schedule"

    print("Same schedule, no changes made")
    return "Same as the last schedule"
    
def step_schedule(uid):
    Mysql = mysql.connector.connect(host="localhost", user="root", password="", database="medtrackdb")
    cursor = Mysql.cursor()

    # Fetch the step hour and minute for the given UID (uid)
    cursor.execute("SELECT label, legend, hour, min FROM pockets WHERE uid = %s", (uid,))
    result = cursor.fetchone()

    if not result:
        raise ValueError(f"No step data found for UID {uid}")

    label1, legend, step_hour, step_min = result
    step_sched = timedelta(hours=step_hour, minutes=step_min)

    # Fetch the latest schedule from the records
    cursor.execute("SELECT label, sched FROM records WHERE uid = %s", (uid,))
    latest_record = cursor.fetchall()[-1]

    cursor.execute("SELECT * FROM records WHERE taken IS NULL AND uid = %s", (uid,))
    n_null = len(cursor.fetchall())

    if not latest_record:
        raise ValueError(f"No record found for UID {uid}")

    label, last_sched = latest_record

    n_sched = number_of_sched_ahead
    N_sched = n_sched - n_null

    new_schedules = []
    for i in range(N_sched):
        last_sched += step_sched
        sched = (uid, legend, label1, last_sched.strftime("%Y-%m-%d %H:%M:%S"))
        new_schedules.append(sched)

    cursor.executemany("INSERT INTO records (uid, legend, label, sched) VALUES (%s, %s, %s, %s)", new_schedules)
    Mysql.commit()
    cursor.close()

    return "Successfully added new schedules"

def remove_null_schedule(uid):
    Mysql = mysql.connector.connect(host="localhost", user="root", password="", database="medtrackdb")
    cursor = Mysql.cursor()

    # Select records with 'taken' IS NULL for the given user ID
    cursor.execute("SELECT * FROM records WHERE taken IS NULL AND uid = %s", (uid,))
    null_records = cursor.fetchall()

    if not null_records:
        cursor.close()
        return f"No records with NULL 'taken' found for UID {uid}."

    # Delete the records with 'taken' IS NULL for the user
    cursor.execute("DELETE FROM records WHERE taken IS NULL AND uid = %s", (uid,))
    Mysql.commit()
    cursor.close()

    return f"Deleted {cursor.rowcount} records with NULL 'taken' for UID {uid}."

@app.route('/fetch_records/<int:uid>', methods=['GET'])
def fetch_records(uid):
    Mysql = mysql.connector.connect(host="localhost", user="root", password="", database="medtrackdb")
    cursor = Mysql.cursor()

    # Fetch records for the given UID
    cursor.execute("SELECT uuid, uid, label, sched, taken, status FROM records WHERE uid = %s", (uid,))
    records = cursor.fetchall()
    cursor.close()

    if not records:
        return jsonify([])

    # Format the records into a list of dictionaries for better readability
    record_list = [
        {
            "uuid": record[0],
            "uid": record[1],
            "label": record[2],
            "sched": record[3].strftime("%Y-%m-%d %H:%M:%S") if isinstance(record[3], datetime) else record[3],
            "taken": record[4],
            "status": record[5],
        }
        for record in records
    ]

    return jsonify(record_list), 200

@app.route('/get_image/<path:filename>', methods=['GET'])
def get_image(filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    if not os.path.isfile(file_path):
        return "File not found", 404
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename), 200

@app.route('/fetch_schedules', methods=['GET'])
def fetch_schedules():
    Mysql = mysql.connector.connect(host="localhost", user="root", password="", database="medtrackdb")
    cursor = Mysql.cursor()

    cursor.execute("SELECT uuid, legend, label, sched FROM records WHERE taken IS NULL ORDER BY sched ASC")
    schedules = cursor.fetchall()
    
    
    schedules_list = []
    for uuid, legend, label, sched in schedules:
        cursor.execute("SELECT hour, min FROM pockets WHERE legend = %s", (legend,))
        interval = cursor.fetchone()
        hour, minute = interval[0], interval[1]
        
        # Convert interval to total minutes
        total_minutes = (hour * 60) + minute

        # Determine the grace period
        if total_minutes >= 1440:  # Once a day (24 hrs and above)
            grace_period = 3 * 60  # 3 hours in minutes
        elif total_minutes >= 720:  # Twice a day (12 hrs and above)
            grace_period = 2 * 60  # 2 hours in minutes
        elif total_minutes >= 480:  # Thrice a day (8 hrs and above)
            grace_period = 90  # 1 hour 30 minutes in minutes
        elif total_minutes >= 360:  # Every 6 hrs and above
            grace_period = 60  # 1 hour in minutes
        elif total_minutes >= 240:  # Every 4 hrs and above
            grace_period = 45  # 45 minutes
        else: # Below 4 hrs
            grace_period = 3  # 30 minutes
        
        schedules_list.append({"uuid": uuid, "legend": legend, "label":label, "sched": sched.strftime("%Y-%m-%d %H:%M:%S"), "grace": grace_period, "taken": ""})
    
    cursor.close()
    return jsonify(schedules_list), 200

@app.route('/post_schedules', methods=['POST'])
def post_schedules():
    records = request.json  # Get JSON data from ESP32

    if not records:
        return "No data to begin with!", 200

    Mysql = mysql.connector.connect(host="localhost", user="root", password="", database="medtrackdb")
    cursor = Mysql.cursor()
    check = []

    for record in records:
        if record["legend"] not in check:
            check.append(record["legend"])
        
        sched_time = datetime.strptime(record["sched"], "%Y-%m-%d %H:%M:%S")
        
        if record["taken"] != "Not Taken":
            taken_time = datetime.strptime(record["taken"], "%Y-%m-%d %H:%M:%S")
            
            # Calculate the time difference in minutes
            time_diff = (taken_time - sched_time).total_seconds() / 60

            # Determine the status
            if -15 <= time_diff <= 15:
                status = "On Time"
            elif time_diff < -30:
                status = f"Taken {abs(int(time_diff))} mins earlier"
            else:
                status = f"Taken {int(time_diff)} mins late"
        
        else:
            taken_time = datetime.strptime("1970-01-01 00:00:00", "%Y-%m-%d %H:%M:%S")
            status = "Not Taken"

        

        query = "UPDATE records SET label = %s, legend = %s, sched = %s, taken = %s, status = %s WHERE uuid = %s"
        values = (record["label"], record["legend"], record["sched"], record["taken"], status, record["uuid"])
        cursor.execute(query, values)

    Mysql.commit()
    cursor.close()

    Mysql = mysql.connector.connect(host="localhost", user="root", password="", database="medtrackdb")
    cursor = Mysql.cursor()
    cursor.execute("SELECT uid, legend FROM pockets WHERE status = 'Activated'")
    pockets = cursor.fetchall()
    cursor.close()

    for pocket in pockets:
        if pocket[1] in check:
            step_schedule(pocket[0])

    socketio.emit('records_updated', True)  # Send the latest data to the newly connected client
    return "Records updated successfully!", 200

@app.route('/time', methods=['GET'])
def get_time():
    ph_tz = pytz.timezone('Asia/Manila')  # Set timezone to PH
    ph_time = datetime.now(ph_tz).strftime('%y/%m/%d,%H:%M:%S+08')
    
    return jsonify({"datetime": ph_time})

@socketio.on('connect')
def handle_connect():
    print("JS connected")

# @socketio.on('connect')
# def handle_connect():
#     print("ESP32 connected")
#     # Emit a test message right after the ESP32 connects
#     socketio.emit('message', {'text': 'Hello from server!'}, broadcast=True)

# @socketio.on('disconnect')
# def on_disconnect():
#     print("Client disconnected")

# @app.route("/send")
# def send_message():
#     data = {"message": "Hello ESP32!"}
#     print(f"Sending message: {data}")  # Debug print to check if the message is being created
#     socketio.emit("message", data)
#     return "Message sent to ESP32!"


if __name__ == "__main__":
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    # app.run(debug=True, host="0.0.0.0", port=5000)
    socketio.run(app, debug=True, host="0.0.0.0", port=5000, allow_unsafe_werkzeug=True)
    
    