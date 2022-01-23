from flask import Flask, render_template, request, redirect, url_for, flash
from flaskext.mysql import MySQL

app = Flask(__name__)

# app.config['MYSQL_DATABASE_USER'] = 'admin'
# app.config['MYSQL_DATABASE_PASSWORD'] = '1234'
# app.config['MYSQL_DATABASE_DB'] = 'flask-app'
# app.config['MYSQL_DATABASE_HOST'] = '127.0.0.1'
mysql = MySQL(app, 
              prefix = "my_database", 
              host = "127.0.0.1", 
              user = "admin", 
              password = "1234", 
              db = "flask-app", 
              autocommit = True)
mysql.init_app(app)

app.secret_key = 'mysecretkey'

@app.route('/')
def Index():
    cur = mysql.get_db().cursor()
    cur.execute('SELECT * FROM cuentas')
    data = cur.fetchall()
    return render_template('index.html', cuentas = data)

@app.route('/add_cuenta', methods = ['POST'])
def add_cuenta():
    if request.method == 'POST':
        id_cuenta = request.form['id_cuenta']
        nombre_cuenta = request.form['nombre_cuenta']
        tipo_cuenta = request.form['tipo_cuenta']
        moneda_cuenta = request.form['moneda_cuenta']
        saldo_inicial_cuenta = request.form['saldo_inicial_cuenta']
        api_cuenta = request.form['api_cuenta']

        cur = mysql.get_db().cursor()
        cur.execute('INSERT INTO cuentas (cuenta_id, cuenta_nombre, cuenta_tipo, cuenta_moneda, cuenta_saldo_inicial, cuenta_api) VALUES (%s, %s, %s, %s, %s, %s)', 
                    (id_cuenta, nombre_cuenta, tipo_cuenta, moneda_cuenta, saldo_inicial_cuenta, api_cuenta))
        # mysql.connection.commit()
        flash('Cuenta agregada satisfactoriamente')
        return redirect(url_for('Index'))

@app.route('/edit/<id>')
def get_cuenta(id):
    cur = mysql.get_db().cursor()
    cur.execute('SELECT * FROM cuentas WHERE cuenta_id = %s', (id))
    data = cur.fetchall()
    return render_template('edit_cuentas.html', cuenta = data[0])

@app.route('/update/<id>', methods = ['POST'])
def update_cuenta(id):
    if request.method == 'POST':
        id_cuenta = request.form['id_cuenta']
        nombre_cuenta = request.form['nombre_cuenta']
        tipo_cuenta = request.form['tipo_cuenta']
        moneda_cuenta = request.form['moneda_cuenta']
        saldo_inicial_cuenta = request.form['saldo_inicial_cuenta']
        api_cuenta = request.form['api_cuenta']

        cur = mysql.get_db().cursor()
        cur.execute("""
            UPDATE cuentas
            SET cuenta_id = %s,
                cuenta_nombre = %s,
                cuenta_tipo = %s,
                cuenta_moneda = %s,
                cuenta_saldo_inicial = %s,
                cuenta_api = %s
            WHERE cuenta_id = %s
        """, (id_cuenta, nombre_cuenta, tipo_cuenta, moneda_cuenta, saldo_inicial_cuenta, api_cuenta, id))
        flash('Cuenta actualizada satisfactoriamente')
        return redirect(url_for('Index'))

@app.route('/delete/<string:id>')
def delete_movement(id):
    cur = mysql.get_db().cursor()
    cur.execute("DELETE FROM cuentas WHERE cuenta_id = '%s'"%(id))
    flash('Cuenta eliminada satisfactoriamente')
    return redirect(url_for('Index'))

if __name__ == '__main__':
    app.run(port = 5000, debug = False)