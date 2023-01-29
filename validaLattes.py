# -*- coding: utf-8 -*-
"""
Created on Sat Dec 17 17:06:02 2022

@author: Marcos
"""

from lxml import etree as ET_lxml

xml_filename = "lattesFrozza.xml"

root = ET_lxml.parse(xml_filename).getroot()

for child in root:
    print(child.tag)

print(root.tag)
print(len(root))

dados_gerais = root[0]
print(dados_gerais.tag)

producao_bibliografica = root[1]
print(producao_bibliografica.tag)

producao_tecnica = root[2]
print(producao_tecnica.tag)

outra_producao = root[3]
print(outra_producao.tag)

dados_complementares = root[4]
print(dados_complementares.tag)

# Ver todas as tags das childrens do root
children = list(root)
for child in root:
    print(child.tag)
    
# Ver todas as tags das childrens do dados_gerais
children = list(dados_gerais)
for child in dados_gerais:
    print(child.tag)

# Texto de resumo do Curriculo Lattes
for i, item in enumerate(root.findall("DADOS-GERAIS/RESUMO-CV")):
    print("{}: {}".format(i, item.attrib["TEXTO-RESUMO-CV-RH"]))
    
# Texto de resumo do Curriculo Lattes em ingles
for i, item in enumerate(root.findall("DADOS-GERAIS/RESUMO-CV")):
    print("{}: {}".format(i, item.attrib["TEXTO-RESUMO-CV-RH-EN"]))

# Ver os atributos da tag root
sorted(root.keys())

# Ver os atributos da tag dados_gerais
sorted(dados_gerais.keys()) 

# Criar dicionário com atributos do root
attributes = root.attrib
print(attributes)

# Faz print de todo o conteúdo do root como string
ET_lxml.tostring(root)

# Faz print de todo o conteúdo do dados_gerais como string
ET_lxml.tostring(dados_gerais)

# Print via xpath partindo do root das disciplinas
print(root.xpath("DADOS-GERAIS//ATUACOES-PROFISSIONAIS//ATUACAO-PROFISSIONAL//ATIVIDADES-DE-ENSINO//ENSINO//DISCIPLINA//text()"))

# Pretty print root content
print(ET_lxml.tostring(root, pretty_print=True))

# Texto das disciplinas ministradas enumeradas
for i, item in enumerate(root.findall("DADOS-GERAIS//ATUACOES-PROFISSIONAIS//ATUACAO-PROFISSIONAL//ATIVIDADES-DE-ENSINO//ENSINO//DISCIPLINA")):
    print("{}: {}".format(i, item.text))

### Com beautiful soup

# from bs4 import BeautifulSoup

# arquivoLattes = 'lattesFrozza.xml'

# # Reading the data inside the xml
# # file to a variable under the name
# # data
# with open(arquivoLattes, 'r') as f:
# 	data = f.read()

# # Passing the stored data inside
# # the beautifulsoup parser, storing
# # the returned object
# Bs_data = BeautifulSoup(data, "xml")

# # Finding all instances of tag
# # `FORMACAO-ACADEMICA-TITULACAO`
# b_formacao_academica = Bs_data.find_all('FORMACAO-ACADEMICA-TITULACAO')

# print(b_formacao_academica)

# b_doutorado = Bs_data.find_all('DOUTORADO')

# print(b_doutorado)


