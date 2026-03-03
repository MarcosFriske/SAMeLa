# -*- coding: utf-8 -*-
"""
Created on Fri Dec 19 09:19:26 2025

@author: Marcos
"""

import xml.etree.ElementTree as ET
from datetime import datetime

def extrair_dados_lattes(xml_path: str) -> dict:
    with open(xml_path, 'rb') as f:
        xml_bytes = f.read()

    xml_text = xml_bytes.decode('utf-8', errors='replace')

    root = ET.fromstring(xml_text)

    numero_lattes = root.attrib.get('NUMERO-IDENTIFICADOR')
    if not numero_lattes:
        raise ValueError('Número identificador do Lattes não encontrado.')

    lattes_link = f'http://lattes.cnpq.br/{numero_lattes}'

    dados_gerais = root.find('DADOS-GERAIS')
    if dados_gerais is None:
        raise ValueError('DADOS-GERAIS não encontrados.')

    nome = dados_gerais.attrib.get('NOME-COMPLETO')
    cpf = dados_gerais.attrib.get('CPF')

    if not nome or not cpf:
        raise ValueError('Nome ou CPF não encontrados.')

    # Data última atualização
    data_lattes = None
    data_atualizacao = dados_gerais.attrib.get('DATA-ATUALIZACAO')
    if data_atualizacao:
        try:
            data_lattes = datetime.strptime(data_atualizacao, '%d%m%Y')
        except ValueError:
            pass

    # Email
    email = None
    endereco = root.find('ENDERECO')
    if endereco is not None:
        prof = endereco.find('ENDERECO-PROFISSIONAL')
        res = endereco.find('ENDERECO-RESIDENCIAL')

        if prof is not None and prof.attrib.get('E-MAIL'):
            email = prof.attrib.get('E-MAIL')
        elif res is not None and res.attrib.get('E-MAIL'):
            email = res.attrib.get('E-MAIL')

    return {
        'nome': nome.upper(),
        'cpf': cpf,
        'email': email,
        'lattes_link': lattes_link,
        'xml_text': xml_text,               # 👈 STRING
        'data_lattes': data_lattes
    }