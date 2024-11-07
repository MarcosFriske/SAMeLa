#app.py
from flask import Flask, request, session, redirect, url_for, render_template, flash, make_response, send_file
import pandas as pd
import psycopg2 #pip install psycopg2 
import psycopg2.extras
import re 
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from lxml import etree
import chardet

#reset senha
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import random
import string

# script da pontuação
from algoritmoPontuacaoBD import executar_algoritmo

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

### FUNÇÕES

# Função para gerar tokens aleatórios para redefinição de senha
def generate_token():
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(32))

# Função de envio do e-mail para resetar senha
def send_password_reset_email(receiver_email, token):
    sender_email = 'geati.ifc@gmail.com'  # Insira seu endereço de e-mail aqui
    sender_password = 'fthi rjrw kpop vmfq'  # Insira chave de acesso app - autenticação 2 etapas

    subject = "SAMeLa - Redefinição de Senha"
    body = f"Para redefinir sua senha, clique no link a seguir:\n\nhttp://127.0.0.1:5000/reset_password/{token}"

    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = receiver_email
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            text = message.as_string()
            server.sendmail(sender_email, receiver_email, text)
        print("E-mail enviado com sucesso!")
    except Exception as e:
        print(f"Erro ao enviar e-mail: {e}")


### ROTAS

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
        # Check if account exists using SQL query
        cursor.execute('SELECT * FROM servidores WHERE matricula = %s OR e_mail = %s', (matricula, matricula))
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
        cursor.execute('SELECT * FROM servidores WHERE matricula = %s OR e_mail = %s', (matricula, matricula))
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
        cursor.execute('SELECT * FROM servidores WHERE matricula = %s OR e_mail = %s', (matricula, matricula))
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

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    if request.method == 'POST':
        email = request.form.get('email')

        cursor.execute('SELECT * FROM servidores WHERE e_mail = %s', (email,))
        user = cursor.fetchone()

        if user:
            token = generate_token()

            # Armazena o token no banco de dados
            cursor.execute("UPDATE servidores SET reset_token = %s WHERE id_servidor = %s", (token, user['id_servidor']))
            conn.commit()

            # Envia e-mail com o token para redefinição de senha
            send_password_reset_email(email, token)

            flash('Um e-mail foi enviado com instruções para redefinir sua senha.', 'alert-success')
            return redirect(url_for('login'))
        else:
            flash('E-mail não encontrado. Por favor, insira o e-mail cadastrado.', 'alert-warning')
            return redirect(url_for('login'))  # Adicionando o redirecionamento para a página de login

    return render_template('forgot_password.html')

# Rota para a página de redefinição de senha
@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    # Verifica se o token corresponde a um usuário
    cursor.execute('SELECT * FROM servidores WHERE reset_token = %s', (token,))
    user = cursor.fetchone()

    if user:
        if request.method == 'POST':
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')

            # Verifica se as senhas coincidem
            if new_password == confirm_password:
                # Hash da nova senha
                hashed_password = generate_password_hash(new_password, method='sha256')

                # Atualiza a senha no banco de dados
                cursor.execute("UPDATE servidores SET senha = %s WHERE id_servidor = %s", (hashed_password, user['id_servidor']))

                # Limpa o reset_token
                cursor.execute("UPDATE servidores SET reset_token = NULL WHERE id_servidor = %s", (user['id_servidor'],))
                conn.commit()

                flash('Senha redefinida com sucesso.', 'alert-success')
                return redirect(url_for('login'))
            else:
                flash('As senhas não coincidem. Tente novamente.', 'alert-danger')

        return render_template('reset_password.html', token=token)
    else:
        flash('Token inválido. Por favor, solicite outra redefinição de senha.', 'alert-danger')
        return redirect(url_for('forgot_password'))

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
    cursor.execute('SELECT * FROM eventos WHERE ativo = true ORDER BY data_fim ASC')
    eventos = cursor.fetchall()
    
    cursor.execute('SELECT * FROM instrumentos_avaliacao')
    instrumentos = cursor.fetchall()
    
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute('SELECT unnest(enum_range(NULL::type_evento))')
    tipos_evento = [item for sublist in cursor.fetchall() for item in sublist]

    # Verifique se o usuário está logado
    if 'loggedin' in session:
        return render_template('eventos.html', eventos=eventos, user_role=session['role'], instrumentos=instrumentos, tipos_evento=tipos_evento, eventos_ativos=bool(eventos))
    # Caso contrário, redirecione para a página de login
    return redirect(url_for('login'))

@app.route('/avaliacoes')
def avaliacoes():
    if 'loggedin' in session and session['role'] == 'Docente':
        # Lógica para recuperar os eventos ativos e inscritos pelo Docente
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        current_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute(
            'SELECT a.id_avaliacao, a.data_avaliacao, e.identificacao, e.localizacao '
            'FROM avaliacao a '
            'JOIN eventos e ON a.fk_id_evento = e.id_evento '
            'WHERE a.fk_id_servidor = %s AND e.data_fim >= %s',
            (session['id'], current_datetime)
        )
        eventos_inscritos = cursor.fetchall()

        return render_template('avaliacoes.html', eventos_inscritos=eventos_inscritos)
    else:
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

@app.route('/inscrever_evento', methods=['POST'])
def inscrever_evento():
    if 'loggedin' in session and session['role'] == 'Docente':
        # Lógica para verificar se o Docente já está inscrito no evento
        evento_id = request.form.get('evento_id')
        
        cursor = conn.cursor()
        cursor.execute(
            'SELECT * FROM avaliacao WHERE fk_id_servidor = %s AND fk_id_evento = %s AND data_avaliacao BETWEEN (SELECT data_inicio FROM eventos WHERE id_evento = %s) AND (SELECT data_fim FROM eventos WHERE id_evento = %s)',
            (session['id'], evento_id, evento_id, evento_id)
        )
        inscricao_existente = cursor.fetchone()

        if inscricao_existente:
            # Docente já está inscrito no evento
            flash('Você já está inscrito neste evento.', 'warning')
            return redirect(url_for('eventos'))
        else:
            # Verificar se há um XML de Lattes associado ao servidor
            cursor.execute('SELECT lattes_xml FROM servidores WHERE id_servidor = %s', (session['id'],))
            lattes_xml_result = cursor.fetchone()
            
            if lattes_xml_result is None or lattes_xml_result[0] is None:
                # Se não houver XML de Lattes, exibir mensagem de erro e redirecionar para eventos
                flash('Não há XML de Lattes associado ao seu perfil. Insira seu XML de Lattes para participar da avaliação.', 'danger')
                return redirect(url_for('eventos'))
            
            # Lógica para criar a inscrição na tabela 'avaliacao'
            cursor.execute(
                'SELECT localizacao FROM eventos WHERE id_evento = %s',
                (evento_id,)
            )
            localizacao_do_evento = cursor.fetchone()[0]
            
            cursor.execute(
                'INSERT INTO avaliacao (organizacao, data_avaliacao, fk_id_servidor, fk_id_evento) VALUES (%s, NOW(), %s, %s)',
                (localizacao_do_evento, session['id'], evento_id)
            )
            conn.commit()
            
            cursor.execute(
                'SELECT id_avaliacao FROM avaliacao WHERE fk_id_servidor = %s AND fk_id_evento = %s',
                (session['id'], evento_id)
            )
            id_avaliacao_result = cursor.fetchone()
            
            if id_avaliacao_result is not None:
                id_avaliacao = id_avaliacao_result[0]
            else:
                flash('Erro ao obter o ID da avaliação.', 'danger')
                return redirect(url_for('eventos'))
            
            cursor.execute(
                'SELECT fk_id_instrumento_avaliacao FROM eventos WHERE id_evento = %s',
                (evento_id)
            )
            id_instrumento_avaliacao_result = cursor.fetchone()
            
            if id_instrumento_avaliacao_result is not None:
                instrumento_avaliacao_id = str(id_instrumento_avaliacao_result[0])
            else:
                flash('Erro ao obter o ID do instrumento de avaliação.', 'danger')
                return redirect(url_for('eventos'))
            
            # Chamar a função para obter o DataFrame
            df_avaliacao = executar_algoritmo(id_servidor=session['id'], instrumento_avaliacao_id=instrumento_avaliacao_id)
    
            # Verificar se o DataFrame é válido antes de continuar
            if df_avaliacao is not None:
                # Inserir os dados na tabela avaliacao_dados
                for index, row in df_avaliacao.iterrows():
                    cursor.execute(
                        'INSERT INTO avaliacao_dados (fk_id_avaliacao, item, criterios, pontuacao_por_item, pontuacao_maxima, quantidade, pontuacao_atingida) VALUES (%s, %s, %s, %s, %s, %s, %s)',
                        (id_avaliacao, row['item'], row['criterios'], row['pontuacao_por_item'], row['pontuacao_maxima'], row['quantidade'], row['pontuacao_atingida'])
                    )
                conn.commit()
                
                # Somar os pontos_atingidos da tabela avaliacao_dados
                cursor.execute(
                    'SELECT SUM(pontuacao_atingida) FROM avaliacao_dados WHERE fk_id_avaliacao = %s',
                    (id_avaliacao,)
                )
                soma_pontuacao_result = cursor.fetchone()
                soma_pontuacao = soma_pontuacao_result[0] if soma_pontuacao_result[0] is not None else 0
                
                # Atualizar o campo pontuacao na tabela avaliacao
                cursor.execute(
                    'UPDATE avaliacao SET pontuacao = %s WHERE id_avaliacao = %s',
                    (soma_pontuacao, id_avaliacao)
                )
                conn.commit()
            
                flash('Inscrição realizada com sucesso!', 'success')
                return redirect(url_for('avaliacoes'))
            else:
                flash('Erro ao gerar dados de avaliação.', 'danger')
                return redirect(url_for('eventos'))
    
    return redirect(url_for('login'))
    
@app.route('/detalhes_avaliacao/<int:avaliacao_id>', methods=['GET'])
def detalhes_avaliacao(avaliacao_id):
    if 'loggedin' in session and session['role'] == 'Docente':
        cursor = conn.cursor()

        # Consultar dados da avaliação
        cursor.execute(
            'SELECT * FROM avaliacao_dados WHERE fk_id_avaliacao = %s',
            (avaliacao_id,)
        )
        dados_avaliacao = cursor.fetchall()
        print("Dados da Avaliação:", dados_avaliacao)  # Adicione este print para debug

        # Consultar IDs do docente e do evento associados à avaliação
        cursor.execute(
            'SELECT fk_id_servidor, id_avaliacao FROM avaliacao WHERE id_avaliacao = %s',
            (avaliacao_id,)
        )
        result = cursor.fetchone()

        # Verificar se o resultado não é nulo
        if result:
            id_docente, id_avaliacao = result
            print("ID do Docente:", id_docente)  # Adicione este print para debug
            print("ID do Avaliacao:", id_avaliacao)    # Adicione este print para debug
            return render_template('avaliacao_dados.html', dados_avaliacao=dados_avaliacao, id_avaliacao=id_avaliacao, id_docente=id_docente)
        else:
            # Lidar com a situação em que os IDs não foram encontrados
            flash('IDs do docente e/ou do evento não encontrados para a avaliação.')
            return redirect(url_for('alguma_pagina_de_erro'))

    return redirect(url_for('login'))

@app.route('/download_avaliacao/<int:id_avaliacao>/<int:id_docente>')
def download_avaliacao(id_avaliacao, id_docente):
    # Consultar o banco de dados para obter os dados da avaliação com base nos IDs fornecidos
    query = f"SELECT * FROM avaliacao_dados WHERE fk_id_avaliacao = {id_avaliacao}"
    df_avaliacao = pd.read_sql_query(query, conn)  # Certifique-se de ajustar a conexão com o banco de dados

    # Criar um arquivo Excel temporário
    excel_file = f'avaliacao_{id_avaliacao}_{id_docente}.xlsx'
    df_avaliacao.to_excel(excel_file, index=False)

    # Enviar o arquivo Excel para download
    return send_file(excel_file, as_attachment=True)
    
@app.route('/desinscrever_evento/<int:avaliacao_id>', methods=['POST'])
def desinscrever_evento(avaliacao_id):
    if 'loggedin' in session and session['role'] == 'Docente':
        cursor = conn.cursor()

        # Verificar se o Docente está inscrito no evento
        cursor.execute(
            'SELECT * FROM avaliacao WHERE id_avaliacao = %s AND fk_id_servidor = %s',
            (avaliacao_id, session['id'])
        )
        inscricao_existente = cursor.fetchone()

        if inscricao_existente:
            # Antes de excluir a avaliação, precisamos excluir os dados correspondentes na tabela avaliacao_dados
            cursor.execute('DELETE FROM avaliacao_dados WHERE fk_id_avaliacao = %s', (avaliacao_id,))
            
            # Agora podemos excluir a inscrição na tabela 'avaliacao'
            cursor.execute('DELETE FROM avaliacao WHERE id_avaliacao = %s', (avaliacao_id,))
            
            conn.commit()
            flash('Desinscrição realizada com sucesso!', 'success')
        else:
            flash('Você não está inscrito neste evento.', 'warning')

        # Redirecionar para a página de avaliações após a desinscrição
        return redirect(url_for('avaliacoes'))

    return redirect(url_for('login'))

@app.route('/instrumentos_avaliacao')
def instrumentos_avaliacao():
    if 'loggedin' in session and session['role'] == 'Administrador':
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute('SELECT * FROM instrumentos_avaliacao')
        instrumentos = cursor.fetchall()
        return render_template('instrumentos_avaliacao.html', instrumentos=instrumentos, user_role=session['role'])
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

@app.route('/criterios')
def criterios():
    if 'loggedin' in session and session['role'] == 'Administrador':
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Parâmetros de filtro e paginação
        filtro_instrumento = request.args.get('instrumento_filtro', '')
        pagina = int(request.args.get('pagina', 1))
        itens_por_pagina = int(request.args.get('itens_por_pagina', 5))

        # Calcular o offset para a paginação
        offset = (pagina - 1) * itens_por_pagina

        # Inicialização de instrumento_selecionado
        instrumento_selecionado = None

        # Verificar se existe um filtro de instrumento
        if filtro_instrumento:
            # Filtrar critérios por instrumento de avaliação
            cursor.execute("""
                SELECT * FROM criterios
                WHERE fk_id_instrumento_avaliacao = %s
                LIMIT %s OFFSET %s
            """, (filtro_instrumento, itens_por_pagina, offset))
            criterios = cursor.fetchall()

            cursor.execute("""
                SELECT COUNT(*) FROM criterios
                WHERE fk_id_instrumento_avaliacao = %s
            """, (filtro_instrumento,))
            
            # Buscar o instrumento selecionado
            cursor.execute("""
                SELECT * FROM instrumentos_avaliacao
                WHERE id_instrumento_avaliacao = %s
            """, (filtro_instrumento,))
            instrumento_selecionado = cursor.fetchone()

        else:
            # Caso não tenha filtro, buscar todos os critérios
            cursor.execute("""
                SELECT * FROM criterios
                LIMIT %s OFFSET %s
            """, (itens_por_pagina, offset))
            criterios = cursor.fetchall()

            cursor.execute("""
                SELECT COUNT(*) FROM criterios
            """)

        # Verificação da contagem
        count_result = cursor.fetchone()
        if count_result and count_result[0]:
            total_criterios = count_result[0]
        else:
            total_criterios = 0

        # Calcular o número total de páginas
        total_paginas = (total_criterios + itens_por_pagina - 1) // itens_por_pagina

        # Buscar todos os instrumentos para o filtro
        cursor.execute("SELECT * FROM instrumentos_avaliacao")
        instrumentos = cursor.fetchall()

        return render_template('criterios.html', criterios=criterios, instrumentos=instrumentos,
                               pagina=pagina, total_paginas=total_paginas,
                               filtro_instrumento=filtro_instrumento, 
                               instrumento_selecionado=instrumento_selecionado,
                               itens_por_pagina=itens_por_pagina,
                               user_role=session['role'])
    else:
        return redirect(url_for('login'))


@app.route('/criar_criterio', methods=['GET', 'POST'])
def criar_criterio():
    if 'loggedin' not in session or session['role'] != 'Administrador':
        return redirect(url_for('login'))

    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    if request.method == 'POST':
        try:
            nome_criterio = request.form['criterio']  # Nome do critério
            qtd_maxima_itens = request.form['qtd_maxima_itens']  # Quantidade máxima de itens
            pontuacao_item = request.form['pontuacao_item']  # Pontuação por item
            xpath_criterio_lattes = request.form['xpath_criterio_lattes']  # XPath do critério
            considera_qualis = bool(request.form.get('considera_qualis'))  # Se considera qualis (checkbox)
            id_instrumento = request.form['fk_id_instrumento_avaliacao']  # ID do instrumento de avaliação
            ativo = bool(request.form.get('ativo'))  # Critério ativo (checkbox)
            
            # Inserir o novo critério no banco de dados
            cursor.execute("""
                INSERT INTO criterios (qtd_maxima_itens, pontuacao_item, criterio, xpath_criterio_lattes, 
                                       considera_qualis, fk_id_instrumento_avaliacao, ativo)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (qtd_maxima_itens, pontuacao_item, nome_criterio, xpath_criterio_lattes, considera_qualis, id_instrumento, ativo))

            conn.commit()

            flash('Critério criado e associado com sucesso!', 'success')
        except psycopg2.Error as e:
            conn.rollback()
            flash(f'Ocorreu um erro ao criar o critério: {str(e)}', 'danger')

        # Após criação, redireciona para a página de critérios com o filtro correto
        return redirect(url_for('criterios', instrumento_filtro=request.form['fk_id_instrumento_avaliacao']))

    # Carregar os instrumentos de avaliação disponíveis
    cursor.execute('SELECT * FROM instrumentos_avaliacao')
    instrumentos = cursor.fetchall()

    return render_template('criar_criterio.html', instrumentos=instrumentos)


@app.route('/remover_criterio/<int:criterio_id>', methods=['POST'])
def remover_criterio(criterio_id):
    if 'loggedin' not in session or session['role'] != 'Administrador':
        return redirect(url_for('login'))

    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    try:
        # Deletar o critério com o ID fornecido
        cursor.execute("""
            DELETE FROM criterios WHERE id_criterio = %s
        """, (criterio_id,))
        
        conn.commit()

        flash('Critério removido com sucesso!', 'success')
    except psycopg2.Error as e:
        conn.rollback()
        flash(f'Ocorreu um erro ao remover o critério: {str(e)}', 'danger')

    # Obter os parâmetros de filtro para manter a visualização
    filtro_instrumento = request.args.get('instrumento_filtro', '')  # Pega o valor de filtro ou uma string vazia
    pagina = request.args.get('pagina', 1)  # A página deve ser obtida
    itens_por_pagina = request.args.get('itens_por_pagina', 5)  # O número de itens por página

    # Redirecionar de volta para a página de critérios com os filtros aplicados
    return redirect(url_for('criterios', instrumento_filtro=filtro_instrumento, pagina=pagina, itens_por_pagina=itens_por_pagina))



@app.route('/editar_criterio/<int:criterio_id>', methods=['GET', 'POST'])
def editar_criterio(criterio_id):
    if 'loggedin' not in session or session['role'] != 'Administrador':
        return redirect(url_for('login'))

    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    if request.method == 'POST':
        try:
            nome_criterio = request.form['criterio']
            qtd_maxima_itens = int(request.form['qtd_maxima_itens'])
            pontuacao_item = float(request.form['pontuacao_item'])
            xpath_criterio_lattes = request.form['xpath_criterio_lattes']
            considera_qualis = bool(request.form.get('considera_qualis'))
            id_instrumento = int(request.form['fk_id_instrumento_avaliacao'])
            ativo = bool(request.form.get('ativo'))

            # Validação para evitar valores negativos
            if qtd_maxima_itens < 0 or pontuacao_item < 0:
                flash('A quantidade máxima de itens e a pontuação por item não podem ser negativos.', 'danger')
                cursor.execute('SELECT * FROM criterios WHERE id_criterio = %s', (criterio_id,))
                criterio = cursor.fetchone()
                cursor.execute('SELECT * FROM instrumentos_avaliacao')
                instrumentos = cursor.fetchall()
                return render_template('editar_criterio.html', criterio=criterio, instrumentos=instrumentos)

            cursor.execute("""
                UPDATE criterios
                SET qtd_maxima_itens = %s, pontuacao_item = %s, criterio = %s, xpath_criterio_lattes = %s, 
                    considera_qualis = %s, fk_id_instrumento_avaliacao = %s, ativo = %s
                WHERE id_criterio = %s
            """, (qtd_maxima_itens, pontuacao_item, nome_criterio, xpath_criterio_lattes, considera_qualis, id_instrumento, ativo, criterio_id))

            conn.commit()
            flash('Critério atualizado com sucesso!', 'success')
            return redirect(url_for('criterios'))
        except psycopg2.Error as e:
            conn.rollback()
            flash(f'Ocorreu um erro ao atualizar o critério: {str(e)}', 'danger')

    cursor.execute('SELECT * FROM criterios WHERE id_criterio = %s', (criterio_id,))
    criterio = cursor.fetchone()
    cursor.execute('SELECT * FROM instrumentos_avaliacao')
    instrumentos = cursor.fetchall()

    return render_template('editar_criterio.html', criterio=criterio, instrumentos=instrumentos)

@app.route('/associar_criterio', methods=['GET', 'POST'])
def associar_criterio():
    if 'loggedin' not in session or session['role'] != 'Administrador':
        return redirect(url_for('login'))

    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # Obter o ID do instrumento de avaliação da query string
    instrumento_id = request.args.get('instrumento')
    
    if request.method == 'POST':
        try:
            criterio_id = request.form['criterio_id']  # ID do critério selecionado
            
            # Atualizar o critério para associá-lo ao instrumento selecionado
            cursor.execute("""
                UPDATE criterios
                SET fk_id_instrumento_avaliacao = %s
                WHERE id_criterio = %s
            """, (instrumento_id, criterio_id))

            conn.commit()
            flash('Critério associado com sucesso!', 'success')
            return redirect(url_for('criterios', instrumento_filtro=instrumento_id))
        except psycopg2.Error as e:
            conn.rollback()
            flash(f'Ocorreu um erro ao associar o critério: {str(e)}', 'danger')

    # Buscar todos os critérios que ainda não estão associados ao instrumento selecionado
    cursor.execute("""
        SELECT * FROM criterios
        WHERE fk_id_instrumento_avaliacao IS NULL OR fk_id_instrumento_avaliacao != %s
    """, (instrumento_id,))
    criterios_disponiveis = cursor.fetchall()

    # Buscar o instrumento selecionado
    cursor.execute("""
        SELECT * FROM instrumentos_avaliacao
        WHERE id_instrumento_avaliacao = %s
    """, (instrumento_id,))
    instrumento = cursor.fetchone()

    return render_template('associar_criterio.html', criterios=criterios_disponiveis, instrumento=instrumento)


@app.route('/instrumentos_criterios/<int:instrumento_id>')
def instrumentos_criterios(instrumento_id):
    if 'loggedin' in session and session['role'] == 'Administrador':
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute("""
            SELECT c.criterio, c.qtd_maxima_itens, c.pontuacao_item, c.xpath_criterio_lattes, c.considera_qualis, c.ativo 
            FROM criterios c
            WHERE c.fk_id_instrumento_avaliacao = %s
        """, (instrumento_id,))
        criterios = cursor.fetchall()

        return render_template('instrumentos_criterios.html', criterios=criterios, instrumento_id=instrumento_id)
    else:
        return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(debug=True)
    # app.run()