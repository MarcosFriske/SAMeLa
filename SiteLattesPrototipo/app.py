#app.py
from flask import Flask, request, session, redirect, url_for, render_template, flash
import psycopg2 #pip install psycopg2 
import psycopg2.extras
import re 
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'SAMeLa'

# Dados da conexão
DB_HOST = "localhost"
DB_NAME = "valida_lattes"
DB_USER = "postgres"
DB_PASS = "admin"
 
conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
 
@app.route('/')
def home():
    # Check if user is loggedin
    if 'loggedin' in session:
    
        # User is loggedin show them the home page
        return render_template('home.html', nome_completo=session['nome_completo'].title())
    # User is not loggedin redirect to login page
    return redirect(url_for('login'))
 
@app.route('/login/', methods=['GET', 'POST'])
def login():
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
   
    # Check if "matricula" and "password" POST requests exist (user submitted form)
    if request.method == 'POST' and 'matricula' in request.form and 'password' in request.form:
        matricula = request.form['matricula']
 
        password = request.form['password']
        print(password)
 
        # Check if account exists using MySQL
        cursor.execute('SELECT * FROM servidores WHERE matricula = %s', (matricula,))
        # Fetch one record and return result
        account = cursor.fetchone()
        
        if account:
            password_rs = account['senha']
            print(password_rs)
            # If account exists in users table in out database
            if check_password_hash(password_rs, password):
                # Create session data, we can access this data in other routes
                session['loggedin'] = True
                session['id'] = account['id_servidor']
                session['matricula'] = account['matricula']
                session['nome_completo'] = account['nome']
                # Redirect to home page
                return redirect(url_for('home'))
            else:
                # Account doesnt exist or matricula/password incorrect
                flash('Matricula/Senha incorretos.', 'alert-warning')
        else:
            # Account doesnt exist or matricula/password incorrect
            flash('Matricula/Senha incorretos.', 'alert-warning')
 
    return render_template('login.html')
  
@app.route('/register', methods=['GET', 'POST'])
def register():
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
 
    # Check if "matricula", "password" and "email" POST requests exist (user submitted form)
    if request.method == 'POST' and 'matricula' in request.form and 'password' in request.form and 'email' in request.form:
        # Create variables for easy access
        fullname = request.form['fullname'].upper()
        matricula = request.form['matricula']
        password = request.form['password']
        email = request.form['email']
        lattes_link = request.form['lattes_link']
        tipo_servidor = 'Docente'
    
        _hashed_password = generate_password_hash(password)
 
        #Check if account exists using MySQL
        cursor.execute('SELECT * FROM servidores WHERE matricula = %s', (matricula,))
        account = cursor.fetchone()
        print(account)
        # If account exists show error and validation checks
        if account:
            flash('Essa conta já existe!', 'alert-danger')
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            flash('Endereço de e-mail inválido!', 'alert-warning')
        elif not re.match(r'^[0-9]+$', matricula):
            flash('Matricula deve conter apenas numeros!', 'alert-warning')
        elif not re.match(r'^http://lattes.cnpq.br/\d{16}$', lattes_link):
            flash('Forneça um Lattes iD válido!', 'alert-warning')
        elif not matricula or not password or not email:
            flash('Por favor, preencha todos os campos!', 'alert-warning')
        else:
            # Account doesnt exists and the form data is valid, now insert new account into users table
            cursor.execute("INSERT INTO servidores (nome, matricula, senha, e_mail, tipo_servidor, lattes_link) VALUES (%s,%s,%s,%s,%s,%s)", (fullname, matricula, _hashed_password, email, tipo_servidor, lattes_link))
            conn.commit()
            flash('Sua conta foi registrada com sucesso!', 'alert-success')
            return render_template('login.html')
    elif request.method == 'POST':
        # Form is empty... (no POST data)
        flash('Por favor, preencha o formulário completo!', 'alert-warning')
    # Show registration form with message (if any)
    return render_template('register.html')
   
   
@app.route('/logout')
def logout():
    # Remove session data, this will log the user out
   session.pop('loggedin', None)
   session.pop('id', None)
   session.pop('matricula', None)
   session.pop('nome_completo', None)
   # Redirect to login page
   return redirect(url_for('login'))
  
@app.route('/profile')
def profile(): 
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
   
    # Check if user is loggedin
    if 'loggedin' in session:
        cursor.execute('SELECT * FROM servidores WHERE id_servidor = %s', [session['id']])
        account = cursor.fetchone()
        # Show the profile page with account info
        return render_template('profile.html', account=account)
    # User is not loggedin redirect to login page
    return redirect(url_for('login'))
 
if __name__ == "__main__":
    app.run(debug=True)