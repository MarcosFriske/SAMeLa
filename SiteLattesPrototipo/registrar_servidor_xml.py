import xml.etree.ElementTree as ET
from datetime import datetime
import re


def extrair_dados_lattes(xml_path: str) -> dict:
    with open(xml_path, 'rb') as f:
        xml_bytes = f.read()

    xml_text = xml_bytes.decode('utf-8', errors='replace')
    root = ET.fromstring(xml_text)

    # ==============================
    # Identificador Lattes
    # ==============================
    numero_lattes = root.attrib.get('NUMERO-IDENTIFICADOR')
    if not numero_lattes:
        raise ValueError('Número identificador do Lattes não encontrado.')

    lattes_link = f'http://lattes.cnpq.br/{numero_lattes}'

    # ==============================
    # Dados Gerais
    # ==============================
    dados_gerais = root.find('DADOS-GERAIS')
    if dados_gerais is None:
        raise ValueError('DADOS-GERAIS não encontrados.')

    nome = dados_gerais.attrib.get('NOME-COMPLETO')
    cpf = dados_gerais.attrib.get('CPF')

    if not nome or not cpf:
        raise ValueError('Nome ou CPF não encontrados.')

    nome = nome.strip().upper()
    cpf = cpf.strip()

    # ==============================
    # Data última atualização
    # ==============================
    data_lattes = None
    data_atualizacao = dados_gerais.attrib.get('DATA-ATUALIZACAO')

    if data_atualizacao:
        try:
            data_lattes = datetime.strptime(data_atualizacao, '%d%m%Y')
        except ValueError:
            pass

    # ==============================
    # Extração de E-mail (com prioridade)
    # ==============================
    email = None

    # 1️⃣ Profissional
    prof = root.find('.//ENDERECO-PROFISSIONAL')
    if prof is not None:
        email_prof = prof.attrib.get('E-MAIL')
        if email_prof and email_prof.strip():
            email = email_prof.strip()
    
    # 2️⃣ Residencial
    if not email:
        res = root.find('.//ENDERECO-RESIDENCIAL')
        if res is not None:
            email_res = res.attrib.get('E-MAIL')
            if email_res and email_res.strip():
                email = email_res.strip()
    
    # 3️⃣ Atributo ELETRONICO
    if not email:
        endereco = root.find('.//ENDERECO')
        if endereco is not None:
            email_eletronico = endereco.attrib.get('ELETRONICO')
            if email_eletronico and email_eletronico.strip():
                email = email_eletronico.strip()

    # ==============================
    # Normalização e validação
    # ==============================
    if email:
        email = email.lower()

        # validação simples de formato
        if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
            email = None

    # Se ainda não encontrou e-mail, deixa explícito
    if not email:
        raise ValueError('Nenhum e-mail válido encontrado no XML.')

    return {
        'nome': nome,
        'cpf': cpf,
        'email': email,
        'lattes_link': lattes_link,
        'xml_text': xml_text,
        'data_lattes': data_lattes
    }