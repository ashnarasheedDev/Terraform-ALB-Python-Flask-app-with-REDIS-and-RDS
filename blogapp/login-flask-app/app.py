from flask import Flask, render_template, request, redirect, url_for, session
import mysql.connector
from redis import Redis
import os 
app = Flask(__name__)

# Set the secret key to enable sessions
app.secret_key = 'mysecretkey'

# Connect to Redis
redis = Redis(host='172.31.40.206', port=6379)

# Use Redis to store sessions
app.config['SESSION_TYPE'] = 'redis'
app.config['SESSION_REDIS'] = redis

# Connect to MySQL
db = mysql.connector.connect(
    host="172.31.40.206",
    user="root",
    password="mysqlroot123",
    database="flaskapp"
)

# Create a cursor object to execute queries
cursor = db.cursor()

@app.route('/', methods=['GET', 'POST'])
def login():
    # If the user is already logged in, redirect to the "Hello, World!" page
    if 'username' in session:
        return redirect(url_for('hello_world'))

    error = None
    if request.method == 'POST':
        # Check if the provided username is in the database
        username = request.form['username']
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        if user:
            # If the username is valid, store it in the session and redirect to the "Hello, World!" page
            session['username'] = user[1]
            return redirect(url_for('hello_world'))
        else:
            # If the username is invalid, display an error message
            error = 'Invalid username'

    # Render the login template
    return render_template('login.html', error=error,hostname=hostname)

@app.route('/hello_world')
def hello_world():
    # If the user is not logged in, redirect to the login page
    if 'username' not in session:
        return redirect(url_for('login'))

    # Get the username from the session
    name = session['username']

    # Display a "Hello, World!" message
    return render_template('hello_world.html', name=name,hostname=hostname)

@app.route('/logout', methods=['POST'])
def logout():
    # Remove the username from the session
    session.pop('username', None)
    # Redirect to the login page
    return redirect(url_for('login'))

@app.route('/health')
def health_check():
    
    db = mysql.connector.connect(
        host="172.31.40.206",
        user="root",
        password="mysqlroot123",
        database="flaskapp"
    )

    # Create a cursor object to execute queries
    cursor = db.cursor()
    
    # Check if Redis is running
    try:
        redis.ping()
        # Check if MySQL is running
        cursor.execute("SELECT 1")
        return 'OK', 200
    except:
        return 'Service is not available', 500

if __name__ == '__main__':
    hostname = os.getenv('HOSTNAME',None)
    app.run(debug=True,host="0.0.0.0",port=8080)
