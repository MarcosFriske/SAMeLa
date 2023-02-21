# -*- coding: utf-8 -*-
"""
Created on Mon Feb 20 17:32:14 2023

@author: Marcos
"""

import requests
from bs4 import BeautifulSoup

# Define a URL do Lattes iD a ser baixado
lattes_id_url = "http://lattes.cnpq.br/2867543412620882"

# Faz o request para a página do Lattes iD
response = requests.get(lattes_id_url)

# Parseia o HTML da página usando o BeautifulSoup
soup = BeautifulSoup(response.text, "html.parser")

# Encontra a URL para o XML do currículo Lattes
xml_url = soup.find("a", href=True, text="XML").get("href")

# Faz o download do arquivo XML
xml_response = requests.get(xml_url)

# Escreve o conteúdo do XML em um arquivo local
with open("meu_curriculo_lattes.xml", "wb") as xml_file:
    xml_file.write(xml_response.content)
