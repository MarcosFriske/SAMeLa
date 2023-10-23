#app.py
from flask import Flask, request, session, redirect, url_for, render_template, flash, make_response
import psycopg2 #pip install psycopg2 
import psycopg2.extras
import re 
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from lxml import etree
import chardet

app = Flask(__name__)
app.secret_key = 'SAMeLa'
app.config['PERMANENT_SESSION_LIFETIME'] =  timedelta(minutes=10)
COOKIE_TIME_OUT = 60*60*24*7 #7 days

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
        return render_template('home.html', nome_completo=session['nome_completo'].title(), role=session['role'])
    # User is not loggedin redirect to login page
    return redirect(url_for('login'))
 
@app.route('/login/', methods=['GET', 'POST'])
def login():
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    # Login com Lembre-me (Cookies)
    if 'matricula' in request.cookies:
        matricula = request.cookies.get('matricula')
        password = request.cookies.get('senha')
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
                session['senha'] = account['senha']
                session['nome_completo'] = account['nome']
                session['role'] = account['tipo_servidor']
                # Redirect to home page
                return redirect(url_for('home'))
            else:
                # Account doesnt exist or matricula/password incorrect
                flash('Matricula/Senha incorretos.', 'alert-warning')
        else:
            # Account doesnt exist or matricula/password incorrect
            flash('Matricula/Senha incorretos.', 'alert-warning')
    
    # Checar se foi tentativa de login normal, "matricula" e "password" POST request existe (usuario submeteu o formulario)
    elif request.method == 'POST' and 'matricula' in request.form and 'password' in request.form:
        matricula = request.form['matricula']
        password = request.form['password']
        remember = True if request.form.get('remember') else False
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
                session['senha'] = account['senha']
                session['nome_completo'] = account['nome']
                session['role'] = account['tipo_servidor']
                if remember:
                    resp = make_response(redirect(url_for('home')))
                    resp.set_cookie('matricula', matricula, max_age=COOKIE_TIME_OUT)
                    resp.set_cookie('senha', password, max_age=COOKIE_TIME_OUT)
                    resp.set_cookie('remember', 'checked', max_age=COOKIE_TIME_OUT)
                    return resp
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


@app.route('/upload_xml', methods=['POST'])
def upload_xml():
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    if 'file' not in request.files:
        flash('Nenhum arquivo foi selecionado', 'alert-warning')
        return redirect(url_for('profile'))

    file = request.files['file']
    if file.filename == '':
        flash('Nenhum arquivo foi selecionado', 'alert-warning')
        return redirect(url_for('profile'))

    if file:
        xml_content = file.read()
        
        # Detecta a codificação correta do arquivo
        detected_encoding = chardet.detect(xml_content)['encoding']

        try:
            etree.fromstring(xml_content)
        except etree.XMLSyntaxError as e:
            flash('O arquivo fornecido não é um XML válido', 'alert-warning')
            return redirect(url_for('profile'))
        
        try:
            # Convertendo bytes para string usando a codificação detectada
            xml_string = xml_content.decode(detected_encoding)
        except UnicodeDecodeError as e:
            flash('Ocorreu um erro ao decodificar o arquivo', 'alert-danger')
            return redirect(url_for('profile'))

        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute("UPDATE servidores SET lattes_xml = %s, ultimo_upload = current_timestamp WHERE id_servidor = %s", (xml_string, session['id']))
        conn.commit()
        flash('Arquivo XML enviado com sucesso', 'alert-success')
        return redirect(url_for('profile'))

    flash('Algo deu errado ao enviar o arquivo', 'alert-danger')
    return redirect(url_for('profile'))

@app.route('/logout')
def logout():
    # Remove session data, this will log the user out
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('matricula', None)
    session.pop('senha', None)
    session.pop('nome_completo', None)
    session.pop('role', None)
   
    # Remove cookies
    resp = make_response(redirect(url_for('login')))
    resp.set_cookie('matricula', '', max_age=0)
    resp.set_cookie('senha', '', max_age=0)
    resp.set_cookie('remember', '', max_age=0)
    
    # Redirect to login page
    return resp
      
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

@app.route('/eventos')
def eventos():
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute('SELECT * FROM eventos')
    eventos = cursor.fetchall()
    
    cursor.execute('SELECT * FROM instrumentos_avaliacao')
    instrumentos = cursor.fetchall()
    
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute('SELECT unnest(enum_range(NULL::type_evento))')
    tipos_evento = [item for sublist in cursor.fetchall() for item in sublist]

    # Verifique se o usuário está logado
    if 'loggedin' in session:
        return render_template('eventos.html', eventos=eventos, user_role=session['role'], instrumentos=instrumentos, tipos_evento=tipos_evento)
    # Caso contrário, redirecione para a página de login
    return redirect(url_for('login'))

@app.route('/criar_evento', methods=['POST'])
def criar_evento():
    if 'loggedin' not in session or session['role'] != 'Administrador':
        return redirect(url_for('login'))

    if request.method == 'POST':
        try:
            identificacao = request.form['identificacao']
            tipo_evento = request.form['tipo_evento']
            data_inicio = request.form['data_inicio']
            data_fim = request.form['data_fim']
            localizacao = request.form['localizacao']
            descricao = request.form['descricao']
            data_criacao = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            data_atualizacao = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            id_instrumento_avaliacao = request.form['fk_id_instrumento_avaliacao']  # Use diretamente o ID do instrumento recebido
            print("Valor recebido do formulário:", id_instrumento_avaliacao)  # Adicione esta linha para verificar o valor recebido
    
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO eventos (identificacao, tipo_evento, data_inicio, data_fim, localizacao, descricao, data_criacao, data_atualizacao, fk_id_instrumento_avaliacao)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (identificacao, tipo_evento, data_inicio, data_fim, localizacao, descricao, data_criacao, data_atualizacao, id_instrumento_avaliacao))
    
            conn.commit()
    
            flash('Novo evento criado com sucesso!', 'alert-success')
        except psycopg2.Error as e:
            conn.rollback()  # Realiza um rollback da transação para garantir a consistência
            flash(f'Ocorreu um erro ao criar o evento: {str(e)}', 'alert-danger')
            
    return redirect(url_for('eventos'))

@app.route('/remover_evento/<int:evento_id>', methods=['GET', 'POST'])
def remover_evento(evento_id):
    if 'loggedin' not in session or session['role'] != 'Administrador':
        return redirect(url_for('login'))

    if request.method == 'POST':
        cursor = conn.cursor()
        cursor.execute("DELETE FROM eventos WHERE id_evento = %s", (evento_id,))
        conn.commit()

        flash('Evento removido com sucesso!', 'alert-success')
        return redirect(url_for('eventos'))

    return redirect(url_for('eventos'))

@app.route('/editar_evento/<int:evento_id>', methods=['GET', 'POST'])
def editar_evento(evento_id):
    if 'loggedin' not in session or session['role'] != 'Administrador':
        return redirect(url_for('login'))

    if request.method == 'POST':
        try:
            identificacao = request.form['identificacao']
            tipo_evento = request.form['tipo_evento']
            data_inicio = request.form['data_inicio']
            data_fim = request.form['data_fim']
            localizacao = request.form['localizacao']
            descricao = request.form['descricao']
            id_instrumento_avaliacao = request.form['fk_id_instrumento_avaliacao']

            cursor = conn.cursor()
            cursor.execute("""
                UPDATE eventos 
                SET identificacao = %s, 
                    tipo_evento = %s, 
                    data_inicio = %s, 
                    data_fim = %s, 
                    localizacao = %s, 
                    descricao = %s, 
                    fk_id_instrumento_avaliacao = %s 
                WHERE id_evento = %s
            """, (identificacao, tipo_evento, data_inicio, data_fim, localizacao, descricao, id_instrumento_avaliacao, evento_id))
            conn.commit()

            flash('Evento atualizado com sucesso!', 'alert-success')
            return redirect(url_for('eventos'))
        except Exception as e:
            flash(f'Ocorreu um erro ao atualizar o evento: {str(e)}', 'alert-danger')

    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute("SELECT * FROM eventos WHERE id_evento = %s", (evento_id,))
    evento = cursor.fetchone()

    cursor.execute('SELECT * FROM instrumentos_avaliacao')
    instrumentos = cursor.fetchall()

    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute('SELECT unnest(enum_range(NULL::type_evento))')
    tipos_evento = [item for sublist in cursor.fetchall() for item in sublist]

    return render_template('editar_evento.html', evento=evento, instrumentos=instrumentos, tipos_evento=tipos_evento)

@app.route('/instrumentos_avaliacao')
def instrumentos_avaliacao():
    if 'loggedin' in session and session['role'] == 'Administrador':
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute('SELECT * FROM instrumentos_avaliacao')
        instrumentos = cursor.fetchall()
        return render_template('instrumentos_avaliacao.html', instrumentos=instrumentos)
    else:
        return redirect(url_for('login'))
    
@app.route('/criar_instrumento', methods=['POST'])
def criar_instrumento():
    if 'loggedin' not in session or session['role'] != 'Administrador':
        return redirect(url_for('login'))

    if request.method == 'POST':
        try:
            nome = request.form['nome']
            descricao = request.form['descricao']
            ativo = request.form.get('ativo') == 'on'  # Verifica se a caixa de seleção está marcada e atribui True ou False

            data_criacao = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # Obtém a data atual

            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO instrumentos_avaliacao (nome, descricao, ativo, data_criacao)
                VALUES (%s, %s, %s, %s)
            """, (nome, descricao, ativo, data_criacao))

            conn.commit()

            flash('Novo instrumento de avaliação criado com sucesso!', 'alert-success')
        except psycopg2.Error as e:
            conn.rollback()  # Realiza um rollback da transação para garantir a consistência
            flash(f'Ocorreu um erro ao criar o instrumento de avaliação: {str(e)}', 'alert-danger')
            
    return redirect(url_for('instrumentos_avaliacao'))

@app.route('/editar_instrumento/<int:instrumento_id>', methods=['GET', 'POST'])
def editar_instrumento(instrumento_id):
    if 'loggedin' not in session or session['role'] != 'Administrador':
        return redirect(url_for('login'))

    if request.method == 'POST':
        try:
            nome = request.form['nome']
            descricao = request.form['descricao']
            ativo = request.form.get('ativo') == 'on'

            cursor = conn.cursor()
            cursor.execute("""
                UPDATE instrumentos_avaliacao 
                SET nome = %s, 
                    descricao = %s, 
                    ativo = %s 
                WHERE id_instrumento_avaliacao = %s
            """, (nome, descricao, ativo, instrumento_id))
            conn.commit()

            flash('Instrumento de avaliação atualizado com sucesso!', 'alert-success')
            return redirect(url_for('instrumentos_avaliacao'))
        except Exception as e:
            flash(f'Ocorreu um erro ao atualizar o instrumento de avaliação: {str(e)}', 'alert-danger')

    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute("SELECT * FROM instrumentos_avaliacao WHERE id_instrumento_avaliacao = %s", (instrumento_id,))
    instrumento = cursor.fetchone()

    return render_template('editar_instrumento.html', instrumento=instrumento)


@app.route('/remover_instrumento/<int:instrumento_id>', methods=['POST'])
def remover_instrumento(instrumento_id):
    if 'loggedin' not in session or session['role'] != 'Administrador':
        return redirect(url_for('login'))

    cursor = conn.cursor()
    cursor.execute("DELETE FROM instrumentos_avaliacao WHERE id_instrumento_avaliacao = %s", (instrumento_id,))
    conn.commit()

    flash('Instrumento de avaliação removido com sucesso!', 'alert-success')
    return redirect(url_for('instrumentos_avaliacao'))
 
if __name__ == "__main__":
    # app.run(debug=True)
    app.run()