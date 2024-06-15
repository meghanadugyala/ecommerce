# app.py
from flask import Flask, render_template, request, redirect, url_for, session
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
import re
import config

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with your actual secret key

db_config = config.db_config

def get_db_connection():
    return mysql.connector.connect(**db_config)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT id, password FROM users WHERE username = %s', (username,))
            user = cursor.fetchone()
            if user and check_password_hash(user[1], password):
                session['user_id'] = user[0]
                session['username'] = username
                return redirect(url_for('products'))
            else:
                return render_template('login.html', error='Invalid credentials')
        except mysql.connector.Error as err:
            print(err)
        finally:
            cursor.close()
            conn.close()
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            return render_template('register.html', error="Passwords do not match")
        if len(password) < 6:
            return render_template('register.html', error="Password must be at least 6 characters long")
        if not re.search(r'\d', password):
            return render_template('register.html', error="Password must contain at least one number")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            return render_template('register.html', error="Password must contain at least one special character")

        hashed_password = generate_password_hash(password)
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('INSERT INTO users (username, password) VALUES (%s, %s)', (username, hashed_password))
            conn.commit()
            return render_template('register.html', success="Registration successful! Please log in.")
        except mysql.connector.Error as err:
            print(err)
        finally:
            cursor.close()
            conn.close()
    return render_template('register.html')

@app.route('/products')
def products():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, name, description, price, image_url FROM products')
        products = cursor.fetchall()
    except mysql.connector.Error as err:
        print(err)
        products = []
    finally:
        cursor.close()
        conn.close()
    
    return render_template('products.html', products=products, username=session['username'])

@app.route('/add_to_cart/<int:product_id>')
def add_to_cart(product_id):
    if 'cart' not in session:
        session['cart'] = []
    session['cart'].append(product_id)
    session.modified = True  # Ensure the session is saved after modification
    return redirect(url_for('products'))

@app.route('/cart')
def cart():
    if 'username' not in session:
        return redirect(url_for('login'))

    if 'cart' not in session:
        session['cart'] = []

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        if session['cart']:
            format_strings = ','.join(['%s'] * len(session['cart']))
            cursor.execute(f'SELECT id, name, description, price, image_url FROM products WHERE id IN ({format_strings})', tuple(session['cart']))
            products = cursor.fetchall()
            total_price = sum(product[3] for product in products)
        else:
            products = []
            total_price = 0.0
    except mysql.connector.Error as err:
        print(err)
        products = []
        total_price = 0.0
    finally:
        cursor.close()
        conn.close()

    return render_template('cart.html', products=products, total_price=total_price, username=session['username'])

@app.route('/checkout')
def checkout():
    if 'username' not in session:
        return redirect(url_for('login'))

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        product_ids = ','.join(map(str, session['cart']))
        total_price = request.args.get('total_price', 0.0)
        cursor.execute('INSERT INTO orders (user_id, product_ids, total_price) VALUES (%s, %s, %s)', (session['user_id'], product_ids, total_price))
        conn.commit()
        session.pop('cart', None)
        session.modified = True  # Ensure the session is marked as modified
        return render_template('order_confirmation.html', username=session['username'])
    except mysql.connector.Error as err:
        print(err)
        return redirect(url_for('cart'))
    finally:
        cursor.close()
        conn.close()

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
