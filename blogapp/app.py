
from flask import Flask, render_template, request, redirect, url_for, session
import mysql.connector
from redis import Redis
import configparser
import os 
import subprocess

config = configparser.ConfigParser()
config.read('config.ini')


app = Flask(__name__)

# Set the secret key to enable sessions
app.secret_key = 'mysecretkey'



def make_db_connection():
    
  db = mysql.connector.connect(
    user=mysql_user,
    password=mysql_password,
    host=mysql_host,
    database=mysql_database
  )
    
  return db

@app.route('/', methods=['GET', 'POST'])
def login():
    # If the user is already logged in, redirect to the "Hello, World!" page
    if 'username' in session:
        return redirect(url_for('home'))

    error = None
    if request.method == 'POST':
        # Check if the provided username and password are valid
        username = request.form['username']
        password = request.form['password']
        
        conn = make_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, password))
        user = cursor.fetchone()
        conn.close()
        if user:
            # If the username and password are valid, store the username in the session and redirect to the "Hello, World!" page
            session['username'] = user[1]
            return redirect(url_for('home'))
        else:
            # If the username and password are invalid, display an error message
            error = 'Invalid username or password'

    # Render the login template
    return render_template('login.html', error=error, hostname=hostname)


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    # If the user is already logged in, redirect to the home page
    if 'username' in session:
        return redirect(url_for('home'))

    error = None
    if request.method == 'POST':
        # Get the values entered in the signup form
        username = request.form['username']
        password = request.form['password']

        # Check if the username is already taken
        conn = make_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        
        

        if user:
            error = 'Username already taken'
            conn.close()
            
        else:
            # Insert the new user into the database
            cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, password))
            conn.commit()
            conn.close()
            
            
            
            # Store the username in the session and redirect to the home page
            session['username'] = username
            return redirect(url_for('home'))

    # Render the signup template
    return render_template('signup.html', error=error, hostname=hostname)




@app.route('/home')
def home():
    # If the user is not logged in, redirect to the login page
    if 'username' not in session:
        return redirect(url_for('login'))

    # Get the username from the session
    name = session['username']

    # Get the error message from the query string, if it exists
    error = request.args.get('error')

    # Fetch all blog posts from the database as a dictionary
    
    
    conn = make_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM blog_posts")
    posts = cursor.fetchall()
    conn.close()
        

    # Render the home template, passing the error message if it exists
    return render_template('home.html', hostname=hostname, name=name, posts=posts, error=error)


@app.route('/edit_blog_post/<int:blog_id>',methods=['GET', 'POST'])
def edit_blog_post(blog_id):
    # If the user is not logged in, redirect to the login page
    if 'username' not in session:
        return redirect(url_for('login'))
    
    
    conn = make_db_connection()
    cursor = conn.cursor(dictionary=True)
   
    cursor.execute("SELECT * FROM blog_posts WHERE id = %s", (blog_id,))
    blog_post = cursor.fetchone()

    # Get the user ID of the logged-in user
    cursor.execute("SELECT id FROM users WHERE username = %s", (session['username'],))
    user_id = cursor.fetchone()['id']
       
    conn.close()

    if not blog_post:
        # If the blog post does not exist, return a 404 error
        return redirect(url_for('home', error='The blog post does not exist'))

    if blog_post['author_id'] != user_id:

       return redirect(url_for('home', error='The logged in user is not the author of the blog post'))


    if request.method == 'POST':
        
        # Update the blog post with the values from the form
        title = request.form['title']
        content = request.form['content']
        cursor.execute("UPDATE blog_posts SET title = %s, content = %s WHERE id = %s", (title, content, blog_id))
        db.commit()
        return redirect(url_for('home'))
        
        
    return render_template('edit_blog_post.html', hostname=hostname, post=blog_post)









@app.route('/delete_blog_post/<int:blog_id>')
def delete_blog_post(blog_id):
    # If the user is not logged in, redirect to the login page
    if 'username' not in session:
        return redirect(url_for('login'))
    
    # Check if the blog post exists in the database
    
    conn = make_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM blog_posts WHERE id = %s", (blog_id,))
    blog_post = cursor.fetchone()

    # Get the user ID of the logged-in user
    cursor.execute("SELECT id FROM users WHERE username = %s", (session['username'],))
    user_id = cursor.fetchone()['id']
    conn.close()
    
    if not blog_post:
        # If the blog post does not exist, return a 404 error
        return redirect(url_for('home', error='The blog post does not exist'))

    # Check if the logged in user is the author of the blog post
    if blog_post['author_id'] != user_id:
        # If the logged in user is not the author of the blog post, return a 403 error
        return redirect(url_for('home', error='If the logged in user is not the author of the blog post'))

    # Delete the blog post from the database
    cursor.execute("DELETE FROM blog_posts WHERE id = %s", (blog_id,))
    db.commit()

    # Redirect the user to the home page
    return redirect(url_for('home'))



# Route to display a single blog post
@app.route('/blog')
def blog():
    # If the user is not logged in, redirect to the login page
    if 'username' not in session:
        return redirect(url_for('login'))

    name = session['username']
    # Get the blog post ID from the query parameter
    blog_id = request.args.get('id')
   
    conn = make_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM blog_posts WHERE id = %s", (blog_id,))
    # Fetch the blog post with the given ID from the database
    blog_post = cursor.fetchone()
    conn.close()
    
    
    error = None
    # If the blog post does not exist, display an error message
    if blog_post is None:
        error = 'Blog ID {} not found'.format(blog_id)
       
    return render_template('blog.html',hostname=hostname, name=name , error=error , blog_post=blog_post)


@app.route('/create_blog_post', methods=['GET', 'POST'])
def create_blog_post():
    # If the user is not logged in, redirect to the login page
    if 'username' not in session:
        return redirect(url_for('login'))
    
    name = session['username']

    # Get the user ID of the logged-in user
    
    
    conn = make_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = %s", (session['username'],))
    user_id = cursor.fetchone()[0]
    conn.close()
    
    if request.method == 'POST':
        # Get the title and content of the new blog post from the form data
        title = request.form.get('title')
        content = request.form.get('content')

        if title and content:
            # Insert the new blog post into the database
            conn = make_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO blog_posts (title, content, author_id) VALUES (%s, %s, %s)", (title, content, user_id))
            conn.commit()
            conn.close()
            
            # Redirect the user to the home page
            return redirect(url_for('home'))

        else:
            # If either the title or content field is missing, show an error message
            error_message = "Please fill in both the title and content fields."
            return render_template('create_blog_post.html',hostname=hostname, name=name ,error_message=error_message)

    # If the request is a GET request, render the create_blog_post template
    return render_template('create_blog_post.html',hostname=hostname, name=name)



@app.route('/logout', methods=['POST'])
def logout():
    # Remove the username from the session
    session.pop('username', None)
    # Redirect to the login page
    return redirect(url_for('login'))

@app.route('/health')
def health_check():
    

    
    # Check if Redis is running
    try:
        
        conn = make_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        conn.close()
    
        redis = Redis(host=redis_host,port=redis_port)
        redis.ping()

        return 'OK', 200
    except:
        return 'Service is not available', 500


if __name__ == '__main__':

    mysql_user = config.get('mysql', 'user')
    mysql_password = config.get('mysql', 'password')
    mysql_host = config.get('mysql', 'host')
    mysql_database = config.get('mysql', 'database')

    app_port = config.getint('app', 'port')
    app_debug = config.getboolean('app', 'debug')

    redis_host = config.get('redis', 'host')
    redis_port = config.getint('redis', 'port')

    
    #hostname = os.getenv('HOSTNAME')
    output = subprocess.check_output(['hostnamectl', 'hostname'])
    hostname = output.decode('utf-8')
    # Connect to MySQL database
    try:
        
        # Create a cursor object to execute queries
        conn = make_db_connection()
        cursor = conn.cursor()
        conn.close()
   
        print("Connected to MySQL database successfully")
        
    except Exception as e:
        print(f"Error connecting to MySQL database: {e}")
        
   
    # Connect to Redis database
    try:
        redis = Redis(host=redis_host,port=redis_port)
        redis.ping()
        print("Connected to Redis database successfully")
    except Exception as e:
        print(f"Error connecting to Redis database: {e}")

    app.config['SESSION_TYPE'] = 'redis'
    app.config['SESSION_REDIS'] = redis
    app.run(debug=app_debug,host="0.0.0.0",port=app_port)




