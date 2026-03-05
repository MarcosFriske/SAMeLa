#app.py
from flask import Flask, request, session, redirect, url_for, render_template, flash, make_response, send_file, jsonify
from io import BytesIO
from pathlib import Path
import pandas as pd
from datetime import datetime, timedelta
import tempfile
import os
import secrets
import psycopg2 #pip install psycopg2 
import psycopg2.extras
from psycopg2 import errors
import re 
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from lxml import etree
import chardet

#logging
import logging

#reset senha e email
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import random
import string

# carregar variáveis de ambiente
from dotenv import load_dotenv

# script da pontuação
from algoritmoPontuacaoBD import executar_algoritmo
# script de formatar excel e passar para pdf
from preencheTemplateExcel import ExcelTemplatePreencher
# script de criar conta usando o XML do servidor
from registrar_servidor_xml import extrair_dados_lattes

# =========================
# LOAD ENVIRONMENT
# =========================
load_dotenv()

# =========================
# FLASK CONFIG
# =========================
app = Flask(__name__)

app.secret_key = os.getenv("FLASK_SECRET_KEY")

app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(
    minutes=int(os.getenv("SESSION_LIFETIME_MINUTES", 10))
)

COOKIE_TIME_OUT = int(os.getenv("COOKIE_TIMEOUT", 604800))


# =========================
# DATABASE CONFIG
# =========================
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_PORT = os.getenv("DB_PORT", 5432)
 
conn = psycopg2.connect(
    dbname=DB_NAME,
    user=DB_USER,
    password=DB_PASS,
    host=DB_HOST,
    port=DB_PORT
)

# =========================
# EMAIL CONFIG
# =========================
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

APP_BASE_URL = os.getenv("APP_BASE_URL")

### FUNÇÕES

# Função para gerar tokens aleatórios para redefinição de senha
def generate_token():
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(32))

# Função de envio do e-mail para resetar senha
def send_password_reset_email(
        receiver_email: str,
        token: str
    ):
        reset_link = f"{APP_BASE_URL}/reset_password/{token}"
    
        subject = "SAMeLa - Redefinição de Senha"
        body = f"""
Olá,

Recebemos uma solicitação para redefinição de senha da sua conta no sistema SAMeLa.

Para criar uma nova senha, clique no link abaixo:

{reset_link}

Se você não solicitou esta redefinição, ignore este e-mail.

Atenciosamente,
Equipe SAMeLa
"""
        message = MIMEMultipart()
        message["From"] = EMAIL_SENDER
        message["To"] = receiver_email
        message["Subject"] = subject
        message.attach(MIMEText(body, "plain"))
    
        try:

            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
    
                server.starttls()
                server.login(EMAIL_SENDER, EMAIL_PASSWORD)
                server.send_message(message)
    
            print(f"E-mail enviado com sucesso para {receiver_email}")
    
        except Exception as e:
    
            print(f"Erro ao enviar e-mail: {e}")

def send_account_created_email(receiver_email, token):
    
    reset_link = f"{APP_BASE_URL}/reset_password/{token}"

    subject = "SAMeLa - Sua conta foi criada"
    body = f"""
Sua conta no sistema SAMeLa foi criada com sucesso.

Para definir sua senha e acessar o sistema, clique no link abaixo:

{reset_link}

Se você não reconhece este cadastro, ignore este e-mail.
"""

    message = MIMEMultipart()
    message["From"] = EMAIL_SENDER
    message["To"] = receiver_email
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:

        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(message)

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
    try:
        # Login com Lembre-me (Cookies)
        if 'matricula' in request.cookies:
            matricula = request.cookies.get('matricula')
            password = request.cookies.get('senha')
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
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

            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
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

    except Exception as e:
        flash(f'Ocorreu um erro durante o login: {e}', 'danger')
    
    # Paginação dos avisos
    avisos = [
        {"tipo": "info", "mensagem": "O sistema estará indisponível no dia 05/12 das 08:00 às 12:00."},
        {"tipo": "warning", "mensagem": "Atualize sua senha regularmente para maior segurança."},
        {"tipo": "success", "mensagem": "Estamos felizes em tê-lo(a) de volta."},
        {"tipo": "info", "mensagem": "Manutenção programada para o próximo fim de semana."},
        {"tipo": "error", "mensagem": "Erro no sistema detectado."},
    ]

    page = request.args.get('page', 1, type=int)
    per_page = 2
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
    try:
        if request.method == 'POST' and 'password' in request.form and 'email' in request.form:
            fullname = request.form['fullname'].upper()
            matricula = request.form.get('matricula', '').strip()
            password = request.form['password']
            email = request.form['email']
            lattes_link = request.form['lattes_link']
            tipo_servidor = 'Docente'

            _hashed_password = generate_password_hash(password)

            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                if matricula:
                    cursor.execute(
                        'SELECT * FROM servidores WHERE matricula = %s OR e_mail = %s',
                        (matricula, email)
                    )
                else:
                    cursor.execute(
                        'SELECT * FROM servidores WHERE e_mail = %s',
                        (email,)
                    )

                account = cursor.fetchone()

                if account:
                    flash('Essa conta já existe!', 'danger')
                elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
                    flash('Endereço de e-mail inválido!', 'warning')
                elif matricula and not re.match(r'^[0-9]+$', matricula):
                    flash('Matrícula deve conter apenas números!', 'warning')
                elif not re.match(r'^https://lattes.cnpq.br/\d{16}$', lattes_link):
                    flash('Forneça um Lattes iD válido!', 'warning')
                elif not password or not email:
                    flash('Por favor, preencha os campos obrigatórios!', 'warning')
                else:
                    cursor.execute("""
                        INSERT INTO servidores (
                            nome,
                            matricula,
                            senha,
                            e_mail,
                            tipo_servidor,
                            lattes_link
                        )
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (
                        fullname,
                        matricula if matricula else None,
                        _hashed_password,
                        email,
                        tipo_servidor,
                        lattes_link
                    ))
                    conn.commit()
                    flash('Sua conta foi registrada com sucesso!', 'success')
                    return render_template('login.html')

        elif request.method == 'POST':
            flash('Por favor, preencha o formulário corretamente!', 'warning')

    except Exception as e:
        flash(f"Ocorreu um erro durante o registro: {e}", 'danger')

    return render_template('register.html')


@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    try:
        if request.method == 'POST':
            email = request.form.get('email')

            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                cursor.execute('SELECT * FROM servidores WHERE e_mail = %s', (email,))
                user = cursor.fetchone()

                if user:
                    token = generate_token()

                    cursor.execute("UPDATE servidores SET reset_token = %s WHERE id_servidor = %s", (token, user['id_servidor']))
                    conn.commit()

                    send_password_reset_email(email, token)

                    flash('Um e-mail foi enviado com instruções para redefinir sua senha.', 'success')
                    return redirect(url_for('login'))
                else:
                    flash('E-mail não encontrado. Por favor, insira o e-mail cadastrado.', 'warning')
                    return redirect(url_for('login'))

    except Exception as e:
        flash(f"Ocorreu um erro ao solicitar redefinição de senha: {e}", 'danger')

    return render_template('forgot_password.html')


# Rota para a página de redefinição de senha
@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:

            # 🔎 Buscar usuário pelo token
            cursor.execute(
                'SELECT * FROM servidores WHERE reset_token = %s',
                (token,)
            )
            user = cursor.fetchone()

            if not user:
                flash(
                    'Token inválido ou já utilizado. Solicite nova redefinição.',
                    'danger'
                )
                return redirect(url_for('forgot_password'))

            if request.method == 'POST':
                new_password = request.form.get('new_password')
                confirm_password = request.form.get('confirm_password')

                # 🔐 Validações básicas
                if not new_password or not confirm_password:
                    flash('Preencha todos os campos.', 'warning')
                    return render_template('reset_password.html', token=token)

                if new_password != confirm_password:
                    flash('As senhas não coincidem.', 'danger')
                    return render_template('reset_password.html', token=token)

                if len(new_password) < 6:
                    flash('A senha deve ter pelo menos 6 caracteres.', 'warning')
                    return render_template('reset_password.html', token=token)

                # 🔐 Hash seguro
                hashed_password = generate_password_hash(new_password)

                # 🔄 Atualiza senha e remove token
                cursor.execute("""
                    UPDATE servidores
                    SET senha = %s,
                        reset_token = NULL
                    WHERE id_servidor = %s
                """, (hashed_password, user['id_servidor']))

                conn.commit()

                flash('Senha redefinida com sucesso.', 'success')
                return redirect(url_for('login'))

            return render_template('reset_password.html', token=token)

    except Exception as e:
        conn.rollback()
        app.logger.exception(e)
        flash('Erro ao redefinir a senha.', 'danger')
        return redirect(url_for('forgot_password'))
    
@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    try:
        if request.method == 'POST':
            senha_atual = request.form.get('current_password')
            nova_senha = request.form.get('new_password')
            confirmar_senha = request.form.get('confirm_password')

            if not senha_atual or not nova_senha or not confirmar_senha:
                flash('Preencha todos os campos.', 'warning')
                return redirect(url_for('change_password'))

            if nova_senha != confirmar_senha:
                flash('A nova senha e a confirmação não coincidem.', 'danger')
                return redirect(url_for('change_password'))

            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                cursor.execute(
                    'SELECT senha FROM servidores WHERE id_servidor = %s',
                    (session['id'],)
                )
                user = cursor.fetchone()

                if not user or not check_password_hash(user['senha'], senha_atual):
                    flash('Senha atual incorreta.', 'danger')
                    return redirect(url_for('change_password'))

                nova_senha_hash = generate_password_hash(nova_senha)

                cursor.execute("""
                    UPDATE servidores
                    SET senha = %s,
                        reset_token = NULL
                    WHERE id_servidor = %s
                """, (nova_senha_hash, session['id']))

                conn.commit()

            flash('Senha alterada com sucesso!', 'success')
            return redirect(url_for('profile'))

    except Exception as e:
        flash(f'Ocorreu um erro ao alterar a senha: {e}', 'danger')

    return render_template('change_password.html')

@app.route('/upload_xml', methods=['POST'])
def upload_xml():
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    if 'file' not in request.files or request.files['file'].filename == '':
        flash('Nenhum arquivo foi selecionado', 'warning')
        return redirect(url_for('profile'))

    file = request.files['file']
    xml_content = file.read()

    # Detectar codificação do arquivo
    detected = chardet.detect(xml_content)
    detected_encoding = detected['encoding'] or 'utf-8'
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
        data_hora_lattes = datetime.strptime(data_attr + hora_attr, "%d%m%Y%H%M%S")
        print(f"✅ Timestamp convertido: {data_hora_lattes}")
    except ValueError as e:
        flash('Formato de data/hora inválido no XML', 'danger')
        print(f"❌ Erro ao converter data/hora: {e}")
        return redirect(url_for('profile'))

    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            cursor.execute("""
                UPDATE servidores
                SET lattes_xml = %s,
                    ultimo_upload = current_timestamp,
                    data_ultima_atualizacao_lattes = %s
                WHERE id_servidor = %s
            """, (xml_string, data_hora_lattes, session['id']))
            conn.commit()
            flash('Arquivo XML enviado com sucesso', 'success')
    except Exception as e:
        flash('Erro ao salvar os dados no banco', 'danger')
        print(f"❌ Erro no banco de dados: {e}")
        return redirect(url_for('profile'))

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
      
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:

            # ======================
            # ATUALIZAÇÃO DO PERFIL
            # ======================
            if request.method == 'POST':
                nome = request.form['nome'].upper().strip()
                email = request.form['email'].strip()
                matricula = request.form.get('matricula', '').strip()
                lattes_link = request.form['lattes_link'].strip()

                # Validações
                if not nome or not email:
                    flash('Nome e e-mail são obrigatórios.', 'warning')
                    return redirect(url_for('profile'))

                if not re.match(r'[^@]+@[^@]+\.[^@]+', email):
                    flash('E-mail inválido.', 'warning')
                    return redirect(url_for('profile'))

                if matricula and not re.match(r'^[0-9]+$', matricula):
                    flash('Matrícula deve conter apenas números.', 'warning')
                    return redirect(url_for('profile'))

                if not re.match(r'^http://lattes.cnpq.br/\d{16}$', lattes_link):
                    flash('Forneça um Lattes iD válido.', 'warning')
                    return redirect(url_for('profile'))

                # Verifica duplicidade de e-mail ou matrícula
                if matricula:
                    cursor.execute("""
                        SELECT 1 FROM servidores
                        WHERE (e_mail = %s OR matricula = %s)
                        AND id_servidor != %s
                    """, (email, matricula, session['id']))
                else:
                    cursor.execute("""
                        SELECT 1 FROM servidores
                        WHERE e_mail = %s
                        AND id_servidor != %s
                    """, (email, session['id']))

                if cursor.fetchone():
                    flash('E-mail ou matrícula já estão em uso.', 'danger')
                    return redirect(url_for('profile'))

                # Atualiza perfil
                cursor.execute("""
                    UPDATE servidores
                    SET nome = %s,
                        e_mail = %s,
                        matricula = %s,
                        lattes_link = %s
                    WHERE id_servidor = %s
                """, (
                    nome,
                    email,
                    matricula if matricula else None,
                    lattes_link,
                    session['id']
                ))

                conn.commit()
                flash('Perfil atualizado com sucesso!', 'success')
                return redirect(url_for('profile'))

            # ======================
            # CARREGAMENTO DO PERFIL
            # ======================
            cursor.execute(
                'SELECT * FROM servidores WHERE id_servidor = %s',
                (session['id'],)
            )
            account = cursor.fetchone()

    except Exception as e:
        flash('Erro ao carregar ou atualizar o perfil.', 'danger')
        print(f"❌ Erro no perfil: {e}")
        return redirect(url_for('login'))

    if not account:
        flash('Conta não encontrada.', 'warning')
        return redirect(url_for('login'))

    return render_template(
        'profile.html',
        account=account,
        now=datetime.now()
    )


@app.route('/eventos')
def eventos():
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
        # Agora fazemos LEFT JOIN para pegar o nome do instrumento
        cursor.execute("""
            SELECT e.*, i.nome AS nome_instrumento
            FROM eventos e
            LEFT JOIN instrumentos_avaliacao i 
              ON e.fk_id_instrumento_avaliacao = i.id_instrumento_avaliacao
            WHERE e.ativo = true 
              AND e.data_fim >= CURRENT_DATE
            ORDER BY e.data_fim ASC
        """)
        eventos = cursor.fetchall()

        # Consulta dos instrumentos permanece igual
        cursor.execute('SELECT * FROM instrumentos_avaliacao')
        instrumentos = cursor.fetchall()

        # Pegando os tipos de evento do enum do banco
        cursor.execute('SELECT unnest(enum_range(NULL::type_evento))')
        tipos_evento = [item for sublist in cursor.fetchall() for item in sublist]

    return render_template(
        'eventos.html', 
        eventos=eventos, 
        user_role=session['role'], 
        instrumentos=instrumentos, 
        tipos_evento=tipos_evento, 
        eventos_ativos=bool(eventos)
    )


@app.route('/avaliacoes')
def avaliacoes():
    if 'loggedin' not in session or session.get('role') != 'Docente':
        return redirect(url_for('login'))

    current_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            cursor.execute('''
                SELECT a.id_avaliacao, a.data_avaliacao, e.identificacao, e.localizacao
                FROM avaliacao a
                JOIN eventos e ON a.fk_id_evento = e.id_evento
                WHERE a.fk_id_servidor = %s AND e.data_fim >= %s
                ORDER BY a.data_avaliacao ASC
            ''', (session['id'], current_datetime))
            eventos_inscritos = cursor.fetchall()
    except Exception as e:
        flash('Erro ao carregar avaliações.', 'danger')
        print(f"❌ Erro ao consultar avaliações: {e}")
        eventos_inscritos = []

    return render_template('avaliacoes.html', eventos_inscritos=eventos_inscritos)


@app.route('/criar_evento', methods=['POST'])
def criar_evento():
    if 'loggedin' not in session or session.get('role') != 'Administrador':
        return redirect(url_for('login'))

    try:
        identificacao = request.form.get('identificacao', '').strip()
        tipo_evento = request.form.get('tipo_evento', '').strip()
        data_inicio = request.form.get('data_inicio')
        data_fim = request.form.get('data_fim')
        localizacao = request.form.get('localizacao', '').strip()
        descricao = request.form.get('descricao', '').strip()
        
        # Pode vir como string vazia, tratamos como None
        id_instrumento_avaliacao = request.form.get('fk_id_instrumento_avaliacao') or None

        data_criacao = datetime.now()
        data_atualizacao = datetime.now()

        print("🔍 Valor recebido do formulário:", id_instrumento_avaliacao)

        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO eventos (
                    identificacao, tipo_evento, data_inicio, data_fim, 
                    localizacao, descricao, data_criacao, data_atualizacao, 
                    fk_id_instrumento_avaliacao
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                identificacao, tipo_evento, data_inicio, data_fim, 
                localizacao, descricao, data_criacao, data_atualizacao, 
                id_instrumento_avaliacao
            ))
            conn.commit()

        flash('✅ Novo evento criado com sucesso!', 'success')

    except psycopg2.Error as e:
        conn.rollback()
        flash(f'❌ Ocorreu um erro ao criar o evento: {str(e)}', 'danger')

    return redirect(url_for('eventos'))


@app.route('/remover_evento/<int:evento_id>', methods=['POST'])
def remover_evento(evento_id):
    if 'loggedin' not in session or session.get('role') != 'Administrador':
        return redirect(url_for('login'))

    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM eventos WHERE id_evento = %s", (evento_id,))
            conn.commit()

        flash('✅ Evento removido com sucesso!', 'success')

    except psycopg2.Error as e:
        conn.rollback()
        flash(f'❌ Erro ao remover o evento: {str(e)}', 'danger')

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
            id_instrumento_avaliacao = request.form.get('fk_id_instrumento_avaliacao')

            with conn:
                with conn.cursor() as cursor:

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
                    """, (
                        identificacao,
                        tipo_evento,
                        data_inicio,
                        data_fim,
                        localizacao,
                        descricao,
                        id_instrumento_avaliacao,
                        evento_id
                    ))

            flash('Evento atualizado com sucesso!', 'success')
            return redirect(url_for('eventos'))

        except Exception as e:
            flash(f'Ocorreu um erro ao atualizar o evento: {str(e)}', 'danger')

    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:

        # Buscar evento
        cursor.execute("""
            SELECT *
            FROM eventos
            WHERE id_evento = %s
        """, (evento_id,))
        evento = cursor.fetchone()

        # Buscar instrumentos
        cursor.execute("""
            SELECT id_instrumento_avaliacao, nome
            FROM instrumentos_avaliacao
            ORDER BY nome
        """)
        instrumentos = cursor.fetchall()

        criterios_disponiveis = []

        # Buscar critérios do instrumento associado ao evento
        if evento and evento['fk_id_instrumento_avaliacao']:

            cursor.execute("""
                SELECT
                    c.id_criterio,
                    c.criterio,
                    c.pontuacao_item,
                    c.qtd_maxima_itens
                FROM criterios c
                JOIN rel_criterios_instrumentos rci
                    ON rci.id_criterio = c.id_criterio
                WHERE rci.id_instrumento_avaliacao = %s
                AND c.ativo = TRUE
                ORDER BY c.criterio
            """, (evento['fk_id_instrumento_avaliacao'],))

            criterios_disponiveis = cursor.fetchall()

        # Tipos de evento (ENUM)
        cursor.execute("""
            SELECT unnest(enum_range(NULL::type_evento))
        """)
        tipos_evento = [row[0] for row in cursor.fetchall()]

    return render_template(
        'editar_evento.html',
        evento=evento,
        criterios=criterios_disponiveis,
        tipos_evento=tipos_evento,
        instrumentos=instrumentos
    )


@app.route('/api/criterios_por_instrumento/<int:instrumento_id>')
def api_criterios_por_instrumento(instrumento_id):

    if 'loggedin' not in session:
        return jsonify({"erro": "não autorizado"}), 403

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:

        cursor.execute("""
            SELECT
                c.id_criterio,
                c.criterio,
                c.pontuacao_item,
                c.qtd_maxima_itens
            FROM criterios c
            INNER JOIN rel_criterios_instrumentos rci
                ON rci.id_criterio = c.id_criterio
            WHERE rci.id_instrumento_avaliacao = %s
            AND c.ativo = TRUE
            ORDER BY c.criterio
        """, (instrumento_id,))

        criterios = cursor.fetchall()

    return jsonify(criterios)



@app.route('/inscrever_evento', methods=['POST'])
def inscrever_evento():
    if 'loggedin' not in session or session['role'] != 'Docente':
        return redirect(url_for('login'))

    evento_id = request.form.get('evento_id')
    if not evento_id:
        flash('Evento inválido.', 'danger')
        return redirect(url_for('eventos'))

    with conn.cursor() as cursor:
        # Verifica se já existe inscrição para o período do evento
        cursor.execute('''
            SELECT 1 FROM avaliacao 
            WHERE fk_id_servidor = %s AND fk_id_evento = %s 
              AND data_avaliacao BETWEEN 
                (SELECT data_inicio FROM eventos WHERE id_evento = %s) 
                AND 
                (SELECT data_fim FROM eventos WHERE id_evento = %s)
        ''', (session['id'], evento_id, evento_id, evento_id))
        if cursor.fetchone():
            flash('Você já está inscrito neste evento.', 'warning')
            return redirect(url_for('eventos'))

        # Busca XML e data de atualização do Lattes
        cursor.execute('''
            SELECT lattes_xml, data_ultima_atualizacao_lattes 
            FROM servidores 
            WHERE id_servidor = %s
        ''', (session['id'],))
        lattes_info = cursor.fetchone()

        if not lattes_info or not lattes_info[0]:
            flash('Não há XML de Lattes associado ao seu perfil. Acesse seu perfil e envie o XML do Lattes para participar.', 'danger')
            return redirect(url_for('eventos'))

        data_atualizacao_lattes = lattes_info[1]

        # Busca local do evento, limite de meses e instrumento de avaliação
        cursor.execute('''
            SELECT localizacao, meses_maximos_desde_atualizacao_lattes, fk_id_instrumento_avaliacao 
            FROM eventos 
            WHERE id_evento = %s
        ''', (evento_id,))
        evento_info = cursor.fetchone()

        if not evento_info:
            flash('Evento não encontrado.', 'danger')
            return redirect(url_for('eventos'))

        localizacao_do_evento = evento_info[0]
        meses_maximos = evento_info[1] or 6  # fallback para 6 meses se não definido
        instrumento_avaliacao_id = str(evento_info[2]) if evento_info[2] else None

        if not data_atualizacao_lattes:
            flash('Data de atualização do Lattes não encontrada. Atualize seu XML na página de perfil.', 'danger')
            return redirect(url_for('eventos'))

        # Verifica limite de atualização do Lattes (corrigido)
        delta_dias = (datetime.now().date() - data_atualizacao_lattes.date()).days
        delta_meses = delta_dias // 30  # Aproximação por mês

        if delta_meses > meses_maximos:
            flash(f'Seu currículo Lattes está desatualizado há {delta_meses} meses. O máximo permitido para este evento é {meses_maximos} meses. Atualize seu XML na página de perfil para se inscrever.', 'danger')
            return redirect(url_for('eventos'))

        # Cria registro de avaliação
        cursor.execute('''
            INSERT INTO avaliacao (organizacao, data_avaliacao, fk_id_servidor, fk_id_evento) 
            VALUES (%s, NOW(), %s, %s)
        ''', (localizacao_do_evento, session['id'], evento_id))
        conn.commit()

        # Busca ID da avaliação recém-criada
        cursor.execute('''
            SELECT id_avaliacao 
            FROM avaliacao 
            WHERE fk_id_servidor = %s AND fk_id_evento = %s 
            ORDER BY id_avaliacao DESC 
            LIMIT 1
        ''', (session['id'], evento_id))
        avaliacao_result = cursor.fetchone()
        if not avaliacao_result:
            flash('Erro ao registrar a avaliação.', 'danger')
            return redirect(url_for('eventos'))

        id_avaliacao = avaliacao_result[0]

    # Executa algoritmo fora do bloco `with`
    df_avaliacao = executar_algoritmo(id_servidor=session['id'], instrumento_avaliacao_id=instrumento_avaliacao_id)
    if df_avaliacao is None:
        flash('Erro ao gerar dados de avaliação.', 'danger')
        return redirect(url_for('eventos'))

    with conn.cursor() as cursor:
        for _, row in df_avaliacao.iterrows():
            cursor.execute('''
                INSERT INTO avaliacao_dados (
                    fk_id_avaliacao, item, criterios, 
                    pontuacao_por_item, pontuacao_maxima, 
                    quantidade, pontuacao_atingida
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (
                id_avaliacao, row['item'], row['criterios'],
                row['pontuacao_por_item'], row['pontuacao_maxima'],
                row['quantidade'], row['pontuacao_atingida']
            ))
        conn.commit()

        # Atualiza total de pontuação
        cursor.execute('''
            SELECT SUM(pontuacao_atingida) 
            FROM avaliacao_dados 
            WHERE fk_id_avaliacao = %s
        ''', (id_avaliacao,))
        soma_pontuacao = cursor.fetchone()[0] or 0

        cursor.execute('''
            UPDATE avaliacao 
            SET pontuacao = %s 
            WHERE id_avaliacao = %s
        ''', (soma_pontuacao, id_avaliacao))
        conn.commit()

    flash('Inscrição realizada com sucesso!', 'success')
    return redirect(url_for('avaliacoes'))

    
@app.route('/detalhes_avaliacao/<int:avaliacao_id>', methods=['GET'])
def detalhes_avaliacao(avaliacao_id):
    if 'loggedin' not in session or session.get('role') not in ('Docente', 'Administrador'):
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

@app.route('/download_avaliacao_pdf/<int:id_avaliacao>/<int:id_docente>')
def download_avaliacao_pdf(id_avaliacao, id_docente):

    if 'loggedin' not in session or session.get('role') not in ('Docente', 'Administrador'):
        flash('Acesso negado.', 'danger')
        return redirect(url_for('login'))

    query = """
        SELECT * 
        FROM avaliacao_dados 
        WHERE fk_id_avaliacao = %s 
        ORDER BY item ASC
    """

    df_avaliacao = pd.read_sql_query(query, conn, params=(id_avaliacao,))

    if df_avaliacao.empty:
        flash('Nenhum dado encontrado para esta avaliação.', 'warning')

        if session['role'] == 'Administrador':
            return redirect(url_for('admin_avaliacoes'))
        else:
            return redirect(url_for('avaliacoes'))

    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            s.nome AS nome_docente,
            s.lattes_link,
            e.identificacao AS nome_evento,
            e.data_inicio,
            e.data_fim,
            i.nome AS instrumento_nome
        FROM avaliacao a
        JOIN servidores s
            ON s.id_servidor = a.fk_id_servidor
        JOIN eventos e
            ON e.id_evento = a.fk_id_evento
        JOIN instrumentos_avaliacao i
            ON i.id_instrumento_avaliacao = e.fk_id_instrumento_avaliacao
        WHERE a.id_avaliacao = %s
    """, (id_avaliacao,))

    info = cursor.fetchone()

    if not info:
        flash('Erro ao localizar informações do evento/servidor.', 'danger')

        if session['role'] == 'Administrador':
            return redirect(url_for('admin_avaliacoes'))
        else:
            return redirect(url_for('avaliacoes'))

    dados_header = {
        "{{NOME_EDITAL}}": info[2] if info[2] else "Edital",
        "{{COORDENADOR_PROJETO}}": info[0],
        "{{LINK_CURRICULO_LATTES}}": info[1] or "",
        "{{DATA_INICIO_EVENTO}}": info[3].strftime("%d/%m/%Y") if info[3] else "",
        "{{DATA_FIM_EVENTO}}": info[4].strftime("%d/%m/%Y") if info[4] else "",
    }

    criterios = []

    for _, row in df_avaliacao.iterrows():
        criterios.append({
            "NUMERO": int(row["item"]) + 1 if row["item"] is not None else 0,
            "CRITERIO": row["criterios"] or "",
            "PONTOS": float(row["pontuacao_por_item"]) if row["pontuacao_por_item"] else 0.0,
            "MAX_ITENS": float(row["pontuacao_maxima"]) if row["pontuacao_maxima"] else 0.0,
            "TOTAL_MAX": int(row["quantidade"]) if row["quantidade"] else 0,
        })

    tpl_path = Path("static/files/master_file.xlsx")

    pre = ExcelTemplatePreencher(tpl_path)

    pre.substituir_placeholders(dados_header)
    pre.preencher_criterios(criterios)

    img = pre.gerar_imagem_em_memoria()

    fragmentos = pre.gerar_fragmentos_a4(img)

    logo_path = Path("static/images/logo_estado.png")

    pdf_bytes = ExcelTemplatePreencher.gerar_pdf_em_memoria(fragmentos, logo_path)

    # IMPORTANTE para arquivos em memória
    pdf_bytes.seek(0)

    pdf_filename = f"avaliacao_{id_avaliacao}_{id_docente}.pdf"

    return send_file(
        pdf_bytes,
        mimetype="application/pdf",
        as_attachment=True,
        attachment_filename=pdf_filename
    )


    
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

    # ==============================
    # Buscar tipos de servidor
    # ==============================
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
        cursor.execute("SELECT unnest(enum_range(NULL::type_servidor)) AS tipo_servidor")
        tipos_servidor = [row['tipo_servidor'] for row in cursor.fetchall()]

    if request.method == 'POST':

        fullname = request.form.get('fullname', '').strip()
        matricula = request.form.get('matricula', '').strip()
        password = request.form.get('password', '').strip()
        email = request.form.get('email', '').strip().lower()
        tipo_servidor = request.form.get('tipo_servidor')
        lattes_link = request.form.get('lattes_link', '').strip()

        # ==============================
        # Validações
        # ==============================

        if not fullname:
            flash('Nome é obrigatório.', 'warning')
            return render_template('registrar_servidor.html', tipos_servidor=tipos_servidor)

        if not re.match(r'^[0-9]+$', matricula):
            flash('Matrícula deve conter apenas números.', 'warning')
            return render_template('registrar_servidor.html', tipos_servidor=tipos_servidor)

        if not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            flash('Endereço de e-mail inválido.', 'warning')
            return render_template('registrar_servidor.html', tipos_servidor=tipos_servidor)

        if not re.match(r'^https://lattes.cnpq.br/\d{16}$', lattes_link):
            flash('Link do Lattes inválido.', 'warning')
            return render_template('registrar_servidor.html', tipos_servidor=tipos_servidor)

        # ==============================
        # Verificação prévia duplicidade
        # ==============================

        with conn.cursor() as cursor:

            cursor.execute(
                "SELECT 1 FROM servidores WHERE e_mail = %s",
                (email,)
            )
            if cursor.fetchone():
                flash('Este e-mail já está cadastrado.', 'warning')
                return render_template('registrar_servidor.html', tipos_servidor=tipos_servidor)

            cursor.execute(
                "SELECT 1 FROM servidores WHERE matricula = %s",
                (matricula,)
            )
            if cursor.fetchone():
                flash('Esta matrícula já está cadastrada.', 'warning')
                return render_template('registrar_servidor.html', tipos_servidor=tipos_servidor)

        try:

            # ==============================
            # CASO 1 — SENHA INFORMADA
            # ==============================
            if password:

                if len(password) < 6:
                    flash('A senha deve possuir ao menos 6 caracteres.', 'warning')
                    return render_template('registrar_servidor.html', tipos_servidor=tipos_servidor)

                senha_hash = generate_password_hash(password)

                with conn.cursor() as cursor:

                    cursor.execute("""
                        INSERT INTO servidores
                        (nome, matricula, senha, e_mail, tipo_servidor, lattes_link)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (
                        fullname.upper(),
                        matricula,
                        senha_hash,
                        email,
                        tipo_servidor,
                        lattes_link
                    ))

                    conn.commit()

                flash('Servidor administrativo registrado com sucesso.', 'success')
                return redirect(url_for('listar_servidores'))

            # ==============================
            # CASO 2 — PRIMEIRO ACESSO (SEM SENHA)
            # ==============================
            else:

                senha_temporaria = secrets.token_urlsafe(16)
                senha_hash = generate_password_hash(senha_temporaria)

                reset_token = secrets.token_urlsafe(32)

                with conn.cursor() as cursor:

                    cursor.execute("""
                        INSERT INTO servidores
                        (nome, matricula, senha, e_mail, tipo_servidor, lattes_link, reset_token)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (
                        fullname.upper(),
                        matricula,
                        senha_hash,
                        email,
                        tipo_servidor,
                        lattes_link,
                        reset_token
                    ))

                    conn.commit()

                # enviar e-mail
                send_account_created_email(email, reset_token)

                flash(
                    f'Servidor cadastrado. Um e-mail foi enviado para {email} para definir a senha.',
                    'success'
                )

                return redirect(url_for('listar_servidores'))

        except psycopg2.errors.UniqueViolation as e:

            conn.rollback()

            if 'servidores_email_unique' in str(e):
                flash('Este e-mail já está cadastrado.', 'warning')
            elif 'servidores_matricula_unique' in str(e):
                flash('Esta matrícula já está cadastrada.', 'warning')
            else:
                flash('Registro duplicado.', 'warning')

        except Exception as e:

            conn.rollback()
            app.logger.exception(e)
            flash('Erro interno ao registrar servidor.', 'danger')

    return render_template(
        'registrar_servidor.html',
        tipos_servidor=tipos_servidor
    )


@app.route('/servidores', methods=['GET'])
def listar_servidores():
    page = request.args.get('page', 1, type=int)
    per_page = 10

    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
        cursor.execute("SELECT COUNT(*) FROM servidores")
        total_servidores = cursor.fetchone()[0]

        cursor.execute(
            "SELECT * FROM servidores ORDER BY id_servidor LIMIT %s OFFSET %s",
            (per_page, (page - 1) * per_page)
        )
        servidores = cursor.fetchall()

    total_pages = (total_servidores + per_page - 1) // per_page

    pagination = {
        'current': page,
        'total_pages': total_pages,
        'has_prev': page > 1,
        'has_next': page < total_pages
    }

    return render_template(
        'servidores.html',
        servidores=servidores,
        pagination=pagination
    )

@app.route('/registrar_servidor_xml', methods=['GET', 'POST'])
def registrar_servidor_xml():
    if 'loggedin' not in session or session['role'] != 'Administrador':
        return redirect(url_for('login'))

    if request.method == 'POST':
        file = request.files.get('xml')

        if not file or not file.filename.lower().endswith('.xml'):
            flash('Envie um arquivo XML válido do Lattes.', 'warning')
            return redirect(request.url)

        os.makedirs('temp', exist_ok=True)
        temp_path = os.path.join('temp', secure_filename(file.filename))
        file.save(temp_path)

        try:
            dados = extrair_dados_lattes(temp_path)

            if not dados['cpf'] or not dados['nome'] or not dados['lattes_link']:
                flash('XML inválido: dados essenciais ausentes.', 'danger')
                return redirect(request.url)

            # 🔐 Senha temporária (usuário não sabe)
            senha_temporaria = secrets.token_urlsafe(16)
            senha_hash = generate_password_hash(senha_temporaria)

            # 🔑 Token para primeiro acesso
            reset_token = secrets.token_urlsafe(32)
            data_upload = datetime.now()
            
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO servidores
                        (nome, cpf, e_mail, senha, tipo_servidor,
                         lattes_link, lattes_xml,
                         data_ultima_atualizacao_lattes,
                         ultimo_upload,
                         reset_token)
                    VALUES (%s, %s, %s, %s, %s, %s, %s::xml, %s, %s, %s)
                    RETURNING id_servidor
                """, (
                    dados['nome'],
                    dados['cpf'],
                    dados['email'],
                    senha_hash,
                    'Docente',
                    dados['lattes_link'],
                    dados['xml_text'],
                    dados['data_lattes'],
                    data_upload,
                    reset_token
                ))

                id_servidor = cursor.fetchone()[0]
                conn.commit()

            # 📧 Enviar e-mail com link de definição de senha
            send_account_created_email(dados['email'], reset_token)

            flash(
                f'Servidor cadastrado com sucesso. '
                f'E-mail enviado para {dados["email"]}.',
                'success'
            )

            return redirect(url_for('listar_servidores'))

        except psycopg2.errors.UniqueViolation:
            conn.rollback()
            flash('Já existe um servidor cadastrado com este CPF ou e-mail.', 'warning')

        except Exception as e:
            conn.rollback()
            app.logger.exception(e)
            flash('Erro ao processar o XML.', 'danger')

        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    return render_template('registrar_servidor_xml.html')

@app.route('/completar_servidor_xml', methods=['GET', 'POST'])
def completar_servidor_xml():
    if 'loggedin' not in session or session['role'] != 'Administrador':
        return redirect(url_for('login'))

    id_servidor = session.get('servidor_pendente_email')
    if not id_servidor:
        return redirect(url_for('listar_servidores'))

    if request.method == 'POST':
        email = request.form.get('email')

        if not email:
            flash('E-mail é obrigatório.', 'danger')
            return redirect(request.url)

        reset_token = secrets.token_urlsafe(32)

        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE servidores
                SET e_mail = %s,
                    reset_token = %s
                WHERE id_servidor = %s
            """, (email, reset_token, id_servidor))

            conn.commit()

        send_account_created_email(email, reset_token)

        session.pop('servidor_pendente_email', None)

        flash(
            'Cadastro concluído. O servidor receberá um e-mail para definir a senha.',
            'success'
        )
        return redirect(url_for('listar_servidores'))

    return render_template('completar_servidor_xml.html')

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

@app.route('/deletar_servidor/<int:id>', methods=['POST'])
def deletar_servidor(id):
    try:
        # Verifica permissão
        if session.get('role') != 'Administrador':
            flash('Você não tem permissão para realizar esta ação.', 'danger')
            return redirect(url_for('home'))

        # Evita que admin delete a si mesmo
        if session.get('id_servidor') == id:
            flash('Você não pode excluir sua própria conta enquanto estiver logado.', 'warning')
            return redirect(url_for('editar_servidor', id=id))

        with conn.cursor() as cursor:
            cursor.execute(
                'DELETE FROM servidores WHERE id_servidor = %s',
                (id,)
            )
            conn.commit()

        flash('Servidor excluído com sucesso!', 'success')
        return redirect(url_for('listar_servidores'))  # ajuste para sua rota real

    except Exception as e:
        conn.rollback()
        flash(f'Ocorreu um erro ao excluir: {e}', 'danger')
        return redirect(url_for('editar_servidor', id=id))


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


@app.route('/admin/avaliacoes')
def admin_avaliacoes():

    if 'loggedin' not in session or session.get('role') != 'Administrador':
        flash("Acesso negado.", "danger")
        return redirect(url_for('login'))

    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            a.id_avaliacao,
            s.nome,
            e.identificacao,
            e.data_inicio,
            e.data_fim
        FROM avaliacao a
        JOIN servidores s ON s.id_servidor = a.fk_id_servidor
        JOIN eventos e ON e.id_evento = a.fk_id_evento
        ORDER BY a.id_avaliacao DESC
    """)

    avaliacoes = cursor.fetchall()

    return render_template(
        "admin_avaliacoes.html",
        avaliacoes=avaliacoes
    )

@app.route('/admin/avaliacoes/<int:id_evento>')
def admin_avaliacoes_evento(id_evento):

    if 'loggedin' not in session or session['role'] != 'Administrador':
        return redirect(url_for('login'))

    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:

        cursor.execute("""
            SELECT
                s.id_servidor,
                s.nome,
                s.matricula,
                a.id_avaliacao,
                a.pontuacao_total,
                a.data_avaliacao
            FROM avaliacao a
            JOIN servidores s
                ON s.id_servidor = a.fk_id_servidor
            WHERE a.fk_id_evento = %s
            ORDER BY s.nome
        """, (id_evento,))

        avaliacoes = cursor.fetchall()

        cursor.execute("""
            SELECT nome_evento, ano_evento
            FROM eventos
            WHERE id_evento = %s
        """, (id_evento,))

        evento = cursor.fetchone()

    return render_template(
        'admin_avaliacoes_evento.html',
        avaliacoes=avaliacoes,
        evento=evento
    )


@app.route('/admin/detalhes_avaliacao/<int:avaliacao_id>')
def admin_detalhes_avaliacao(avaliacao_id):

    if 'loggedin' not in session or session.get('role') != 'Administrador':
        flash("Acesso negado.", "danger")
        return redirect(url_for('login'))

    cursor = conn.cursor()

    # Dados detalhados da avaliação
    cursor.execute("""
        SELECT *
        FROM avaliacao_dados
        WHERE fk_id_avaliacao = %s
        ORDER BY item ASC
    """, (avaliacao_id,))

    dados = cursor.fetchall()

    # Buscar docente e ID do docente
    cursor.execute("""
        SELECT 
            s.id_servidor,
            s.nome
        FROM avaliacao a
        JOIN servidores s 
            ON s.id_servidor = a.fk_id_servidor
        WHERE a.id_avaliacao = %s
    """, (avaliacao_id,))

    docente_info = cursor.fetchone()

    id_docente = None
    nome_docente = "Docente"

    if docente_info:
        id_docente = docente_info[0]
        nome_docente = docente_info[1]

    cursor.close()

    return render_template(
        "admin_detalhes_avaliacao.html",
        dados=dados,
        avaliacao_id=avaliacao_id,
        docente=nome_docente,
        id_docente=id_docente
    )


@app.route('/admin/rankings')
def admin_rankings():

    if 'loggedin' not in session or session.get('role') != 'Administrador':
        flash("Acesso negado.", "danger")
        return redirect(url_for('login'))

    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:

        cursor.execute("""
            SELECT
                id_evento,
                identificacao,
                data_inicio,
                data_fim
            FROM eventos
            ORDER BY data_inicio DESC
        """)

        eventos = cursor.fetchall()

    return render_template(
        "admin_rankings.html",
        eventos=eventos
    )

@app.route('/admin/ranking_evento/<int:id_evento>')
def admin_ranking_evento(id_evento):

    if 'loggedin' not in session or session.get('role') != 'Administrador':
        flash("Acesso negado.", "danger")
        return redirect(url_for('login'))

    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:

        cursor.execute("""
            SELECT
                s.id_servidor,
                s.nome,
                s.matricula,
                a.id_avaliacao,

                SUM(ad.pontuacao_atingida) AS pontuacao_total,

                RANK() OVER (
                    ORDER BY SUM(ad.pontuacao_atingida) DESC
                ) AS posicao

            FROM avaliacao a

            JOIN servidores s
                ON s.id_servidor = a.fk_id_servidor

            JOIN avaliacao_dados ad
                ON ad.fk_id_avaliacao = a.id_avaliacao

            WHERE a.fk_id_evento = %s

            GROUP BY
                s.id_servidor,
                s.nome,
                s.matricula,
                a.id_avaliacao

            ORDER BY pontuacao_total DESC
        """, (id_evento,))

        ranking = cursor.fetchall()

        cursor.execute("""
            SELECT identificacao, data_inicio, data_fim
            FROM eventos
            WHERE id_evento = %s
        """, (id_evento,))

        evento = cursor.fetchone()

    return render_template(
        "admin_ranking_evento.html",
        ranking=ranking,
        evento=evento,
        id_evento=id_evento
    )

if __name__ == "__main__":
    # app.run(host="127.0.0.1", port=5000, debug=True)
    app.run(host='127.0.0.1', port=5000)