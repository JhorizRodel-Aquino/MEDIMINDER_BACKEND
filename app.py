from flask import Flask, jsonify, request, send_from_directory
import os
from werkzeug.utils import secure_filename
import uuid as uuid
from flask_cors import CORS
from datetime import datetime, timedelta
# import mysql.connector
import pymysql

app = Flask(__name__)

db_name = "u854837124_mediminder_db"
number_of_sched_ahead = 10

# Enable CORS for all routes
CORS(app, resources={r"/*": {"origins": "http://127.0.0.1:5501"}})

# Configure MySQL connection
app.config['MYSQL_HOST'] = "srv1668.hstgr.io"
app.config['MYSQL_USER'] = "u854837124_mediminder"  
app.config['MYSQL_PASSWORD'] = "mediMinder457!"
app.config['MYSQL_DB'] = "u854837124_mediminder_db"

mysql = pymysql.connect(
    host=app.config['MYSQL_HOST'],
    user=app.config['MYSQL_USER'],
    password=app.config['MYSQL_PASSWORD'],
    database=app.config['MYSQL_DB'],
)

# Configure upload folder and allowed file types
app.config['UPLOAD_FOLDER'] = 'C:/Users/aquin/Downloads/MEDIMINDER - BACKEND/uploads'

# mysql = mysql.connector.connect(host="mediminder457.mysql.pythonanywhere-services.com", user="mediminder457", password="mediMINDERmySQLdb!!", database="u854837124_mediminder_db")
# mysql = mysql.connector.connect(host="srv1668.hstgr.io", user="u854837124_mediminder", password="mediMinder457!", database="u854837124_mediminder_db")
# mysql = mysql.connector.connect(host="localhost", user="root", password="", database="medtrackerdb")


def strip_seconds():
    mysql = pymysql.connect(
        host=app.config['MYSQL_HOST'],
        user=app.config['MYSQL_USER'],
        password=app.config['MYSQL_PASSWORD'],
        database=app.config['MYSQL_DB']
    )
    cursor = mysql.cursor()

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

    mysql.commit()
    cursor.close()
    mysql.close()

def initialize_database():
    """Ensure the database and table exist."""
    mysql = pymysql.connect(
        host=app.config['MYSQL_HOST'],
        user=app.config['MYSQL_USER'],
        password=app.config['MYSQL_PASSWORD'],
        database=app.config['MYSQL_DB']
    )
    cursor = mysql.cursor()

    try:
        # Ensure database exists
        cursor.execute("CREATE DATABASE IF NOT EXISTS u854837124_mediminder_db")
        print("Database 'u854837124_mediminder_db' ensured.")

        # Use the 'u854837124_mediminder_db' database
        cursor.execute("USE u854837124_mediminder_db")

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
        mysql.commit()
        print("Table 'users' ensured.")

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS pockets (
                uid INT AUTO_INCREMENT PRIMARY KEY,
                id INT,
                legend VARCHAR(1),
                label VARCHAR(50),
                start DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                hour INT NOT NULL DEFAULT 0,
                min INT NOT NULL DEFAULT 0,
                status VARCHAR(20) NOT NULL DEFAULT 'Deactivated',
                FOREIGN KEY (id) REFERENCES users(id)
            )
            """
        )
        mysql.commit()
        print("Table 'pockets' ensured.")

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS records (
                uuid INT AUTO_INCREMENT PRIMARY KEY,
                uid INT,
                label VARCHAR(50),
                sched DATETIME,
                taken DATETIME,
                status VARCHAR(100),
                FOREIGN KEY (uid) REFERENCES pockets(uid)
            )
            """
        )
        mysql.commit()
        print("Table 'records' ensured.")

    except Exception as e:
        print(f"Error during database initialization: {e}")
    finally:
        cursor.close()
        mysql.close()


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
@app.route('/show_databases')
def show_databases():
    mysql = pymysql.connect(
        host=app.config['MYSQL_HOST'],
        user=app.config['MYSQL_USER'],
        password=app.config['MYSQL_PASSWORD'],
        database=app.config['MYSQL_DB']
    )
    cursor = mysql.cursor()

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
        mysql.close()

@app.route('/show_tables')
def show_tables():
    mysql = pymysql.connect(
        host=app.config['MYSQL_HOST'],
        user=app.config['MYSQL_USER'],
        password=app.config['MYSQL_PASSWORD'],
        database=app.config['MYSQL_DB']
    )
    cursor = mysql.cursor()

    try:
        cursor.execute("USE u854837124_mediminder_db")
        cursor.execute("SHOW TABLES")
        tables = [table[0] for table in cursor.fetchall()]  # Fetch all tables
        return jsonify(tables)
    except Exception as e:
        return f"Error fetching tables: {e}"
    finally:
        cursor.close()
        mysql.close()

@app.route('/')
def index():
    return "Hello, Flask! Database and table setup is automatic."

@app.route('/fetch_users', methods=['GET'])
def fetch_users():
    mysql = pymysql.connect(
        host=app.config['MYSQL_HOST'],
        user=app.config['MYSQL_USER'],
        password=app.config['MYSQL_PASSWORD'],
        database=app.config['MYSQL_DB']
    )
    cursor = mysql.cursor()
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
    mysql.close()
    strip_seconds()
    return jsonify(user_list)

@app.route('/create_user', methods=['POST'])
def create_user():
    name = request.form['username']
    image = request.files['user_image']

    if not name:
        return "Username is required.", 400

    img_name = save_image(image)

    mysql = pymysql.connect(
        host=app.config['MYSQL_HOST'],
        user=app.config['MYSQL_USER'],
        password=app.config['MYSQL_PASSWORD'],
        database=app.config['MYSQL_DB']
    )
    cursor = mysql.cursor()
    cursor.execute("SELECT name FROM users WHERE status = 'Active'")
    n_active = cursor.fetchone()

    if not n_active:  # if there are no active user
        status = "Active"
    else:
        status = "Inactive"

    cursor.execute("INSERT INTO users (name, img_name, status) VALUES (%s, %s, %s)", (name, img_name, status,))
    mysql.commit()

    user_id = cursor.lastrowid  # Get the ID of the last inserted user
    pocket_data = [
        (user_id, 'A', 'A'),
        (user_id, 'B', 'B'),
        (user_id, 'C', 'C'),
        (user_id, 'D', 'D'),
        (user_id, 'E', 'E'),
    ]

    cursor.executemany("INSERT INTO pockets (id, legend, label) VALUES (%s, %s, %s)", pocket_data)
    mysql.commit()
 
    cursor.close()
    mysql.close()

    return "User and Pockets created successfully!"

@app.route('/update_user/<int:id>', methods=['PATCH'])
def update_user(id):
    name = request.form['updatedUserName']
    image = request.files['updatedUserImg']

    mysql = pymysql.connect(
        host=app.config['MYSQL_HOST'],
        user=app.config['MYSQL_USER'],
        password=app.config['MYSQL_PASSWORD'],
        database=app.config['MYSQL_DB']
    )
    cursor = mysql.cursor()
    cursor.execute("SELECT name, img_name FROM users WHERE id = %s", (id,))
    user = cursor.fetchone()

    if image:
        img_name = save_image(image)
        delete_image(user[1])
    else:
        img_name = user[1]

    cursor.execute("UPDATE users SET name = %s, img_name = %s WHERE id = %s", (name, img_name, id,))
    mysql.commit()
    cursor.close()
    mysql.close()
    return "User updated successfully!"

@app.route('/delete_user/<int:id>', methods=['DELETE'])
def delete_user(id):
    mysql = pymysql.connect(
        host=app.config['MYSQL_HOST'],
        user=app.config['MYSQL_USER'],
        password=app.config['MYSQL_PASSWORD'],
        database=app.config['MYSQL_DB']
    )
    cursor = mysql.cursor()

    cursor.execute("DELETE FROM pockets WHERE id = %s", (id,))

    # Fetch the user to get the image name before deletion
    cursor.execute("SELECT img_name FROM users WHERE id = %s", (id,))
    user_img = cursor.fetchone()
    
    if user_img:
        delete_image(user_img[0])

    cursor.execute("DELETE FROM users WHERE id = %s", (id,))
    mysql.commit()
    cursor.close()
    mysql.close()
    return "User deleted successfully!"

@app.route('/set_active/<int:id>', methods=['PATCH'])
def set_active(id):
    mysql = pymysql.connect(
        host=app.config['MYSQL_HOST'],
        user=app.config['MYSQL_USER'],
        password=app.config['MYSQL_PASSWORD'],
        database=app.config['MYSQL_DB']
    )
    cursor = mysql.cursor()
    cursor.execute("SELECT id FROM users WHERE status = 'Active' AND id != %s", (id,))
    active_ID = cursor.fetchone()

    if active_ID:
        cursor.execute("UPDATE users SET status = 'Inactive' WHERE id = %s", (active_ID[0],))
        cursor.execute("UPDATE pockets SET status = 'Deactivated' WHERE id = %s", (active_ID[0],))
        cursor.execute("UPDATE users SET status = 'Active' WHERE id = %s", (id,))
        mysql.commit()
        cursor.close()
        mysql.close()
        return "User updated successfully!"
    
    return "Failed to update user!", 400

@app.route('/fetch_pockets/<int:id>', methods=['GET'])
def fetch_pockets(id):
    mysql = pymysql.connect(
        host=app.config['MYSQL_HOST'],
        user=app.config['MYSQL_USER'],
        password=app.config['MYSQL_PASSWORD'],
        database=app.config['MYSQL_DB']
    )
    cursor = mysql.cursor()
    cursor.execute("SELECT uid, legend, label, start, hour, min, status FROM pockets WHERE id = %s", (id,))
    pockets = cursor.fetchall()

    if not pockets:
        return jsonify({"error": "No pockets found"}), 404  # Respond with a 404 error

    # Convert to a list of dictionaries
    columns = ["uid", "legend", "label", "start", "hour", "min", "status"]
    pocket_list = []
    for row in pockets:
        pocket_data = dict(zip(columns, row))
        pocket_data["start"] = pocket_data["start"].strftime('%Y-%m-%d %H:%M')  # Format datetime
        
        pocket_list.append(pocket_data)

    cursor.close()
    mysql.close()
    return jsonify(pocket_list)

@app.route('/rename_label/<int:uid>', methods=['PATCH'])
def rename_label(uid):
    label = request.form['renameLabel']

    mysql = pymysql.connect(
        host=app.config['MYSQL_HOST'],
        user=app.config['MYSQL_USER'],
        password=app.config['MYSQL_PASSWORD'],
        database=app.config['MYSQL_DB']
    )
    cursor = mysql.cursor()
    cursor.execute("SELECT label FROM pockets WHERE uid = %s", (uid,))
    labelQuery = cursor.fetchone()[0]

    cursor.execute("UPDATE pockets SET label = %s WHERE uid = %s", (label, uid,))

    if labelQuery.upper() != label.upper():
        deactivate_sched(uid)
  
    mysql.commit() 
    cursor.close()
    mysql.close()

    return "Label renamed successfully!"

@app.route('/set_sched/<int:uid>', methods=['PATCH'])
def set_sched(uid):
    date = request.form['setDate']
    time = request.form['setTime']
    step_hour = abs(int(request.form['setHour']))
    step_min = abs(int(request.form['setMin']))

    start = " ".join([date, time])

    mysql = pymysql.connect(
        host=app.config['MYSQL_HOST'],
        user=app.config['MYSQL_USER'],
        password=app.config['MYSQL_PASSWORD'],
        database=app.config['MYSQL_DB']
    )
    cursor = mysql.cursor()
    cursor.execute("SELECT start, hour, min FROM pockets WHERE uid = %s", (uid,))
    oldQuery = cursor.fetchone()
    
    cursor.execute("UPDATE pockets SET start = %s, hour = %s, min = %s WHERE uid = %s", (start, step_hour, step_min, uid,))
    cursor.execute("SELECT start, hour, min FROM pockets WHERE uid = %s", (uid,))
    newQuery = cursor.fetchone()

    if oldQuery != newQuery:
        deactivate_sched(uid)
    
    mysql.commit() 
    cursor.close()
    mysql.close()

    return "Label renamed successfully!"

@app.route('/toggle_sched/<int:uid>/<int:stat>', methods=['PATCH'])
def toggle_sched(uid, stat):
    if stat == 1:
        activate_sched(uid)
    else: 
        deactivate_sched(uid)
    
    return "Schedule activated/deactivated successfully!"

def activate_sched(uid):
    mysql = pymysql.connect(
        host=app.config['MYSQL_HOST'],
        user=app.config['MYSQL_USER'],
        password=app.config['MYSQL_PASSWORD'],
        database=app.config['MYSQL_DB']
    )
    cursor = mysql.cursor()
    cursor.execute("UPDATE pockets SET status = 'Activated' WHERE uid = %s", (uid,))
    mysql.commit()
    cursor.close() 
    mysql.close()

def deactivate_sched(uid):
    mysql = pymysql.connect(
        host=app.config['MYSQL_HOST'],
        user=app.config['MYSQL_USER'],
        password=app.config['MYSQL_PASSWORD'],
        database=app.config['MYSQL_DB']
    )
    cursor = mysql.cursor()
    cursor.execute("UPDATE pockets SET status = 'Deactivated' WHERE uid = %s", (uid,))
    mysql.commit()
    cursor.close()
    mysql.close()

def create_schedule(uid):
    mysql = pymysql.connect(
        host=app.config['MYSQL_HOST'],
        user=app.config['MYSQL_USER'],
        password=app.config['MYSQL_PASSWORD'],
        database=app.config['MYSQL_DB']
    )
    cursor = mysql.cursor()

    cursor.execute("SELECT label, start FROM pockets WHERE uid = %s", (uid,))
    pocket_data = cursor.fetchone()
    label, new_sched = pocket_data

    cursor.execute("SELECT label, sched FROM records WHERE uid = %s", (uid,))
    sched_data = cursor.fetchall()
    
    

    if len(sched_data) < 1:
        cursor.execute("INSERT INTO records (uid, label, sched) VALUES (%s, %s, %s)", (uid, label, new_sched))
        mysql.commit()
        return "Inserted a new schedule"

    
    if pocket_data !=  sched_data[-1]:
        cursor.execute("INSERT INTO records (uid, label, sched) VALUES (%s, %s, %s)", (uid, label, new_sched))
        mysql.commit()
        return "Inserted a new schedule"
    
    cursor.close()
    mysql.close()
    return "Same as the last schedule"
    
def step_schedule(uid):
    mysql = pymysql.connect(
        host=app.config['MYSQL_HOST'],
        user=app.config['MYSQL_USER'],
        password=app.config['MYSQL_PASSWORD'],
        database=app.config['MYSQL_DB']
    )
    cursor = mysql.cursor()
    
    # Fetch the step hour and minute for the given user ID (uid)
    cursor.execute("SELECT hour, min FROM pockets WHERE uid = %s", (uid,))
    result = cursor.fetchone()
    
    if not result:
        raise ValueError(f"No step data found for UID {uid}")
    
    step_hour, step_min = result
    step_sched = timedelta(hours=step_hour, minutes=step_min)

    # Fetch the latest schedule from the records
    cursor.execute("SELECT label, sched FROM records WHERE uid = %s ORDER BY sched DESC LIMIT 1", (uid,))
    latest_record = cursor.fetchone()

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
        sched = (uid, label, last_sched.strftime("%Y-%m-%d %H:%M:%S"))
        new_schedules.append(sched)

    cursor.executemany("INSERT INTO records (uid, label, sched) VALUES (%s, %s, %s)", new_schedules)
    mysql.commit()
    cursor.close()  
    mysql.close()

    return "Successfully added new schedules"  
    
def remove_null_schedule(uid):
    mysql = pymysql.connect(
        host=app.config['MYSQL_HOST'],
        user=app.config['MYSQL_USER'],
        password=app.config['MYSQL_PASSWORD'],
        database=app.config['MYSQL_DB']
    )
    cursor = mysql.cursor()
    
    # Select records with 'taken' IS NULL for the given user ID
    cursor.execute("SELECT * FROM records WHERE taken IS NULL AND uid = %s", (uid,))
    null_records = cursor.fetchall()

    if not null_records:
        cursor.close()
        mysql.close()
        return f"No records with NULL 'taken' found for UID {uid}."

    # Delete the records with 'taken' IS NULL for the user
    cursor.execute("DELETE FROM records WHERE taken IS NULL AND uid = %s", (uid,))
    mysql.commit()
    cursor.close()
    mysql.close()

    return f"Deleted {cursor.rowcount} records with NULL 'taken' for UID {uid}."

@app.route('/fetch_records/<int:uid>', methods=['GET'])
def fetch_records(uid):
    mysql = pymysql.connect(
        host=app.config['MYSQL_HOST'],
        user=app.config['MYSQL_USER'],
        password=app.config['MYSQL_PASSWORD'],
        database=app.config['MYSQL_DB']
    )
    cursor = mysql.cursor()
    
    cursor.execute("SELECT status FROM pockets WHERE uid = %s", (uid,))
    pocket_status = cursor.fetchone()[0]

    if pocket_status == "Activated":
        create_schedule(uid)
        step_schedule(uid) 
    else:
        remove_null_schedule(uid)
        
    # Fetch records for the given UID
    cursor.execute("SELECT uuid, uid, label, sched, taken, status FROM records WHERE uid = %s", (uid,))
    records = cursor.fetchall()
    
    cursor.close()
    mysql.close()

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
    print(f"Looking for file: {file_path}")
    if not os.path.isfile(file_path):
        return "File not found", 404
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


if __name__ == "__main__":
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    app.run(debug=True)