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
    # Check if user is logged in
    if 'loggedin' in session:
        # Geração de texto genérico para os avisos (substituir futuramente por consulta no banco)
        avisos = [
            "Bem-vindo ao sistema SAMeLa!",
            "Lembre-se de atualizar seus dados pessoais.",
            "O prazo para submissão de atividades é dia 10/12/2024."
        ]
        # Renderiza a página inicial com os avisos
        return render_template(
            'home.html', 
            nome_completo=session['nome_completo'].title(), 
            role=session['role'],
            avisos=avisos  # Passa os avisos para o template
        )
    # Usuário não está logado, redireciona para a página de login
    return redirect(url_for('login'))

 
@app.route('/login/', methods=['GET', 'POST'])
def login():
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    # Login com Lembre-me (Cookies)
    if 'matricula' in request.cookies:
        matricula = request.cookies.get('matricula')
        password = request.cookies.get('senha')
        cursor.execute('SELECT * FROM servidores WHERE matricula = %s OR e_mail = %s', (matricula, matricula))
        account = cursor.fetchone()
        
        if account:
            password_rs = account['senha']
            if check_password_hash(password_rs, password):
                session['loggedin'] = True
                session['id'] = account['id_servidor']
                session['matricula'] = account['matricula']
                session['senha'] = account['senha']
                session['nome_completo'] = account['nome']
                session['role'] = account['tipo_servidor']
                return redirect(url_for('home'))
            else:
                flash('Matricula/Senha incorretos.', 'warning')
        else:
            flash('Matricula/Senha incorretos.', 'warning')
    
    elif request.method == 'POST' and 'matricula' in request.form and 'password' in request.form:
        matricula = request.form['matricula']
        password = request.form['password']
        remember = True if request.form.get('remember') else False
        
        cursor.execute('SELECT * FROM servidores WHERE matricula = %s OR e_mail = %s', (matricula, matricula))
        account = cursor.fetchone()
        
        if account:
            password_rs = account['senha']
            if check_password_hash(password_rs, password):
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
                return redirect(url_for('home'))
            else:
                flash('Matricula/Senha incorretos.', 'warning')
        else:
            flash('Matricula/Senha incorretos.', 'warning')

    # Paginação dos avisos
    avisos = [
        {"tipo": "info", "mensagem": "O sistema estará indisponível no dia 05/12 das 08:00 às 12:00."},
        {"tipo": "warning", "mensagem": "Atualize sua senha regularmente para maior segurança."},
        {"tipo": "success", "mensagem": "Estamos felizes em tê-lo(a) de volta."},
        {"tipo": "info", "mensagem": "Manutenção programada para o próximo fim de semana."},
        {"tipo": "error", "mensagem": "Erro no sistema detectado."},
    ]

    # Paginação manual
    page = request.args.get('page', 1, type=int)
    per_page = 2  # Quantos avisos por página
    total = len(avisos)
    start = (page - 1) * per_page
    end = start + per_page
    paginated_avisos = avisos[start:end]

    pagination = {
        "has_prev": page > 1,
        "has_next": end < total,
        "prev_num": page - 1 if page > 1 else None,
        "next_num": page + 1 if end < total else None,
        "pages": list(range(1, (total // per_page) + (1 if total % per_page > 0 else 0) + 1)),
        "current_page": page,
    }

    return render_template('login.html', avisos=paginated_avisos, pagination=pagination)

  
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
            flash('Essa conta já existe!', 'danger')
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            flash('Endereço de e-mail inválido!', 'warning')
        elif not re.match(r'^[0-9]+$', matricula):
            flash('Matricula deve conter apenas numeros!', 'warning')
        elif not re.match(r'^http://lattes.cnpq.br/\d{16}$', lattes_link):
            flash('Forneça um Lattes iD válido!', 'warning')
        elif not matricula or not password or not email:
            flash('Por favor, preencha todos os campos!', 'warning')
        else:
            # Account doesnt exists and the form data is valid, now insert new account into users table
            cursor.execute("INSERT INTO servidores (nome, matricula, senha, e_mail, tipo_servidor, lattes_link) VALUES (%s,%s,%s,%s,%s,%s)", (fullname, matricula, _hashed_password, email, tipo_servidor, lattes_link))
            conn.commit()
            flash('Sua conta foi registrada com sucesso!', 'success')
            return render_template('login.html')
    elif request.method == 'POST':
        # Form is empty... (no POST data)
        flash('Por favor, preencha o formulário completo!', 'warning')
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

            flash('Um e-mail foi enviado com instruções para redefinir sua senha.', 'success')
            return redirect(url_for('login'))
        else:
            flash('E-mail não encontrado. Por favor, insira o e-mail cadastrado.', 'warning')
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

                flash('Senha redefinida com sucesso.', 'success')
                return redirect(url_for('login'))
            else:
                flash('As senhas não coincidem. Tente novamente.', 'danger')

        return render_template('reset_password.html', token=token)
    else:
        flash('Token inválido. Por favor, solicite outra redefinição de senha.', 'danger')
        return redirect(url_for('forgot_password'))

@app.route('/upload_xml', methods=['POST'])
def upload_xml():
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    if 'file' not in request.files:
        flash('Nenhum arquivo foi selecionado', 'warning')
        return redirect(url_for('profile'))

    file = request.files['file']
    if file.filename == '':
        flash('Nenhum arquivo foi selecionado', 'warning')
        return redirect(url_for('profile'))

    if file:
        xml_content = file.read()

        # Detectar codificação do arquivo
        detected_encoding = chardet.detect(xml_content)['encoding']
        print(f"📄 Codificação detectada: {detected_encoding}")

        try:
            # Decodificar XML e verificar se é válido
            xml_string = xml_content.decode(detected_encoding)
            root = etree.fromstring(xml_string.encode('utf-8'))
        except (UnicodeDecodeError, etree.XMLSyntaxError) as e:
            flash('Erro ao processar o XML', 'danger')
            print(f"❌ Erro ao processar XML: {e}")
            return redirect(url_for('profile'))

        # Extrair data e hora do XML
        data_attr = root.attrib.get("DATA-ATUALIZACAO")
        hora_attr = root.attrib.get("HORA-ATUALIZACAO")

        if not data_attr or not hora_attr:
            flash('Não foi possível encontrar a data/hora de atualização no XML', 'warning')
            print("⚠️ DATA-ATUALIZACAO ou HORA-ATUALIZACAO não encontrados")
            return redirect(url_for('profile'))

        print(f"📅 DATA-ATUALIZACAO: {data_attr} | 🕒 HORA-ATUALIZACAO: {hora_attr}")

        try:
            # Converter string "12022023" + "190416" para datetime
            data_hora_lattes = datetime.strptime(data_attr + hora_attr, "%d%m%Y%H%M%S")
            print(f"✅ Timestamp convertido: {data_hora_lattes}")
        except ValueError as e:
            flash('Formato de data/hora inválido no XML', 'danger')
            print(f"❌ Erro ao converter data/hora: {e}")
            return redirect(url_for('profile'))

        # Atualizar o banco de dados
        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            cursor.execute("""
                UPDATE servidores
                SET lattes_xml = %s,
                    ultimo_upload = current_timestamp,
                    data_ultima_atualizacao_lattes = %s
                WHERE id_servidor = %s
            """, (xml_string, data_hora_lattes, session['id']))
            conn.commit()
            cursor.close()
            flash('Arquivo XML enviado com sucesso', 'success')
        except Exception as e:
            flash('Erro ao salvar os dados no banco', 'danger')
            print(f"❌ Erro no banco de dados: {e}")
            return redirect(url_for('profile'))

        return redirect(url_for('profile'))

    flash('Algo deu errado ao enviar o arquivo', 'danger')
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
        return render_template('profile.html', account=account, now=datetime.now())
    
    # User is not loggedin redirect to login page
    return redirect(url_for('login'))

@app.route('/eventos')
def eventos():
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    # Ajustando a query para filtrar eventos cujo data_fim ainda não passou
    cursor.execute("""
        SELECT * FROM eventos 
        WHERE ativo = true 
        AND data_fim >= CURRENT_DATE
        ORDER BY data_fim ASC
    """)
    eventos = cursor.fetchall()
    
    cursor.execute('SELECT * FROM instrumentos_avaliacao')
    instrumentos = cursor.fetchall()
    
    cursor.execute('SELECT unnest(enum_range(NULL::type_evento))')
    tipos_evento = [item for sublist in cursor.fetchall() for item in sublist]

    if 'loggedin' in session:
        return render_template('eventos.html', eventos=eventos, user_role=session['role'], instrumentos=instrumentos, tipos_evento=tipos_evento, eventos_ativos=bool(eventos))

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
    
            flash('Novo evento criado com sucesso!', 'success')
        except psycopg2.Error as e:
            conn.rollback()  # Realiza um rollback da transação para garantir a consistência
            flash(f'Ocorreu um erro ao criar o evento: {str(e)}', 'danger')
            
    return redirect(url_for('eventos'))

@app.route('/remover_evento/<int:evento_id>', methods=['GET', 'POST'])
def remover_evento(evento_id):
    if 'loggedin' not in session or session['role'] != 'Administrador':
        return redirect(url_for('login'))

    if request.method == 'POST':
        cursor = conn.cursor()
        cursor.execute("DELETE FROM eventos WHERE id_evento = %s", (evento_id,))
        conn.commit()

        flash('Evento removido com sucesso!', 'success')
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
            criterios_selecionados = request.form.getlist('criterios')  # Recebe os IDs dos critérios selecionados

            # Atualizando os dados básicos do evento
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE eventos 
                SET identificacao = %s, 
                    tipo_evento = %s, 
                    data_inicio = %s, 
                    data_fim = %s, 
                    localizacao = %s, 
                    descricao = %s 
                WHERE id_evento = %s
            """, (identificacao, tipo_evento, data_inicio, data_fim, localizacao, descricao, evento_id))
            conn.commit()
            
            # Atualizando as associações de critérios (removendo as antigas e adicionando as novas)
            cursor.execute("DELETE FROM rel_eventos_criterios WHERE id_evento = %s", (evento_id,))
            for criterio_id in criterios_selecionados:
                cursor.execute("""
                    INSERT INTO rel_eventos_criterios (id_evento, id_criterio) 
                    VALUES (%s, %s)
                """, (evento_id, criterio_id))
            conn.commit()

            flash('Evento atualizado com sucesso!', 'success')
            return redirect(url_for('eventos'))
        except Exception as e:
            flash(f'Ocorreu um erro ao atualizar o evento: {str(e)}', 'danger')

    # Carregando os dados do evento
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute("SELECT * FROM eventos WHERE id_evento = %s", (evento_id,))
    evento = cursor.fetchone()
    
    # Carregando os instrumentos de avaliação e critérios associados
    cursor.execute("""
        SELECT c.id_criterio, c.criterio, i.nome_instrumento
        FROM criterios c
        JOIN rel_criterios_instrumentos rci ON c.id_criterio = rci.id_criterio
        JOIN instrumentos_avaliacao i ON rci.id_instrumento_avaliacao = i.id_instrumento_avaliacao
        WHERE c.ativo = TRUE
        ORDER BY i.nome_instrumento, c.criterio
    """)
    criterios_disponiveis = cursor.fetchall()

    # Carregando os critérios já associados ao evento
    cursor.execute("""
        SELECT id_criterio 
        FROM rel_eventos_criterios 
        WHERE id_evento = %s
    """, (evento_id,))
    criterios_associados = [row['id_criterio'] for row in cursor.fetchall()]

    # Carregando os tipos de evento
    cursor.execute('SELECT unnest(enum_range(NULL::type_evento))')
    tipos_evento = [item for sublist in cursor.fetchall() for item in sublist]

    return render_template(
        'editar_evento.html', 
        evento=evento, 
        criterios_disponiveis=criterios_disponiveis, 
        criterios_associados=criterios_associados, 
        tipos_evento=tipos_evento
    )

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
            
            # Obter o ID do instrumento de avaliação a partir da nova tabela
            cursor.execute(
                '''
                SELECT id_instrumento_avaliacao 
                FROM rel_criterios_instrumentos 
                WHERE id_instrumento_avaliacao = (
                    SELECT fk_id_instrumento_avaliacao 
                    FROM eventos 
                    WHERE id_evento = %s
                )
                ''',
                (evento_id,)
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

            flash('Novo instrumento de avaliação criado com sucesso!', 'success')
        except psycopg2.Error as e:
            conn.rollback()  # Realiza um rollback da transação para garantir a consistência
            flash(f'Ocorreu um erro ao criar o instrumento de avaliação: {str(e)}', 'danger')
            
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

            flash('Instrumento de avaliação atualizado com sucesso!', 'success')
            return redirect(url_for('instrumentos_avaliacao'))
        except Exception as e:
            flash(f'Ocorreu um erro ao atualizar o instrumento de avaliação: {str(e)}', 'danger')

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

    flash('Instrumento de avaliação removido com sucesso!', 'success')
    return redirect(url_for('instrumentos_avaliacao'))

@app.route('/criterios', methods=['GET'])
def criterios():
    if 'loggedin' in session and session['role'] == 'Administrador':
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        # Parâmetros de filtro e paginação
        pesquisa = request.args.get('pesquisa', '').strip()
        pagina = int(request.args.get('pagina', 1))
        itens_por_pagina = int(request.args.get('itens_por_pagina', 5))

        # Calcular o offset para a paginação
        offset = (pagina - 1) * itens_por_pagina

        # Debug: log da pesquisa
        print(f"Pesquisa: {pesquisa}")

        try:
            # Filtrar critérios com base na pesquisa (caso haja pesquisa)
            if pesquisa:
                cursor.execute("""
                    SELECT * FROM criterios
                    WHERE ativo = TRUE AND criterio ILIKE %s
                    ORDER BY criterio ASC
                    LIMIT %s OFFSET %s
                """, ('%' + pesquisa + '%', itens_por_pagina, offset))
            else:
                cursor.execute("""
                    SELECT * FROM criterios
                    WHERE ativo = TRUE
                    ORDER BY criterio ASC
                    LIMIT %s OFFSET %s
                """, (itens_por_pagina, offset))
            
            criterios = cursor.fetchall()

            # Contar total de critérios
            if pesquisa:
                cursor.execute("""
                    SELECT COUNT(*) FROM criterios
                    WHERE ativo = TRUE AND criterio ILIKE %s
                """, ('%' + pesquisa + '%',))
            else:
                cursor.execute("""
                    SELECT COUNT(*) FROM criterios
                    WHERE ativo = TRUE
                """)
            
            count_result = cursor.fetchone()
            total_criterios = count_result[0] if count_result else 0

            # Calcular o número total de páginas
            total_paginas = (total_criterios + itens_por_pagina - 1) // itens_por_pagina

            # Se a requisição for AJAX, renderizar apenas a tabela de critérios
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':  # Verifica se é uma requisição AJAX
                return render_template('tabela_criterios.html', criterios=criterios, pagina=pagina, total_paginas=total_paginas, pesquisa=pesquisa, itens_por_pagina=itens_por_pagina)

            # Caso contrário, renderizar a página completa
            return render_template('criterios.html', criterios=criterios, pagina=pagina, total_paginas=total_paginas, pesquisa=pesquisa, itens_por_pagina=itens_por_pagina, user_role=session['role'])

        except Exception as e:
            # Caso ocorra algum erro, log o erro para depuração
            print(f"Erro ao realizar a pesquisa: {e}")
            return "Erro na pesquisa, por favor, tente novamente."

    else:
        return redirect(url_for('login'))

    

@app.route('/criar_criterio', methods=['GET', 'POST'])
def criar_criterio():
    if 'loggedin' not in session or session['role'] != 'Administrador':
        return redirect(url_for('login'))

    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    if request.method == 'POST':
        try:
            nome_criterio = request.form['criterio'].strip()
            qtd_maxima_itens = int(request.form['qtd_maxima_itens'])
            pontuacao_item = float(request.form['pontuacao_item'])
            xpath_criterio_lattes = request.form['xpath_criterio_lattes'].strip()
            considera_qualis = request.form.get('considera_qualis') == 'on'
            ativo = request.form.get('ativo') == 'on'

            # Validar dados numéricos
            if qtd_maxima_itens < 0 or pontuacao_item < 0:
                flash('Quantidade máxima de itens e pontuação por item devem ser maiores ou iguais a zero.', 'danger')
                raise ValueError("Valores inválidos.")

            # Inserir o critério
            cursor.execute("""
                INSERT INTO criterios (qtd_maxima_itens, pontuacao_item, criterio, xpath_criterio_lattes, 
                                       considera_qualis, ativo)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (qtd_maxima_itens, pontuacao_item, nome_criterio, xpath_criterio_lattes, considera_qualis, ativo))
            conn.commit()

            flash('Critério criado com sucesso!', 'success')
            return redirect(url_for('criterios'))  # Não precisamos mais passar o filtro do instrumento

        except (psycopg2.Error, ValueError) as e:
            conn.rollback()
            flash(f'Ocorreu um erro ao criar o critério: {str(e)}', 'danger')

    return render_template('criar_criterio.html')



@app.route('/remover_criterio/<int:criterio_id>', methods=['POST'])
def remover_criterio(criterio_id):
    if 'loggedin' not in session or session['role'] != 'Administrador':
        return redirect(url_for('login'))

    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    try:
        # Confirmar se o critério existe
        cursor.execute("SELECT id_criterio FROM criterios WHERE id_criterio = %s", (criterio_id,))
        if not cursor.fetchone():
            flash('Critério não encontrado.', 'danger')
            return redirect(url_for('criterios'))

        # Remover o critério
        cursor.execute("DELETE FROM criterios WHERE id_criterio = %s", (criterio_id,))
        conn.commit()

        flash('Critério removido com sucesso!', 'success')
    except psycopg2.Error as e:
        conn.rollback()
        flash(f'Ocorreu um erro ao remover o critério: {str(e)}', 'danger')

    # Obter o filtro de instrumento do form
    filtro_instrumento = request.form.get('instrumento_filtro', '')
    pagina = request.form.get('pagina', 1)
    itens_por_pagina = request.form.get('itens_por_pagina', 5)

    # Redirecionar para a página de critérios com os filtros aplicados
    return redirect(url_for('criterios', instrumento_filtro=filtro_instrumento, pagina=pagina, itens_por_pagina=itens_por_pagina))


@app.route('/editar_criterio/<int:criterio_id>', methods=['GET', 'POST'])
def editar_criterio(criterio_id):
    if 'loggedin' not in session or session['role'] != 'Administrador':
        return redirect(url_for('login'))

    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    if request.method == 'POST':
        try:
            nome_criterio = request.form['criterio'].strip()
            qtd_maxima_itens = int(request.form['qtd_maxima_itens'])
            pontuacao_item = float(request.form['pontuacao_item'])
            xpath_criterio_lattes = request.form['xpath_criterio_lattes'].strip()
            considera_qualis = request.form.get('considera_qualis') == 'on'
            ativo = request.form.get('ativo') == 'on'

            if qtd_maxima_itens < 0 or pontuacao_item < 0:
                flash('Quantidade máxima de itens e pontuação por item devem ser maiores ou iguais a zero.', 'danger')
                raise ValueError("Valores inválidos.")

            # Atualizando apenas o critério sem modificar o instrumento
            cursor.execute("""
                UPDATE criterios
                SET qtd_maxima_itens = %s, pontuacao_item = %s, criterio = %s, xpath_criterio_lattes = %s, 
                    considera_qualis = %s, ativo = %s
                WHERE id_criterio = %s
            """, (qtd_maxima_itens, pontuacao_item, nome_criterio, xpath_criterio_lattes, considera_qualis, ativo, criterio_id))
            conn.commit()

            flash('Critério atualizado com sucesso!', 'success')
            return redirect(url_for('criterios'))
        except (psycopg2.Error, ValueError) as e:
            conn.rollback()
            flash(f'Ocorreu um erro ao atualizar o critério: {str(e)}', 'danger')

    cursor.execute("SELECT * FROM criterios WHERE id_criterio = %s", (criterio_id,))
    criterio = cursor.fetchone()

    return render_template('editar_criterio.html', criterio=criterio)

@app.route('/associar_criterios', methods=['GET', 'POST'])
def associar_criterios():
    if 'loggedin' not in session or session['role'] != 'Administrador':
        return redirect(url_for('login'))

    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    filtro_instrumento = request.args.get('instrumento_filtro', type=int)

    if filtro_instrumento:
        # Buscar o instrumento específico
        cursor.execute("SELECT * FROM instrumentos_avaliacao WHERE id_instrumento_avaliacao = %s", (filtro_instrumento,))
        instrumento = cursor.fetchone()

        if not instrumento:
            flash('Instrumento de avaliação não encontrado.', 'danger')
            return redirect(url_for('associar_criterios'))

        # Buscar critérios associados ordenados alfabeticamente
        cursor.execute("""
            SELECT rci.id_relacao, c.id_criterio, c.criterio
            FROM criterios c
            JOIN rel_criterios_instrumentos rci ON c.id_criterio = rci.id_criterio
            WHERE rci.id_instrumento_avaliacao = %s
            ORDER BY c.criterio ASC
        """, (filtro_instrumento,))
        criterios_associados = cursor.fetchall()

        # Buscar critérios disponíveis ordenados alfabeticamente
        cursor.execute("""
            SELECT id_criterio, criterio 
            FROM criterios 
            WHERE id_criterio NOT IN (SELECT id_criterio FROM rel_criterios_instrumentos WHERE id_instrumento_avaliacao = %s)
            ORDER BY criterio ASC
        """, (filtro_instrumento,))
        criterios_disponiveis = cursor.fetchall()

        if request.method == 'POST':
            # Adicionar critérios ao instrumento
            criterios_selecionados = request.form.getlist('criterios_id')
            for criterio_id in criterios_selecionados:
                cursor.execute("""
                    INSERT INTO rel_criterios_instrumentos (id_criterio, id_instrumento_avaliacao)
                    VALUES (%s, %s)
                """, (criterio_id, filtro_instrumento))
            conn.commit()
            flash('Critérios associados com sucesso!', 'success')
            return redirect(url_for('associar_criterios', instrumento_filtro=filtro_instrumento))

        return render_template('associar_criterio.html', 
                               criterios_associados=criterios_associados,
                               criterios_disponiveis=criterios_disponiveis, 
                               instrumento=instrumento, 
                               filtro_instrumento=filtro_instrumento)

    # Se nenhum filtro de instrumento foi passado, listar todos os instrumentos de avaliação
    cursor.execute("SELECT * FROM instrumentos_avaliacao")
    instrumentos = cursor.fetchall()
    
    return render_template('associar_criterio.html', instrumentos=instrumentos)


@app.route('/remover_associacao_criterio_instrumento/<int:id_relacao>', methods=['POST'])
def remover_associacao_criterio_instrumento(id_relacao):
    if 'loggedin' not in session or session['role'] != 'Administrador':
        return redirect(url_for('login'))

    cursor = conn.cursor()
    
    # Remove a associação do critério ao instrumento
    cursor.execute("""
        DELETE FROM rel_criterios_instrumentos WHERE id_relacao = %s
    """, (id_relacao,))
    conn.commit()

    flash('Associação removida com sucesso!', 'success')
    return redirect(request.referrer)

    
@app.route('/instrumentos_criterios/<int:instrumento_id>')
def instrumentos_criterios(instrumento_id):
    if 'loggedin' in session and session['role'] == 'Administrador':
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute("""
            SELECT c.criterio, c.qtd_maxima_itens, c.pontuacao_item, c.xpath_criterio_lattes, 
                   c.considera_qualis, c.ativo 
            FROM criterios c
            INNER JOIN rel_criterios_instrumentos rci 
                ON c.id_criterio = rci.id_criterio
            WHERE rci.id_instrumento_avaliacao = %s
        """, (instrumento_id,))
        criterios = cursor.fetchall()

        return render_template('instrumentos_criterios.html', criterios=criterios, instrumento_id=instrumento_id)
    else:
        return redirect(url_for('login'))
    
    
@app.route('/registrar_servidor', methods=['GET', 'POST'])
def registrar_servidor():
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # Obtenha os tipos de servidor do banco de dados (type customizado)
    cursor.execute("SELECT unnest(enum_range(NULL::type_servidor)) AS tipo_servidor")
    tipos_servidor = [row['tipo_servidor'] for row in cursor.fetchall()]

    if request.method == 'POST':
        # Obtenha os dados do formulário
        fullname = request.form.get('fullname')
        matricula = request.form.get('matricula')
        password = request.form.get('password')
        email = request.form.get('email')
        tipo_servidor = request.form.get('tipo_servidor')
        lattes_link = request.form.get('lattes_link')

        # Validações para cada campo
        if not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            flash('Endereço de e-mail inválido!', 'warning')
        elif not re.match(r'^[0-9]+$', matricula):
            flash('Matrícula deve conter apenas números!', 'warning')
        elif not re.match(r'^http://lattes.cnpq.br/\d{16}$', lattes_link):
            flash('Lattes ID inválido!', 'warning')
        else:
            # Se todos os dados forem válidos, insira no banco de dados
            _hashed_password = generate_password_hash(password)
            cursor.execute(
                "INSERT INTO servidores (nome, matricula, senha, e_mail, tipo_servidor, lattes_link) VALUES (%s, %s, %s, %s, %s, %s)",
                (fullname.upper(), matricula, _hashed_password, email, tipo_servidor, lattes_link)
            )
            conn.commit()
            flash('Servidor registrado com sucesso!', 'success')
            return redirect(url_for('listar_servidores'))

    return render_template('registrar_servidor.html', tipos_servidor=tipos_servidor)

@app.route('/servidores', methods=['GET'])
def listar_servidores():
    page = request.args.get('page', 1, type=int)
    per_page = 10  # Número de servidores por página

    # Consulta paginada para obter servidores
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute("SELECT COUNT(*) FROM servidores")
    total_servidores = cursor.fetchone()[0]
    
    cursor.execute(
        "SELECT * FROM servidores ORDER BY id_servidor LIMIT %s OFFSET %s",
        (per_page, (page - 1) * per_page)
    )
    servidores = cursor.fetchall()
    
    # Calcular paginação
    total_pages = (total_servidores + per_page - 1) // per_page
    pagination = {
        'current': page,
        'total_pages': total_pages,
        'has_prev': page > 1,
        'has_next': page < total_pages
    }

    return render_template('servidores.html', servidores=servidores, pagination=pagination)

@app.route('/editar_servidor/<int:id>', methods=['GET', 'POST'])
def editar_servidor(id):
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    # Obtenha dados do servidor para edição
    cursor.execute("SELECT * FROM servidores WHERE id_servidor = %s", (id,))
    servidor = cursor.fetchone()

    # Obtenha tipos de servidor disponíveis
    cursor.execute("SELECT DISTINCT tipo_servidor FROM servidores")
    tipos_servidor = [row['tipo_servidor'] for row in cursor.fetchall()]

    if request.method == 'POST':
        # Dados atualizados do formulário
        fullname = request.form['fullname']
        matricula = request.form['matricula']
        email = request.form['email']
        tipo_servidor = request.form['tipo_servidor']
        lattes_link = request.form['lattes_link']

        cursor.execute("""
            UPDATE servidores
            SET nome = %s, matricula = %s, e_mail = %s, tipo_servidor = %s, lattes_link = %s
            WHERE id_servidor = %s
        """, (fullname, matricula, email, tipo_servidor, lattes_link, id))
        
        conn.commit()
        flash('Servidor atualizado com sucesso!', 'success')
        return redirect(url_for('listar_servidores'))
    
    return render_template('editar_servidor.html', servidor=servidor, tipos_servidor=tipos_servidor)


def verificar_tipo_em_uso(tipo, tipo_table, tipo_coluna):
    cursor = conn.cursor()
    # Utiliza parâmetros para construir a query de forma dinâmica e mais segura
    query = f"SELECT COUNT(*) FROM {tipo_table} WHERE {tipo_coluna} = %s"
    cursor.execute(query, (tipo,))
    count = cursor.fetchone()[0]
    # Retorna True se o tipo estiver em uso, caso contrário, False
    return count > 0

@app.route('/tipos_evento', methods=['GET', 'POST'])
def tipos_evento():
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # Listar tipos de evento
    cursor.execute("SELECT unnest(enum_range(NULL::type_evento)) AS tipo_evento")
    tipos_evento = [row['tipo_evento'] for row in cursor.fetchall()]

    if request.method == 'POST':
        novo_tipo = request.form['novo_tipo']
        # Adiciona o novo tipo ao ENUM, mantendo os existentes
        cursor.execute("ALTER TYPE type_evento ADD VALUE IF NOT EXISTS %s", (novo_tipo,))
        conn.commit()
        flash('Tipo de evento adicionado com sucesso!', 'success')
        return redirect(url_for('tipos_evento'))

    return render_template('tipos_evento.html', tipos_evento=tipos_evento)


@app.route('/editar_tipo_evento', methods=['POST'])
def editar_tipo_evento():
    novo_nome = request.form['novo_nome']
    tipo_antigo = request.form['tipo_antigo']

    cursor = conn.cursor()
    cursor.execute("ALTER TYPE type_evento RENAME VALUE %s TO %s", (tipo_antigo, novo_nome))
    conn.commit()
    flash('Tipo de evento atualizado com sucesso!', 'success')
    return redirect(url_for('tipos_evento'))


@app.route('/deletar_tipo_evento', methods=['POST'])
def deletar_tipo_evento():
    tipo_evento_valor = request.form['tipo_evento']  # Este é o valor do tipo que está sendo excluído
    tipo_evento = 'type_evento'  # Nome real do tipo ENUM no banco de dados
    cursor = conn.cursor()

    # Verificar se o tipo de evento está em uso na tabela de eventos
    if verificar_tipo_em_uso(tipo_evento_valor, 'eventos', 'tipo_evento'):
        flash(f'O tipo de evento "{tipo_evento_valor}" está em uso. Não é possível deletá-lo diretamente. Por favor, atualize os registros antes de tentar novamente.', 'danger')
        return redirect(url_for('tipos_evento'))

    # Obter os valores do tipo ENUM existente
    cursor.execute(f"SELECT unnest(enum_range(NULL::{tipo_evento}))")
    valores_tipo_evento = cursor.fetchall()
    valores_tipo_evento = [v[0] for v in valores_tipo_evento]  # Extrair os valores da tupla

    # Remover o tipo que estamos deletando da lista de valores
    valores_tipo_evento = [v for v in valores_tipo_evento if v != tipo_evento_valor]

    # Criar o novo tipo ENUM com os valores restantes
    novo_tipo = f"{tipo_evento}_temp"
    novo_tipo_valores = ', '.join([f"'{v}'" for v in valores_tipo_evento])
    cursor.execute(f"CREATE TYPE {novo_tipo} AS ENUM ({novo_tipo_valores})")
    conn.commit()

    # Alterar a tabela de eventos para usar o novo tipo (sem remover o tipo antigo ainda)
    cursor.execute(f"ALTER TABLE eventos ALTER COLUMN tipo_evento TYPE {novo_tipo} USING tipo_evento::text::{novo_tipo}")
    conn.commit()

    # Dropar o tipo antigo
    cursor.execute(f"DROP TYPE {tipo_evento}")
    conn.commit()

    # Renomear o tipo novo para o nome do tipo original
    cursor.execute(f"ALTER TYPE {novo_tipo} RENAME TO {tipo_evento}")
    conn.commit()

    flash('Tipo de evento deletado com sucesso!', 'success')
    return redirect(url_for('tipos_evento'))


@app.route('/tipos_servidor', methods=['GET', 'POST'])
def tipos_servidor():
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # Listar tipos de servidor
    cursor.execute("SELECT unnest(enum_range(NULL::type_servidor)) AS tipo_servidor")
    tipos_servidor = [row['tipo_servidor'] for row in cursor.fetchall()]

    if request.method == 'POST':
        novo_tipo = request.form['novo_tipo']
        try:
            # Adiciona o novo tipo ao ENUM, mantendo os existentes
            cursor.execute("ALTER TYPE type_servidor ADD VALUE IF NOT EXISTS %s", (novo_tipo,))
            conn.commit()
            flash('Tipo de servidor adicionado com sucesso!', 'success')
        except Exception as e:
            flash(f"Erro ao adicionar tipo de servidor: {str(e)}", 'danger')
        return redirect(url_for('tipos_servidor'))

    return render_template('tipos_servidor.html', tipos_servidor=tipos_servidor)


@app.route('/editar_tipo_servidor', methods=['POST'])
def editar_tipo_servidor():
    novo_nome = request.form['novo_nome']
    tipo_antigo = request.form['tipo_antigo']

    cursor = conn.cursor()
    try:
        # Renomeia o valor do tipo ENUM
        cursor.execute("ALTER TYPE type_servidor RENAME VALUE %s TO %s", (tipo_antigo, novo_nome))
        conn.commit()
        flash('Tipo de servidor atualizado com sucesso!', 'success')
    except Exception as e:
        flash(f"Erro ao atualizar tipo de servidor: {str(e)}", 'danger')
    return redirect(url_for('tipos_servidor'))


@app.route('/deletar_tipo_servidor', methods=['POST'])
def deletar_tipo_servidor():
    tipo_servidor_valor = request.form['tipo_servidor']  # Este é o valor do tipo que está sendo excluído
    tipo_servidor = 'type_servidor'  # Nome real do tipo ENUM no banco de dados
    cursor = conn.cursor()

    # Verificar se o tipo de servidor está em uso na tabela de servidores
    try:
        if verificar_tipo_em_uso(tipo_servidor_valor, 'servidores', 'tipo_servidor'):
            flash(f'O tipo de servidor "{tipo_servidor_valor}" está em uso. Não é possível deletá-lo diretamente. Por favor, atualize os registros antes de tentar novamente.', 'danger')
            return redirect(url_for('tipos_servidor'))

        # Obter os valores do tipo ENUM existente
        cursor.execute(f"SELECT unnest(enum_range(NULL::{tipo_servidor}))")
        valores_tipo_servidor = cursor.fetchall()
        valores_tipo_servidor = [v[0] for v in valores_tipo_servidor]  # Extrair os valores da tupla

        # Remover o tipo que estamos deletando da lista de valores
        valores_tipo_servidor = [v for v in valores_tipo_servidor if v != tipo_servidor_valor]

        # Criar o novo tipo ENUM com os valores restantes
        novo_tipo = f"{tipo_servidor}_temp"
        novo_tipo_valores = ', '.join([f"'{v}'" for v in valores_tipo_servidor])
        cursor.execute(f"CREATE TYPE {novo_tipo} AS ENUM ({novo_tipo_valores})")
        conn.commit()

        # Alterar a tabela de servidores para usar o novo tipo (sem remover o tipo antigo ainda)
        cursor.execute(f"ALTER TABLE servidores ALTER COLUMN tipo_servidor TYPE {novo_tipo} USING tipo_servidor::text::{novo_tipo}")
        conn.commit()

        # Dropar o tipo antigo
        cursor.execute(f"DROP TYPE {tipo_servidor}")
        conn.commit()

        # Renomear o tipo novo para o nome do tipo original
        cursor.execute(f"ALTER TYPE {novo_tipo} RENAME TO {tipo_servidor}")
        conn.commit()

        flash('Tipo de servidor deletado com sucesso!', 'success')
    except Exception as e:
        flash(f"Erro ao deletar tipo de servidor: {str(e)}", 'danger')

    return redirect(url_for('tipos_servidor'))


if __name__ == "__main__":
    # app.run(debug=True)
    app.run()