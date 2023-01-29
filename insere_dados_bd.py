# -*- coding: utf-8 -*-
"""
Created on Sat Jan 28 20:37:43 2023

@author: Marcos
"""

import psycopg2
import bcrypt
from lxml import etree as ET_lxml

## Credencias conexão ao banco de dados

host_db = "localhost"
port_db = "5432"
database_name = "valida_lattes"
user_db = "postgres"
password_db = "admin"

## Configurações do XML
xml_filename = "lattesFrozza.xml"
xml_file = ET_lxml.parse(xml_filename).getroot()
xml_string = ET_lxml.tostring(xml_file, encoding='utf-8').decode()

## Funções de inserção de dados nas tabelas

def inserir_dados_servidores(tipo_servidor, matricula, senha, nome, lattes_link, lattes_XML, e_mail):
    try:
        connection = psycopg2.connect(user = user_db,
                                      password = password_db,
                                      host = host_db,
                                      port = port_db,
                                      database = database_name)
        cursor = connection.cursor()
        postgres_insert_query = """INSERT INTO SERVIDORES (tipo_servidor, matricula, senha, nome, lattes_link, lattes_XML, e_mail)
        VALUES (%s, %s, %s, %s, %s, %s, %s)"""
        record_to_insert = (tipo_servidor, matricula, senha, nome, lattes_link, lattes_XML, e_mail)
        cursor.execute(postgres_insert_query, record_to_insert)
        connection.commit()
        count = cursor.rowcount
        print(count, "Record inserted successfully into SERVIDORES table")
    except (Exception, psycopg2.Error) as error:
        print("Failed to insert record into SERVIDORES table", error)
        connection.rollback()
    finally:
        # closing database connection.
        if (connection):
            cursor.close()
            connection.close()
            print("PostgreSQL connection is closed")
            
def inserir_dados_instrumentos_avaliacao(nome, descricao, data_criacao, ativo):
    try:
        connection = psycopg2.connect(user = user_db,
                                      password = password_db,
                                      host = host_db,
                                      port = port_db,
                                      database = database_name)
        cursor = connection.cursor()
        postgres_insert_query = """INSERT INTO INSTRUMENTOS_AVALIACAO (nome, descricao, data_criacao, ativo) 
        VALUES (%s, %s, %s, %s)"""
        record_to_insert = (nome, descricao, data_criacao, ativo,)
        cursor.execute(postgres_insert_query, record_to_insert)
        connection.commit()
        count = cursor.rowcount
        print(count, "Record inserted successfully into INSTRUMENTOS_AVALIACAO table")
    except (Exception, psycopg2.Error) as error:
        print("Failed to insert record into INSTRUMENTOS_AVALIACAO table", error)
        connection.rollback()
    finally:
        # closing database connection.
        if (connection):
            cursor.close()
            connection.close()
            print("PostgreSQL connection is closed")

def inserir_evento(identificacao, tipo_evento, data_inicio, data_fim, localizacao, descricao, fk_id_instrumento_avaliacao):
    try:
        connection = psycopg2.connect(user = user_db,
                                      password = password_db,
                                      host = host_db,
                                      port = port_db,
                                      database = database_name)

        cursor = connection.cursor()

        postgres_insert_query = """INSERT INTO eventos (identificacao, tipo_evento, data_inicio, data_fim, localizacao, descricao, fk_id_instrumento_avaliacao) 
        VALUES (%s,%s,%s,%s,%s,%s,%s)"""
        record_to_insert = (identificacao, tipo_evento, data_inicio, data_fim, localizacao, descricao, fk_id_instrumento_avaliacao)
        cursor.execute(postgres_insert_query, record_to_insert)
        connection.commit()
        count = cursor.rowcount
        print (count, "Record inserted successfully into EVENTOS table")

    except (Exception, psycopg2.Error) as error :
        print("Failed to insert record into EVENTOS table", error)
        connection.rollback()
    finally:
        #closing database connection.
        if(connection):
            cursor.close()
            connection.close()
            print("PostgreSQL connection is closed")
            
def inserir_dados_avaliacao(organizacao, pontuacao, fk_id_servidor, fk_id_evento):
    try:
        connection = psycopg2.connect(user = user_db,
                                      password = password_db,
                                      host = host_db,
                                      port = port_db,
                                      database = database_name)
        cursor = connection.cursor()
        postgres_insert_query = """INSERT INTO SERVIDORES (organizacao, pontuacao, fk_id_servidor, fk_id_evento)
        VALUES (%s, %s, %s, %s)"""
        record_to_insert = (organizacao, pontuacao, fk_id_servidor, fk_id_evento)
        cursor.execute(postgres_insert_query, record_to_insert)
        connection.commit()
        count = cursor.rowcount
        print(count, "Record inserted successfully into AVALIACAO table")
    except (Exception, psycopg2.Error) as error:
        print("Failed to insert record into AVALIACAO table", error)
        connection.rollback()
    finally:
        # closing database connection.
        if (connection):
            cursor.close()
            connection.close()
            print("PostgreSQL connection is closed")
            
def inserir_dados_criterios(qtd_maxima_itens, pontuacao_item, criterio, xpath_criterio_lattes, considera_qualis, fk_id_instrumento_avaliacao):
    try:
        connection = psycopg2.connect(user = user_db,
                                      password = password_db,
                                      host = host_db,
                                      port = port_db,
                                      database = database_name)
        cursor = connection.cursor()
        postgres_insert_query = """INSERT INTO criterios (qtd_maxima_itens, pontuacao_item, criterio, xpath_criterio_lattes, considera_qualis, fk_id_instrumento_avaliacao)
        VALUES (%s, %s, %s, %s, %s, %s)"""
        record_to_insert = (qtd_maxima_itens, pontuacao_item, criterio, xpath_criterio_lattes, considera_qualis, fk_id_instrumento_avaliacao)
        cursor.execute(postgres_insert_query, record_to_insert)
        connection.commit()
        count = cursor.rowcount
        print(count, "Record inserted successfully into CRITERIOS table")
    except (Exception, psycopg2.Error) as error:
        print("Failed to insert record into CRITERIOS table", error)
        connection.rollback()
    finally:
        # closing database connection.
        if (connection):
            cursor.close()
            connection.close()
            print("PostgreSQL connection is closed")
            
def inserir_dados_qualis(extrato_capes, sigla, area_de_avaliacao, titulo, url, localidade, issn_isbn, ano_avaliacao, tipo_qualis):
    try:
        connection = psycopg2.connect(user = user_db,
                                      password = password_db,
                                      host = host_db,
                                      port = port_db,
                                      database = database_name)
        cursor = connection.cursor()
        postgres_insert_query = """INSERT INTO qualis (extrato_capes, sigla, area_de_avaliacao, titulo, url, localidade, issn_isbn, ano_avaliacao, tipo_qualis)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"""
        record_to_insert = (extrato_capes, sigla, area_de_avaliacao, titulo, url, localidade, issn_isbn, ano_avaliacao, tipo_qualis)
        cursor.execute(postgres_insert_query, record_to_insert)
        connection.commit()
        count = cursor.rowcount
        print(count, "Record inserted successfully into QUALIS table")
    except (Exception, psycopg2.Error) as error:
        print("Failed to insert record into QUALIS table", error)
        connection.rollback()
    finally:
        # closing database connection.
        if (connection):
            cursor.close()
            connection.close()
            print("PostgreSQL connection is closed")
            
def menu():
    opcao = 0
    running = True
    while running:
        print("1 - Inserir dados na tabela Servidores")
        print("2 - Inserir dados na tabela Instrumentos Avaliacao")
        print("3 - Inserir dados na tabela Eventos")
        print("4 - Inserir dados na tabela Criterios")
        print("5 - Inserir dados na tabela Avaliacao")
        print("6 - Inserir dados na tabela Qualis")
        print("7 - Encerrar programa")
        opcao = int(input("Selecione uma opção: "))
        if opcao == "1":
            opcao = 0
            running2 = True
            while running2:
                print("1 - Administrador")
                print("2 - Docente")
                print("3 - Desenvolvedor")
                opcao = int(input("Selecione o tipo de servidor: "))
                if opcao == "1":
                    tipo_servidor = 'Administrador'
                    running2 = False
                elif opcao == "2":
                    tipo_servidor = 'Docente'
                    running2 = False
                elif opcao == "3":
                    tipo_servidor = 'Desenvolvedor'
                    running2 = False
                else:
                    print("Opção inválida.")
            matricula = input("Informe a matricula do servidor: ")
            senha = input("Informe a senha do servidor: ")
            senha = b'{senha}'
            senha_hash = bcrypt.hashpw(senha, bcrypt.gensalt())
            nome = input("Informe o nome do servidor: ")
            nome = nome.upper()
            lattes_link = input("Informe o link do lattes: ")
            lattes_XML = xml_string
            e_mail = input("Informe o e-mail do servidor: ")
            inserir_dados_servidores(tipo_servidor, matricula, senha_hash, nome, lattes_link, lattes_XML, e_mail)
        elif opcao == "2":
            nome = input("Informe o nome do instrumento de avaliacao: ")
            descricao = input("Informe a descricao do instrumento de avaliacao: ")
            data_criacao = input("Informe a data de criacao do instrumento de avaliacao (dd/mm/aaaa): ")
            ativo = True
            inserir_dados_instrumentos_avaliacao(nome, descricao, data_criacao, ativo)
        elif opcao == "3":
            inserir_evento(identificacao, tipo_evento, data_inicio, data_fim, localizacao, descricao, fk_id_instrumento_avaliacao)
        elif opcao == "4":
            inserir_dados_criterios(qtd_maxima_itens, pontuacao_item, criterio, xpath_criterio_lattes, considera_qualis, fk_id_instrumento_avaliacao)
        elif opcao == "5":
            inserir_dados_avaliacao(organizacao, pontuacao, fk_id_servidor, fk_id_evento)
        elif opcao == "6":
            inserir_dados_qualis(extrato_capes, sigla, area_de_avaliacao, titulo, url, localidade, issn_isbn, ano_avaliacao, tipo_qualis)
        elif opcao == "7":
            pass
        else:
            print("Opção inválida.")

try:
    # código que pode causar exceção
    menu()

except Exception as e:
    print("Erro genérico: ", e)