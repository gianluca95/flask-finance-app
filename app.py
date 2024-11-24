from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flaskext.mysql import MySQL
import os

app = Flask(__name__)

# Database configuration
app.config['MYSQL_DATABASE_USER'] = 'admin'
app.config['MYSQL_DATABASE_PASSWORD'] = '1234'
app.config['MYSQL_DATABASE_DB'] = 'flask-app'
app.config['MYSQL_DATABASE_HOST'] = '127.0.0.1'
mysql = MySQL(app,
                 prefix="my_database",
                 host="127.0.0.1",
                 user="admin",
                 password="1234",
                 db="flask-app",
                 autocommit=True)
mysql.init_app(app)

app.secret_key = 'mysecretkey'

# Main route showing transactions
@app.route('/')
def index():
    cur = mysql.get_db().cursor()
    # Fetch transactions
    cur.execute('SELECT * FROM transactions')
    transactions = cur.fetchall()
    # Fetch categories
    cur.execute('SELECT name FROM categories')
    categories_data = cur.fetchall()
    categories = [row[0] for row in categories_data]
    return render_template('index.html', transactions=transactions, categories=categories)

# Route to add a new transaction
@app.route('/add_transaction', methods=['POST'])
def add_transaction():
    if request.method == 'POST':
        description = request.form['description']
        category = request.form['category']
        amount = request.form['amount']
        date = request.form['date']

        cur = mysql.get_db().cursor()
        # Optionally, you can check if the category exists in the categories table
        cur.execute('SELECT category_id FROM categories WHERE name = %s', (category,))
        category_data = cur.fetchone()
        if category_data:
            category_id = category_data[0]
        else:
            # If category doesn't exist, you can choose to add it automatically or return an error
            cur.execute('INSERT INTO categories (name) VALUES (%s)', (category,))
            mysql.get_db().commit()
            category_id = cur.lastrowid

        # Insert the transaction with the category name
        cur.execute('INSERT INTO transactions (description, category, amount, date) VALUES (%s, %s, %s, %s)',
                    (description, category, amount, date))
        mysql.get_db().commit()
        flash('Transaction added successfully')
        return redirect(url_for('index'))

# Route to edit a transaction
@app.route('/edit_transaction/<int:id>', methods=['GET', 'POST'])
def edit_transaction(id):
    cur = mysql.get_db().cursor()
    if request.method == 'POST':
        description = request.form['description']
        category = request.form['category']
        amount = request.form['amount']
        date = request.form['date']

        cur.execute("""
            UPDATE transactions
            SET description = %s,
                category = %s,
                amount = %s,
                date = %s
            WHERE transaction_id = %s
        """, (description, category, amount, date, id))
        mysql.get_db().commit()
        flash('Transaction updated successfully')
        return redirect(url_for('index'))
    else:
        cur.execute("SELECT * FROM transactions WHERE transaction_id = %s", (id,))
        transaction = cur.fetchone()
        # Fetch categories
        cur.execute('SELECT name FROM categories')
        categories_data = cur.fetchall()
        categories = [row[0] for row in categories_data]
        return render_template('edit_transaction.html', transaction=transaction, categories=categories)

# Route to delete a transaction
@app.route('/delete_transaction/<int:id>')
def delete_transaction(id):
    cur = mysql.get_db().cursor()
    cur.execute("DELETE FROM transactions WHERE transaction_id = %s", (id,))
    mysql.get_db().commit()
    flash('Transaction deleted successfully')
    return redirect(url_for('index'))

# Route for Statistics
@app.route('/statistics')
def statistics():
    cur = mysql.get_db().cursor()
    # Query to get total amount spent per category
    cur.execute("""
        SELECT category, SUM(amount)
        FROM transactions
        GROUP BY category
    """)
    data = cur.fetchall()
    # Prepare data for the chart
    categories = [row[0] for row in data]
    amounts = [float(row[1]) for row in data]
    return render_template('statistics.html', categories=categories, amounts=amounts)

# Routes to manage categories
@app.route('/categories')
def categories():
    cur = mysql.get_db().cursor()
    cur.execute('SELECT * FROM categories')
    data = cur.fetchall()
    return render_template('categories.html', categories=data)

@app.route('/add_category', methods=['GET', 'POST'])
def add_category():
    if request.method == 'POST':
        name = request.form['name']
        cur = mysql.get_db().cursor()
        cur.execute('INSERT INTO categories (name) VALUES (%s)', (name,))
        mysql.get_db().commit()
        flash('Category added successfully')
        return redirect(url_for('categories'))
    else:
        return render_template('add_category.html')

@app.route('/edit_category/<int:id>', methods=['GET', 'POST'])
def edit_category(id):
    cur = mysql.get_db().cursor()
    if request.method == 'POST':
        name = request.form['name']
        cur.execute("""
            UPDATE categories
            SET name = %s
            WHERE category_id = %s
        """, (name, id))
        mysql.get_db().commit()
        flash('Category updated successfully')
        return redirect(url_for('categories'))
    else:
        cur.execute("SELECT * FROM categories WHERE category_id = %s", (id,))
        data = cur.fetchone()
        return render_template('edit_category.html', category=data)

@app.route('/delete_category/<int:id>')
def delete_category(id):
    cur = mysql.get_db().cursor()
    cur.execute("DELETE FROM categories WHERE category_id = %s", (id,))
    mysql.get_db().commit()
    flash('Category deleted successfully')
    return redirect(url_for('categories'))

# Route to get categories for autocomplete (JSON response)
@app.route('/get_categories')
def get_categories():
    cur = mysql.get_db().cursor()
    cur.execute('SELECT name FROM categories')
    data = cur.fetchall()
    categories = [row[0] for row in data]
    return jsonify(categories)

if __name__ == '__main__':
    port = os.environ.get("PORT", 5000)
    app.run(debug=False, host="0.0.0.0", port=port)
