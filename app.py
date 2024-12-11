from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
# from flaskext.mysql import MySQL
import psycopg2
import os

app = Flask(__name__)

# Database configuration
# app.config['MYSQL_DATABASE_USER'] = 'admin'
# app.config['MYSQL_DATABASE_PASSWORD'] = '1234'
# app.config['MYSQL_DATABASE_DB'] = 'flask-app'
# app.config['MYSQL_DATABASE_HOST'] = '127.0.0.1'

# mysql = MySQL(app,
#               prefix="my_database",
#               host="127.0.0.1",
#               user="admin",
#               password="1234",
#               db="flask-app",
#               autocommit=True)

# mysql.init_app(app)

app.secret_key = 'mysecretkey'

host = os.environ.get("POSTGRES_HOST")
user = os.environ.get("POSTGRES_USER")
password = os.environ.get("POSTGRES_PASSWORD")
dbname = os.environ.get("POSTGRES_DATABASE")

connection = psycopg2.connect(host=host, user=user, password=password, dbname=dbname)
cur = connection.cursor()

USERNAME = os.environ.get("APP_USER")
PASSWORD = os.environ.get("APP_PASSWORD")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username == USERNAME and password == PASSWORD:
            session['logged_in'] = True
            flash("Login successful!", "success")
            return redirect(url_for('index'))
        else:
            flash("Invalid username or password.", "danger")
    return render_template('login.html')


# Logout route
@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))


# Protect routes
def login_required(f):
    def wrapper(*args, **kwargs):
        if not session.get('logged_in'):
            flash("Please log in to access this page.", "danger")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper


@app.route('/')
@login_required
def index():
    # cur = mysql.get_db().cursor()
    cur = connection.cursor()

    # Fetch categories
    cur.execute("""SELECT category_name FROM "flask-app-prd".categories""")
    categories_data = cur.fetchall()
    categories = [row[0] for row in categories_data]

    # Fetch people
    cur.execute("""SELECT person_name FROM "flask-app-prd".people ORDER BY person_id""")
    people_data = cur.fetchall()
    people = [row[0] for row in people_data]

    return render_template('index.html', categories=categories, people=people)


@app.route('/transactions')
@login_required
def transactions():
    # cur = mysql.get_db().cursor()
    cur = connection.cursor()

    # Fetch transactions
    cur.execute("""
        SELECT 
            t.transaction_id,
            t.transaction_date,
            c.category_name,
            t.transaction_description,
            t.transaction_total_amount,
            t.gian_paid_amount,
            t.nati_paid_amount,
            t.gian_responsible_amount,
            t.nati_responsible_amount
        FROM "flask-app-prd".transactions t
        LEFT JOIN "flask-app-prd".categories c ON t.category_id = c.category_id
        ORDER BY t.transaction_date DESC
    """)
    transactions = cur.fetchall()

    return render_template('transactions.html', transactions=transactions)



@app.route('/add_transaction', methods=['POST'])
@login_required
def add_transaction():
    # cur = mysql.get_db().cursor()
    cur = connection.cursor()

    date = request.form['date']
    category_name = request.form['category_name']
    description = request.form['description']
    total_amount = float(request.form['total_amount'])

    # Get category_id
    cur.execute("""SELECT category_id FROM "flask-app-prd".categories WHERE category_name = %s""", (category_name,))
    category_id = cur.fetchone()[0]

    # Get people
    cur.execute("""SELECT person_id, person_name FROM "flask-app-prd".people ORDER BY person_id""")
    people_data = cur.fetchall()
    if len(people_data) != 2:
        flash("This example assumes exactly two people in the DB.", "danger")
        return redirect(url_for('index'))

    primary_payer_name = request.form['primary_payer']
    custom_payment_split = request.form['custom_payment_split']  # 'yes' or 'no'
    responsibility_option = request.form['responsibility_option']

    gian_id, gian_name = people_data[0]
    nati_id, nati_name = people_data[1]

    # Determine paid amounts
    if custom_payment_split == 'no':
        gian_paid = total_amount if gian_name == primary_payer_name else 0
        nati_paid = total_amount if nati_name == primary_payer_name else 0
    else:
        gian_paid = float(request.form.get(f'paid_amount_{gian_name}', 0))
        nati_paid = float(request.form.get(f'paid_amount_{nati_name}', 0))
        if round(gian_paid + nati_paid, 2) != round(total_amount, 2):
            flash("The total paid amounts do not match the total transaction amount.", "danger")
            return redirect(url_for('index'))

    # Determine responsible amounts
    if responsibility_option == 'equal':
        half = total_amount / 2
        gian_responsible = half
        nati_responsible = half
    elif responsibility_option == 'single':
        single_responsible_person = request.form['single_responsible_person']
        gian_responsible = total_amount if single_responsible_person == gian_name else 0
        nati_responsible = total_amount if single_responsible_person == nati_name else 0
    elif responsibility_option == 'custom':
        gian_responsible = float(request.form.get(f'responsible_amount_{gian_name}', 0))
        nati_responsible = float(request.form.get(f'responsible_amount_{nati_name}', 0))
        if round(gian_responsible + nati_responsible, 2) != round(total_amount, 2):
            flash("The total responsible amounts do not match the total transaction amount.", "danger")
            return redirect(url_for('index'))

    # Insert
    cur.execute("""
        INSERT INTO "flask-app-prd".transactions 
        (transaction_date, category_id, transaction_description, transaction_total_amount,
         gian_paid_amount, nati_paid_amount, 
         gian_responsible_amount, nati_responsible_amount)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, (date, category_id, description, total_amount,
          gian_paid, nati_paid,
          gian_responsible, nati_responsible))

    # mysql.get_db().commit()
    flash('Transaction added successfully!', 'success')
    return redirect(url_for('index'))


@app.route('/edit_transaction/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_transaction(id):
    # cur = mysql.get_db().cursor()
    cur = connection.cursor()
    cur.execute("""SELECT person_id, person_name FROM "flask-app-prd".people ORDER BY person_id""")
    people_data = cur.fetchall()
    if len(people_data) != 2:
        flash("This example assumes exactly two people.", "danger")
        return redirect(url_for('index'))

    gian_id, gian_name = people_data[0]
    nati_id, nati_name = people_data[1]

    if request.method == 'POST':
        date = request.form['date']
        category = request.form['category']
        description = request.form['description']
        amount = float(request.form['amount'])

        cur.execute("""SELECT category_id FROM "flask-app-prd".categories WHERE category_name = %s""", (category,))
        category_id = cur.fetchone()[0]

        primary_payer_name = request.form['primary_payer']
        custom_payment_split = request.form['custom_payment_split']
        responsibility_option = request.form['responsibility_option']

        # Determine paid amounts
        if custom_payment_split == 'no':
            gian_paid = amount if gian_name == primary_payer_name else 0
            nati_paid = amount if nati_name == primary_payer_name else 0
        else:
            gian_paid = float(request.form.get(f'paid_amount_{gian_name}', 0))
            nati_paid = float(request.form.get(f'paid_amount_{nati_name}', 0))
            if round(gian_paid + nati_paid, 2) != round(amount, 2):
                flash("The total paid amounts do not match the total transaction amount.", "danger")
                return redirect(url_for('edit_transaction', id=id))

        # Responsibility
        if responsibility_option == 'equal':
            half = amount / 2
            gian_responsible = half
            nati_responsible = half
        elif responsibility_option == 'single':
            single_responsible_person = request.form['single_responsible_person']
            gian_responsible = amount if single_responsible_person == gian_name else 0
            nati_responsible = amount if single_responsible_person == nati_name else 0
        elif responsibility_option == 'custom':
            gian_responsible = float(request.form.get(f'responsible_amount_{gian_name}', 0))
            nati_responsible = float(request.form.get(f'responsible_amount_{nati_name}', 0))
            if round(gian_responsible + nati_responsible, 2) != round(amount, 2):
                flash("The total responsible amounts do not match the total transaction amount.", "danger")
                return redirect(url_for('edit_transaction', id=id))

        cur.execute("""
            UPDATE "flask-app-prd".transactions
            SET transaction_date = %s,
                category_id = %s,
                transaction_description = %s,
                transaction_total_amount = %s,
                gian_paid_amount = %s,
                nati_paid_amount = %s,
                gian_responsible_amount = %s,
                nati_responsible_amount = %s
            WHERE transaction_id = %s
        """, (date, category_id, description, amount,
              gian_paid, nati_paid,
              gian_responsible, nati_responsible,
              id))
        # mysql.get_db().commit()

        flash('Transaction updated successfully!', 'success')
        return redirect(url_for('index'))
    else:
        cur.execute("""
            SELECT 
                t.transaction_id,
                t.transaction_date,
                c.category_name,
                t.transaction_description,
                t.transaction_total_amount,
                t.gian_paid_amount,
                t.nati_paid_amount,
                t.gian_responsible_amount,
                t.nati_responsible_amount
            FROM "flask-app-prd".transactions t
            LEFT JOIN "flask-app-prd".categories c ON t.category_id = c.category_id
            WHERE t.transaction_id = %s
        """, (id,))
        row = cur.fetchone()
        if not row:
            flash("Transaction not found", "danger")
            return redirect(url_for('index'))

        transaction = {
            'transaction_id': row[0],
            'transaction_date': row[1].strftime('%Y-%m-%d'),
            'category_name': row[2],
            'transaction_description': row[3],
            'transaction_total_amount': float(row[4]),
            'gian_paid_amount': float(row[5]),
            'nati_paid_amount': float(row[6]),
            'gian_responsible_amount': float(row[7]),
            'nati_responsible_amount': float(row[8])
        }

        amount = transaction['transaction_total_amount']

        # Determine primary_payer and custom_payment_split
        if (transaction['gian_paid_amount'] == amount and transaction['nati_paid_amount'] == 0):
            primary_payer = gian_name
            custom_payment_split = 'no'
        elif (transaction['nati_paid_amount'] == amount and transaction['gian_paid_amount'] == 0):
            primary_payer = nati_name
            custom_payment_split = 'no'
        else:
            custom_payment_split = 'yes'
            primary_payer = gian_name if transaction['gian_paid_amount'] >= transaction['nati_paid_amount'] else nati_name

        # Responsibility
        gian_res = transaction['gian_responsible_amount']
        nati_res = transaction['nati_responsible_amount']

        if round(gian_res,2) == round(nati_res,2) == round(amount/2,2):
            responsibility_option = 'equal'
            single_responsible_person = None
        elif gian_res == amount and nati_res == 0:
            responsibility_option = 'single'
            single_responsible_person = gian_name
        elif nati_res == amount and gian_res == 0:
            responsibility_option = 'single'
            single_responsible_person = nati_name
        else:
            responsibility_option = 'custom'
            single_responsible_person = None

        cur.execute("""SELECT category_name FROM "flask-app-prd".categories""")
        categories_data = cur.fetchall()
        categories = [row[0] for row in categories_data]

        cur.execute("""SELECT person_name FROM "flask-app-prd".people ORDER BY person_id""")
        p_data = cur.fetchall()
        people = [r[0] for r in p_data]

        return render_template('edit_transaction.html',
                               transaction=transaction,
                               categories=categories,
                               people=people,
                               primary_payer=primary_payer,
                               custom_payment_split=custom_payment_split,
                               responsibility_option=responsibility_option,
                               single_responsible_person=single_responsible_person)


@app.route('/delete_transaction/<int:id>')
@login_required
def delete_transaction(id):
    # cur = mysql.get_db().cursor()
    cur = connection.cursor()
    cur.execute("""DELETE FROM "flask-app-prd".transactions WHERE transaction_id = %s""", (id,))
    # mysql.get_db().commit()
    flash('Transaction deleted successfully')
    return redirect(url_for('index'))


@app.route('/statistics', methods=['GET', 'POST'])
@login_required
def statistics():
    # cur = mysql.get_db().cursor()
    cur = connection.cursor()

    # Get filters
    year = request.args.get('year', '').strip()
    category = request.args.get('category', '').strip()

    # Prepare WHERE clauses for each query
    conditions = []
    params = []
    if year:
        conditions.append("YEAR(transaction_date) = %s")
        params.append(year)
    category_condition = ""
    category_params = []
    if category:
        category_condition = " AND c.category_name = %s"
        category_params.append(category)

    where_clause = " AND ".join(conditions)
    if where_clause:
        where_clause = "WHERE " + where_clause

    # Query 1: Monthly Total Expenditure with Gian/Nati breakdown
    query_monthly_total = f"""
        SELECT DATE_FORMAT(transaction_date, '%Y-%m') AS month,
               SUM(transaction_total_amount) AS total,
               SUM(gian_paid_amount) AS gian_expense,
               SUM(nati_paid_amount) AS nati_expense
        FROM "flask-app-prd".transactions
        {where_clause}
        GROUP BY month
        ORDER BY month
    """
    if params:
        cur.execute(query_monthly_total, params)
    else:
        cur.execute(query_monthly_total)
    monthly_data = cur.fetchall()

    # Query 2: Monthly Total Expenditure Per Category (Pivot)
    query_monthly_category = f"""
        SELECT DATE_FORMAT(transaction_date, '%Y-%m') AS month,
               c.category_name AS category,
               SUM(transaction_total_amount) AS total
        FROM "flask-app-prd".transactions t
        LEFT JOIN "flask-app-prd".categories c ON t.category_id = c.category_id
        {where_clause}{category_condition}
        GROUP BY month, category
        ORDER BY category, month
    """
    if params:
        cur.execute(query_monthly_category, params + category_params)
    else:
        cur.execute(query_monthly_category)
    monthly_category_data = cur.fetchall()

    # Process Pivot Data
    unique_months = sorted(list({row[0] for row in monthly_category_data}))
    unique_categories = sorted(list({row[1] for row in monthly_category_data}))
    pivot_data = {cat: {month: 0 for month in unique_months} for cat in unique_categories}
    for month, category, total in monthly_category_data:
        pivot_data[category][month] = total

    # Add Monthly Change (Percentage) for Total Expenditure
    monthly_data_with_change = []
    for i, row in enumerate(monthly_data):
        if i == 0:
            monthly_data_with_change.append(row + (None,))  # No previous month for the first row
        else:
            prev_total = monthly_data[i - 1][1]
            change = ((row[1] - prev_total) / prev_total * 100) if prev_total else None
            monthly_data_with_change.append(row + (change,))

    # Calculate the monthly percentage change for each category
    monthly_change_pivot = {cat: {month: None for month in unique_months} for cat in unique_categories}

    for category in unique_categories:
        previous_month = None
        for month in unique_months:
            current_value = pivot_data[category][month]
            if previous_month is not None:
                previous_value = pivot_data[category][previous_month]
                if previous_value > 0:
                    change = ((current_value - previous_value) / previous_value) * 100
                else:
                    change = None
                monthly_change_pivot[category][month] = change
            previous_month = month

    # Calculate total expenditure across all categories for the pie chart
    total_expenditure = sum(
        sum(month_data.values()) for month_data in pivot_data.values()
    )

    # Calculate percentage breakdown for each category
    category_percentages = {
        category: (
            sum(month_data.values()) / total_expenditure * 100
            if total_expenditure > 0 else 0
        )
        for category, month_data in pivot_data.items()
    }

    # Render the data to the template
    return render_template(
        'statistics.html',
        monthly_data=monthly_data_with_change,
        unique_months=unique_months,
        unique_categories=unique_categories,
        pivot_data=pivot_data,
        monthly_change_pivot=monthly_change_pivot,
        year=year,
        category=category,
        category_percentages=category_percentages,  # For the pie chart
    )



@app.route('/categories')
@login_required
def categories():
    # cur = mysql.get_db().cursor()
    cur = connection.cursor()
    cur.execute("""SELECT category_id, category_name FROM "flask-app-prd".categories""")
    data = cur.fetchall()
    return render_template('categories.html', categories=data)


@app.route('/add_category', methods=['GET', 'POST'])
@login_required
def add_category():
    if request.method == 'POST':
        name = request.form['name']
        # cur = mysql.get_db().cursor()
        cur = connection.cursor()
        cur.execute("""INSERT INTO "flask-app-prd".categories (category_name) VALUES (%s)""", (name,))
        # mysql.get_db().commit()
        flash('Category added successfully')
        return redirect(url_for('categories'))
    else:
        return render_template('add_category.html')


@app.route('/edit_category/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_category(id):
    # cur = mysql.get_db().cursor()
    cur = connection.cursor()
    if request.method == 'POST':
        name = request.form['name']
        cur.execute("""
            UPDATE "flask-app-prd".categories
            SET category_name = %s
            WHERE category_id = %s
        """, (name, id))
        mysql.get_db().commit()
        flash('Category updated successfully')
        return redirect(url_for('categories'))
    else:
        cur.execute("""SELECT * FROM "flask-app-prd".categories WHERE category_id = %s""", (id,))
        data = cur.fetchone()
        return render_template('edit_category.html', category=data)


@app.route('/delete_category/<int:id>')
@login_required
def delete_category(id):
    # cur = mysql.get_db().cursor()
    cur = connection.cursor()
    cur.execute("""DELETE FROM "flask-app-prd".categories WHERE category_id = %s""", (id,))
    mysql.get_db().commit()
    flash('Category deleted successfully')
    return redirect(url_for('categories'))


@app.route('/get_categories')
@login_required
def get_categories():
    # cur = mysql.get_db().cursor()
    cur = connection.cursor()
    cur.execute("""SELECT category_name FROM "flask-app-prd".categories""")
    data = cur.fetchall()
    categories = [row[0] for row in data]
    return jsonify(categories)


if __name__ == '__main__':
    # port = os.environ.get("PORT", 5000)
    # app.run(debug=False, host="0.0.0.0", port=port)
    app.run(debug=True)
