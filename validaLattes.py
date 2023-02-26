# -*- coding: utf-8 -*-
"""
Created on Sat Dec 17 17:06:02 2022

@author: Marcos
"""

from lxml import etree as ET_lxml

xml_filename = r"XML/lattesFrozza.xml"

xml = ET_lxml.parse(xml_filename)

root = ET_lxml.parse(xml_filename).getroot()

for child in root:
    print(child.tag)

print(root.tag)
print(len(root))

# Imprimir o conteúdo em string do item da tag XML
for i, item in enumerate(xml.findall("//DADOS-GERAIS/FORMACAO-ACADEMICA-TITULACAO/DOUTORADO")):
    print("{}: {}".format(i, ET_lxml.tostring(item)))

# contar as ocorrências de DOUTORADO
count = root.xpath('count(//DADOS-GERAIS/FORMACAO-ACADEMICA-TITULACAO/DOUTORADO)')
# imprimir o resultado
print(count)

# contar as ocorrências de MESTRADO
count = root.xpath('count(//DADOS-GERAIS/FORMACAO-ACADEMICA-TITULACAO/MESTRADO)')
# imprimir o resultado
print(count)

# contar as ocorrências de ESPECIALIZACAO
count = root.xpath('count(//DADOS-GERAIS/FORMACAO-ACADEMICA-TITULACAO/ESPECIALIZACAO)')
# imprimir o resultado
print(count)

###################

# Contar as ocorrencias de artigos

# 'ANO-DO-ARTIGO': '2000'

# Ainda precisa ver uma forma de checar se o título está na qualis
# 'TITULO-DO-ARTIGO': 'A Internet como ferramenta de ensino: um estudo sobre seus recursos e como aplicá-los no Ensino a Distância'

artigos_publicados = root.xpath('//PRODUCAO-BIBLIOGRAFICA/ARTIGOS-PUBLICADOS/ARTIGO-PUBLICADO')[0]

for sub_elemento in artigos_publicados.getchildren():
    print(sub_elemento.tag)
    
# encontra todos os elementos ARTIGO-PUBLICADO
artigos = root.findall('.//ARTIGO-PUBLICADO')

# itera sobre cada elemento ARTIGO-PUBLICADO e imprime o conteúdo de DADOS-BASICOS-DO-ARTIGO
for artigo in artigos:
    dados_basicos = artigo.find('DADOS-BASICOS-DO-ARTIGO')
    print(dados_basicos.attrib)
    
min_ano = 1900
max_ano = 2023

xpath = ET_lxml.XPath(
    'count(//PRODUCAO-BIBLIOGRAFICA/ARTIGOS-PUBLICADOS/ARTIGO-PUBLICADO/DADOS-BASICOS-DO-ARTIGO[@ANO-DO-ARTIGO >= $min_ano and @ANO-DO-ARTIGO <= $max_ano])'
)

count = xpath(root, min_ano=min_ano, max_ano=max_ano)

print(count)


##################

# executa o xpath e retorna a contagem de elementos
count = root.xpath('count(//PRODUCAO-BIBLIOGRAFICA/TRABALHOS-EM-EVENTOS/TRABALHO-EM-EVENTOS/DADOS-BASICOS-DO-TRABALHO[@NATUREZA="COMPLETO"])')
# exibe a contagem
print(count)

# Conta o número de ocorrências de trabalhos em eventos com natureza "RESUMO_EXPANDIDO"
count = root.xpath('count(//PRODUCAO-BIBLIOGRAFICA/TRABALHOS-EM-EVENTOS/TRABALHO-EM-EVENTOS/DADOS-BASICOS-DO-TRABALHO[@NATUREZA="RESUMO_EXPANDIDO"])')
print(count)

# XPATH com filtro de ano
# count(//PRODUCAO-BIBLIOGRAFICA/TRABALHOS-EM-EVENTOS[DADOS-BASICOS-DO-TRABALHO[@NATUREZA="COMPLETO" and @ANO-DO-TRABALHO >= $min_ano and @ANO-DO-TRABALHO <= $max_ano]])

min_ano = 1900
max_ano = 2023

xpath = ET_lxml.XPath(
    'count(//PRODUCAO-BIBLIOGRAFICA/TRABALHOS-EM-EVENTOS/TRABALHO-EM-EVENTOS/DADOS-BASICOS-DO-TRABALHO[@NATUREZA="COMPLETO" and @ANO-DO-TRABALHO >= $min_ano and @ANO-DO-TRABALHO <= $max_ano])'
)

count = xpath(root, min_ano=min_ano, max_ano=max_ano)

print(count)


# XPATH com filtro de ano RESUMO_EXPANDIDO

min_ano = 1900
max_ano = 2023

xpath = ET_lxml.XPath(
    'count(//PRODUCAO-BIBLIOGRAFICA/TRABALHOS-EM-EVENTOS/TRABALHO-EM-EVENTOS/DADOS-BASICOS-DO-TRABALHO[@NATUREZA="RESUMO_EXPANDIDO" and @ANO-DO-TRABALHO >= $min_ano and @ANO-DO-TRABALHO <= $max_ano])'
)

count = xpath(root, min_ano=min_ano, max_ano=max_ano)

print(count)

# XPATH com filtro de ano RESUMO

min_ano = 1900
max_ano = 2023

xpath = ET_lxml.XPath(
    'count(//PRODUCAO-BIBLIOGRAFICA/TRABALHOS-EM-EVENTOS/TRABALHO-EM-EVENTOS/DADOS-BASICOS-DO-TRABALHO[@NATUREZA="RESUMO" and @ANO-DO-TRABALHO >= $min_ano and @ANO-DO-TRABALHO <= $max_ano])'
)

count = xpath(root, min_ano=min_ano, max_ano=max_ano)

print(count)

# XPATH com filtro de ano ORIENTACOES INICIACAO_CIENTIFICA

min_ano = 1900
max_ano = 2023

xpath = ET_lxml.XPath(
    'count(//OUTRA-PRODUCAO/ORIENTACOES-CONCLUIDAS/OUTRAS-ORIENTACOES-CONCLUIDAS/DADOS-BASICOS-DE-OUTRAS-ORIENTACOES-CONCLUIDAS[@NATUREZA="INICIACAO_CIENTIFICA" and @ANO >= $min_ano and @ANO <= $max_ano])'
)

count = xpath(root, min_ano=min_ano, max_ano=max_ano)

print(count)

# XPATH com filtro de ano ORIENTACOES INICIACAO_CIENTIFICA

min_ano = 1900
max_ano = 2023

xpath = ET_lxml.XPath(
    'count(//OUTRA-PRODUCAO/ORIENTACOES-CONCLUIDAS/OUTRAS-ORIENTACOES-CONCLUIDAS/DADOS-BASICOS-DE-OUTRAS-ORIENTACOES-CONCLUIDAS[@NATUREZA="INICIACAO_CIENTIFICA" and @ANO >= $min_ano and @ANO <= $max_ano])'
)

count = xpath(root, min_ano=min_ano, max_ano=max_ano)

print(count)

#####################################################

# //PRODUCAO-BIBLIOGRAFICA/TRABALHOS-EM-EVENTOS/count(TRABALHO-EM-EVENTOS/DADOS-BASICOS-DO-TRABALHO[@NATUREZA="RESUMO_EXPANDIDO"])

trabalhos_eventos = root.xpath('//PRODUCAO-BIBLIOGRAFICA/TRABALHOS-EM-EVENTOS/TRABALHO-EM-EVENTOS')[0]

for sub_elemento in trabalhos_eventos.getchildren():
    print(sub_elemento.tag)
    
# encontra todos os elementos ARTIGO-PUBLICADO
trabalhos_eventos = root.findall('.//TRABALHO-EM-EVENTOS')

# itera sobre cada elemento ARTIGO-PUBLICADO e imprime o conteúdo de DADOS-BASICOS-DO-ARTIGO
for artigo in trabalhos_eventos:
    dados_basicos = artigo.find('DADOS-BASICOS-DO-TRABALHO')
    print(dados_basicos.attrib)
    
    
# //OUTRA-PRODUCAO/ORIENTACOES-CONCLUIDAS/count(OUTRAS-ORIENTACOES-CONCLUIDAS/DADOS-BASICOS-DE-OUTRAS-ORIENTACOES-CONCLUIDAS[@NATUREZA="INICIACAO_CIENTIFICA"])

orientacoes = root.xpath('//OUTRA-PRODUCAO/ORIENTACOES-CONCLUIDAS/OUTRAS-ORIENTACOES-CONCLUIDAS')[0]

for sub_elemento in orientacoes.getchildren():
    print(sub_elemento.tag)
    
# encontra todos os elementos ARTIGO-PUBLICADO
orientacoes = root.findall('.//OUTRAS-ORIENTACOES-CONCLUIDAS')

# itera sobre cada elemento ARTIGO-PUBLICADO e imprime o conteúdo de DADOS-BASICOS-DO-ARTIGO
for artigo in orientacoes:
    dados_basicos = artigo.find('DADOS-BASICOS-DE-OUTRAS-ORIENTACOES-CONCLUIDAS')
    print(dados_basicos.attrib)

#####################################################

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


