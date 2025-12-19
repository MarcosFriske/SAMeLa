# -*- coding: utf-8 -*-
"""
Created on Fri Dec 19 09:19:26 2025

@author: Marcos
"""

import xml.etree.ElementTree as ET

def extrair_dados_lattes(xml_path: str) -> dict:
    tree = ET.parse(xml_path)
    root = tree.getroot()

    # --------------------------------
    # ID LATTES (OBRIGATÓRIO)
    # --------------------------------
    numero_lattes = root.attrib.get('NUMERO-IDENTIFICADOR')
    if not numero_lattes:
        raise ValueError('Número identificador do Lattes não encontrado.')

    lattes_link = f'http://lattes.cnpq.br/{numero_lattes}'

    # --------------------------------
    # DADOS GERAIS
    # --------------------------------
    dados_gerais = root.find('DADOS-GERAIS')
    if dados_gerais is None:
        raise ValueError('DADOS-GERAIS não encontrados no XML.')

    nome = dados_gerais.attrib.get('NOME-COMPLETO')
    cpf = dados_gerais.attrib.get('CPF')

    if not nome or not cpf:
        raise ValueError('Nome ou CPF não encontrados no XML.')

    # --------------------------------
    # E-MAIL
    # Prioridade:
    # 1) Profissional
    # 2) Residencial
    # --------------------------------
    email = None

    endereco = dados_gerais.find('ENDERECO')
    if endereco is not None:
        endereco_prof = endereco.find('ENDERECO-PROFISSIONAL')
        endereco_res = endereco.find('ENDERECO-RESIDENCIAL')

        if endereco_prof is not None:
            email = endereco_prof.attrib.get('E-MAIL')

        if not email and endereco_res is not None:
            email = endereco_res.attrib.get('E-MAIL')

    return {
        'nome': nome.upper(),
        'cpf': cpf,
        'email': email.strip().lower() if email else None,
        'lattes_link': lattes_link
    }