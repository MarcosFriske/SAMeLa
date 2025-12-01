# -*- coding: utf-8 -*-
"""
Created on Mon Feb 20 18:27:46 2023

@author: Marcos
"""

############### IMPORTS ############### 

import psycopg2
from lxml import etree
import pandas as pd

############### CONFIGS BD ############### 

## Credencias conexão ao banco de dados

host_db = "localhost"
port_db = "5432"
database_name = "valida_lattes"
user_db = "postgres"
password_db = "admin"

############### FUNÇÕES INTERNAS ############### 

# Definição da função para selecionar os criterios de avaliacao do instrumento de avaliacao informado
def __selecionar_criterios_avaliacao(instrumento_avaliacao):
    try:
        connection = psycopg2.connect(user=user_db,
                                      password=password_db,
                                      host=host_db,
                                      port=port_db,
                                      database=database_name)
        cursor = connection.cursor()

        postgres_select_query = """
            SELECT c.id_criterio, c.criterio, c.qtd_maxima_itens, c.pontuacao_item, c.xpath_criterio_lattes, 
                   c.considera_qualis, c.ativo
            FROM criterios c
            JOIN rel_criterios_instrumentos rci ON c.id_criterio = rci.id_criterio
            WHERE rci.id_instrumento_avaliacao = %s AND c.ativo = TRUE AND rci.ativo = TRUE
            ORDER BY c.criterio
        """
        cursor.execute(postgres_select_query, (instrumento_avaliacao,))

        rows = cursor.fetchall()
        if rows:
            df = pd.DataFrame(rows, columns=[desc[0] for desc in cursor.description])
            print(f"{len(df.index)} records selected successfully from Criterios table")
            return df
        else:
            print("No rows found")
            return None

    except (Exception, psycopg2.Error) as error:
        print("Failed to select records from Criterios table", error)
    finally:
        if connection:
            cursor.close()
            connection.close()
            print("PostgreSQL connection is closed")
            
# Definição da função para carregar o conteúdo da coluna lattes_xml da tabela servidores
def __carregar_lattes_xml(id_servidor):
    try:
        connection = psycopg2.connect(user=user_db,
                                      password=password_db,
                                      host=host_db,
                                      port=port_db,
                                      database=database_name)
        cursor = connection.cursor()
        postgres_select_query = """SELECT lattes_xml FROM public.servidores
                                WHERE id_servidor = %s"""
        id_servidor_select = (id_servidor,)
        cursor.execute(postgres_select_query, id_servidor_select)
        rows = cursor.fetchall()
        if rows:
            xml_element = etree.fromstring(rows[0][0])
            print("Record selected successfully from Servidores table")
            return xml_element
        else:
            print("No rows found")
            return None
    except (Exception, psycopg2.Error) as error:
        print("Failed to select records from Servidores table", error)
    finally:
        # closing database connection.
        if connection:
            cursor.close()
            connection.close()
            print("PostgreSQL connection is closed")
            
# Definição da função para carregar os títulos similares da tabela Qualis
def __selecionar_titulos_similares(titulo, min_similaridade):
    try:
        connection = psycopg2.connect(user=user_db,
                                      password=password_db,
                                      host=host_db,
                                      port=port_db,
                                      database=database_name)
        cursor = connection.cursor()
        postgres_select_query = """SELECT titulo FROM public.qualis
                                   WHERE similarity(titulo, %s) > %s"""
        cursor.execute(postgres_select_query, (titulo, min_similaridade))
        rows = cursor.fetchall()
        if rows:
            titulos_qualis = [row[0] for row in rows]
            return titulos_qualis
        else:
            return []
    except (Exception, psycopg2.Error) as error:
        print("Failed to select similar titles from tabela qualis", error)
        return []
    finally:
        # closing database connection.
        if connection:
            cursor.close()
            connection.close()
    
# Definição da função para verificar ISSN iguais da tabela Qualis
def __verificar_issn_no_qualis(issn_formatado):
    try:
        connection = psycopg2.connect(user=user_db,
                                      password=password_db,
                                      host=host_db,
                                      port=port_db,
                                      database=database_name)
        cursor = connection.cursor()
        postgres_select_query = """SELECT titulo FROM public.qualis
                                   WHERE issn_isbn = %s"""
        cursor.execute(postgres_select_query, (issn_formatado,))
        rows = cursor.fetchall()
        if rows:
            return rows[0][0]
        else:
            return None
    except (Exception, psycopg2.Error) as error:
        print("Failed to verify ISSN in qualis table", error)
        return None
    finally:
        # closing database connection.
        if connection:
            cursor.close()
            connection.close()



############### EXECUÇÃO ############### 
def executar_algoritmo(id_servidor, instrumento_avaliacao_id):
    
    #### Iniciação de variáveis
    
    # Configurando o filtro de ano inicial e final para ser utilizado nos XPATHS do BD
    min_ano = 2018
    max_ano = 2022

    # Inicializando o dataframe vazio para receber os dados dos artigos

    df_artigos_xml = pd.DataFrame()
    contagem_artigos_com_qualis = 0
    contagem_artigos_sem_qualis = 0
    
    ############################
    
    # Começar a execução perguntando por um servidor, verificando se o mesmo tem um XML salvo nos seus dados na tabela servidores.
    
    xml = __carregar_lattes_xml(id_servidor)
    
    if xml is None:
        print(f"O servidor com o ID: {id_servidor} não possui nenhum XML de currículo Lattes associado na coluna lattes_xml.")
        return None
    
    # Continuar a execução do programa utilizando o XML retornado
    
    # Execução da função com o ID informado pelo usuário
    df_criterios_avaliacao = __selecionar_criterios_avaliacao(instrumento_avaliacao_id)
    
    # Verificação do dataframe retornado pela função
    if df_criterios_avaliacao is not None:
        print(df_criterios_avaliacao['criterio'])
        
        df_avaliacao = pd.DataFrame(columns=['item', 'criterios', 'pontuacao_por_item', 'pontuacao_maxima', 'quantidade', 'pontuacao_atingida'])
        
        for index, row in df_criterios_avaliacao.iterrows():
            xpath_criterio_lattes = row['xpath_criterio_lattes']
            print(f'XPATH CRITERIO LATTES: {xpath_criterio_lattes}')
            
            if row['considera_qualis'] == False:
                if 'min_ano' in xpath_criterio_lattes and 'max_ano' in xpath_criterio_lattes:
                    xpath = etree.XPath(xpath_criterio_lattes)
                    count = xpath(xml, min_ano=min_ano, max_ano=max_ano)
                    print(xpath)
                    print(count)
                    
                    # obter a próxima linha vazia do dataframe
                    next_row = len(df_avaliacao)
                    # adicionar os valores à próxima linha vazia
                    valor = row['pontuacao_item']*count
                    if valor > row['pontuacao_item']*row['qtd_maxima_itens']:
                        valor = row['pontuacao_item']*row['qtd_maxima_itens']
                    df_avaliacao.loc[next_row] = [index, row['criterio'], row['pontuacao_item'], (row['pontuacao_item']*row['qtd_maxima_itens']), count, valor]
                    
                elif 'min_ano' not in xpath_criterio_lattes and 'max_ano' not in xpath_criterio_lattes:
                    xpath = etree.XPath(xpath_criterio_lattes)
                    count = xpath(xml)
                    print(xpath)
                    print(count)
                    
                    # obter a próxima linha vazia do dataframe
                    next_row = len(df_avaliacao)
                    # adicionar os valores à próxima linha vazia
                    valor = row['pontuacao_item']*count
                    if valor > row['pontuacao_item']*row['qtd_maxima_itens']:
                        valor = row['pontuacao_item']*row['qtd_maxima_itens']
                    df_avaliacao.loc[next_row] = [index, row['criterio'], row['pontuacao_item'], (row['pontuacao_item']*row['qtd_maxima_itens']), count, valor]
                
            elif row['considera_qualis']:
                
                expressao_xpath = xpath_criterio_lattes
                resultados_xpath = xml.xpath(expressao_xpath, min_ano=min_ano, max_ano=max_ano)
                
                if df_artigos_xml.empty:
                    # O dataframe está vazio, faça alguma outra coisa aqui
                    # Extrair os dados de cada resultado XPath e adicionar em uma lista
                    dados = []
                    for resultado in resultados_xpath:
                        dados_artigo = {}
                        dados_basicos_artigo = resultado.find("DADOS-BASICOS-DO-ARTIGO")
                        detalhamento_artigo = resultado.find("DETALHAMENTO-DO-ARTIGO")
                        dados_artigo['natureza'] = dados_basicos_artigo.get('NATUREZA')
                        dados_artigo['titulo'] = dados_basicos_artigo.get('TITULO-DO-ARTIGO')
                        dados_artigo['ano'] = dados_basicos_artigo.get('ANO-DO-ARTIGO')
                        dados_artigo['pais_publicacao'] = dados_basicos_artigo.get('PAIS-DE-PUBLICACAO')
                        dados_artigo['idioma'] = dados_basicos_artigo.get('IDIOMA')
                        dados_artigo['meio_divulgacao'] = dados_basicos_artigo.get('MEIO-DE-DIVULGACAO')
                        dados_artigo['home_page'] = dados_basicos_artigo.get('HOME-PAGE-DO-TRABALHO')
                        dados_artigo['flag_relevancia'] = dados_basicos_artigo.get('FLAG-RELEVANCIA')
                        dados_artigo['doi'] = dados_basicos_artigo.get('DOI')
                        dados_artigo['titulo_ingles'] = dados_basicos_artigo.get('TITULO-DO-ARTIGO-INGLES')
                        dados_artigo['flag_divulgacao_cientifica'] = dados_basicos_artigo.get('FLAG-DIVULGACAO-CIENTIFICA')
                        dados_artigo['titulo_periodico'] = detalhamento_artigo.get('TITULO-DO-PERIODICO-OU-REVISTA')
                        dados_artigo['issn'] = detalhamento_artigo.get('ISSN')
                        dados.append(dados_artigo)
    
                    # Criar um DataFrame do pandas com os dados extraídos
                    df_artigos_xml = pd.DataFrame(dados)
    
                    # Mostrar o DataFrame
                    print(df_artigos_xml)
                    
                    if df_artigos_xml.empty:
                        # Pular para a próxima iteração do loop se o título estiver vazio
                        print('Sem dados de Artigo pulando para próximo critério.')
                        
                        # Preencher o dataframe df_avaliacao com os dados disponíveis referente aos sem Qualis
                        if xpath_criterio_lattes == 'sem_qualis':
                            # obter a próxima linha vazia do dataframe
                            next_row = len(df_avaliacao)
                            
                            contagem_artigos_sem_qualis = 0
                            
                            # adicionar os valores à próxima linha vazia
                            valor = row['pontuacao_item']*contagem_artigos_sem_qualis
                            if valor > row['pontuacao_item']*row['qtd_maxima_itens']:
                                valor = row['pontuacao_item']*row['qtd_maxima_itens']
                            df_avaliacao.loc[next_row] = [index, row['criterio'], row['pontuacao_item'], (row['pontuacao_item']*row['qtd_maxima_itens']), contagem_artigos_sem_qualis, valor]
                        # Preencher o dataframe df_avaliacao com os dados disponíveis referente aos com Qualis
                        else:
                            # obter a próxima linha vazia do dataframe
                            next_row = len(df_avaliacao)
                            
                            contagem_artigos_com_qualis = 0
                            
                            # adicionar os valores à próxima linha vazia
                            valor = row['pontuacao_item']*contagem_artigos_com_qualis
                            if valor > row['pontuacao_item']*row['qtd_maxima_itens']:
                                valor = row['pontuacao_item']*row['qtd_maxima_itens']
                            df_avaliacao.loc[next_row] = [index, row['criterio'], row['pontuacao_item'], (row['pontuacao_item']*row['qtd_maxima_itens']), contagem_artigos_com_qualis, valor] 
                        continue
                    
                    # Criar uma lista vazia para armazenar os resultados da verificação
                    existe_titulo_similar = []
                    
                    # Para cada linha do dataframe 'df_artigos_xml', verificar se o título do periodico está presente na tabela 'qualis'
                    for idx, row_artigo in df_artigos_xml.iterrows():
                        
                        if row_artigo['issn']:
                            # Executar lógica quando o ISSN está preenchido
                            # Adicionar hífen no quinto caractere
                            issn_formatado = "{}-{}".format(row_artigo['issn'][:4], row_artigo['issn'][4:])
                            # Executar lógica quando o ISSN está preenchido
                            print("ISSN preenchido: ", issn_formatado)
                            titulo_da_issn = __verificar_issn_no_qualis(issn_formatado)
                            if titulo_da_issn:
                                existe_titulo_similar.append(True)
                            else:
                                # Executar lógica quando o ISSN não está preenchido
                                print(f"Não achou ISSN no Qualis: {titulo_da_issn}")
                            
                                titulo = row_artigo['titulo_periodico']
                                titulos_qualis = __selecionar_titulos_similares(titulo, 0.7)
                                if titulos_qualis:
                                    existe_titulo_similar.append(True)
                                else:
                                    existe_titulo_similar.append(False)
                        else:
                            # Executar lógica quando o ISSN não está preenchido
                            print(f"ISSN não preenchido no artigo: {df_artigos_xml['titulo']}")
                        
                            titulo = row_artigo['titulo_periodico']
                            titulos_qualis = __selecionar_titulos_similares(titulo, 0.7)
                            if titulos_qualis:
                                existe_titulo_similar.append(True)
                            else:
                                existe_titulo_similar.append(False)
                    
                    # Adicionar a lista de resultados como uma nova coluna no dataframe 'df_artigos_xml'
                    df_artigos_xml['existe_titulo_similar'] = existe_titulo_similar
                    
                    # Contagem de artigos com e sem qualis
                    contagem_artigos_com_qualis = df_artigos_xml['existe_titulo_similar'].value_counts().get(True, 0)
                    contagem_artigos_sem_qualis = df_artigos_xml['existe_titulo_similar'].value_counts().get(False, 0)
                    
                    # Imprimir os resultados
                    print("Quantidade de artigos com similaridade no título em relação à tabela_qualis: ", contagem_artigos_com_qualis)
                    print("Quantidade de artigos sem similaridade no título em relação à tabela_qualis: ", contagem_artigos_sem_qualis)
                    
                    # Preencher o dataframe df_avaliacao com os dados disponíveis referente aos sem Qualis
                    if xpath_criterio_lattes == 'sem_qualis':
                        # obter a próxima linha vazia do dataframe
                        next_row = len(df_avaliacao)
                        # adicionar os valores à próxima linha vazia
                        valor = row['pontuacao_item']*contagem_artigos_sem_qualis
                        if valor > row['pontuacao_item']*row['qtd_maxima_itens']:
                            valor = row['pontuacao_item']*row['qtd_maxima_itens']
                        df_avaliacao.loc[next_row] = [index, row['criterio'], row['pontuacao_item'], (row['pontuacao_item']*row['qtd_maxima_itens']), contagem_artigos_sem_qualis, valor]  
                    # Preencher o dataframe df_avaliacao com os dados disponíveis referente aos com Qualis
                    else:
                        # obter a próxima linha vazia do dataframe
                        next_row = len(df_avaliacao)
                        # adicionar os valores à próxima linha vazia
                        valor = row['pontuacao_item']*contagem_artigos_com_qualis
                        if valor > row['pontuacao_item']*row['qtd_maxima_itens']:
                            valor = row['pontuacao_item']*row['qtd_maxima_itens']
                        df_avaliacao.loc[next_row] = [index, row['criterio'], row['pontuacao_item'], (row['pontuacao_item']*row['qtd_maxima_itens']), contagem_artigos_com_qualis, valor] 
                else:
                    # Preencher o dataframe df_avaliacao com os dados disponíveis referente aos sem Qualis
                    if xpath_criterio_lattes == 'sem_qualis':
                        # obter a próxima linha vazia do dataframe
                        next_row = len(df_avaliacao)
                        # adicionar os valores à próxima linha vazia
                        valor = row['pontuacao_item']*contagem_artigos_sem_qualis
                        if valor > row['pontuacao_item']*row['qtd_maxima_itens']:
                            valor = row['pontuacao_item']*row['qtd_maxima_itens']
                        df_avaliacao.loc[next_row] = [index, row['criterio'], row['pontuacao_item'], (row['pontuacao_item']*row['qtd_maxima_itens']), contagem_artigos_sem_qualis, valor]
                    # Preencher o dataframe df_avaliacao com os dados disponíveis referente aos com Qualis
                    else:
                        # obter a próxima linha vazia do dataframe
                        next_row = len(df_avaliacao)
                        # adicionar os valores à próxima linha vazia
                        valor = row['pontuacao_item']*contagem_artigos_com_qualis
                        if valor > row['pontuacao_item']*row['qtd_maxima_itens']:
                            valor = row['pontuacao_item']*row['qtd_maxima_itens']
                        df_avaliacao.loc[next_row] = [index, row['criterio'], row['pontuacao_item'], (row['pontuacao_item']*row['qtd_maxima_itens']), contagem_artigos_com_qualis, valor] 
                    
        # após preencher o dataframe df_avaliacao
        return df_avaliacao
    
    if df_criterios_avaliacao is None:
        print(f"Não foi possível encontrar o instrumento de avaliação associado ao ID: {instrumento_avaliacao_id} informado.")
        return None