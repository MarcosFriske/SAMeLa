# -*- coding: utf-8 -*-
"""
Created on Mon Feb 20 18:27:46 2023

@author: Marcos
"""

from lxml import etree as ET_lxml
import json

# abre o arquivo
with open(r'E:/BSI19/TCC2/Lattes_criterios.json', encoding='utf-8') as f:
    # carrega o conteúdo do arquivo na variável dados
    dicionario_criterios = json.load(f)

# exibe o conteúdo da variável
print(dicionario_criterios)

with open(r'E:/BSI19/TCC2/ValidaLattes/XML/lattesFrozza.xml') as f:
    root = ET_lxml.parse(f).getroot()

# exibe a tag nome do root
print(root.tag)

# exibe as tag filhas do root
for child in root:
    print(child.tag)

def conta_xml(path, xml):
    print("Xpath sendo analisado: ")
    print(path)
    print("-"*15)
    if (xml.find(path) is not None):
        for i, item in enumerate(xml.find(path)):
            # Objeto bytes
            elemento = item
            
            # Convertendo para string e aplicando o método upper
            elemento_upper = ET_lxml.tostring(elemento).decode('utf-8').upper()
            
            # print(elemento.tag)
            
            if elemento is not None:
                # faça algo com o elemento encontrado
                print("{}: {}".format(i, ET_lxml.tostring(elemento)))
                # conta o número de elementos filhos de 'elemento'
                if ("PALAVRAS-CHAVE" in elemento.tag):
                    print('a tag é palavras_chave')
                    return 1
                elif ("PALAVRAS-CHAVE" in elemento_upper):
                    print('achou PALAVRAS-CHAVE')
                    ocorrencias = elemento.findall('.//PALAVRAS-CHAVE')
                    # Conta a quantidade de ocorrências encontradas
                    quantidade = len(ocorrencias)
                    return quantidade
                elif ("EDITOR" in elemento_upper or
                      "EDITORAÇÃO" in elemento_upper or
                      "EDITORACAO" in elemento_upper):
                    print("achou EDITOR")
                    num_filhos = len(elemento.findall('.//SERVICO-TECNICO-ESPECIALIZADO[contains(lower-case(@SERVICO-REALIZADO, "editor")) or contains(lower-case(@SERVICO-REALIZADO, "editoração")) or contains(lower-case(@SERVICO-REALIZADO, "editoracao"))]'))
                    return num_filhos
                else:
                    print("Não encontrou nenhum elemento para esse critério.")
                    num_filhos = 0
                    return num_filhos
    else:
        # lide com a ausência do elemento
        print("Não há XPATH definido para esse critério.")
        num_filhos = 0
        return num_filhos

def calcula_valor(criterio, conta_elementos):
    if conta_elementos > criterio.qtd_maxima_itens:
        return criterio.pontuacao_item
    else:
        return (criterio.pontuacao_item / criterio.qtd_maxima_itens) * conta_elementos

def valida_cv_lattes(dicionario_criterios, cv_lattes):
    avaliacao_cv_lattes = 0
    for key in dicionario_criterios:
        print(8*"-" + f" {key}: ".upper() + 8*"-" + " \n")
        for sub_key, value in dicionario_criterios[key].items():
            print(8*"*" + f" {sub_key}: ".upper() + 8*"*" + " \n")
            for sub_sub_key, value in dicionario_criterios[key][sub_key].items():
                # print(f"{sub_sub_key}: {value} \n")
                print(8*"×" + f" {sub_sub_key}: ".upper() + 8*"×" + " \n")
                print("Critério a ser analisado: ")
                print(dicionario_criterios[key][sub_key][sub_sub_key].get('criterio'))
                print("-"*15)
                conta_elementos = conta_xml(dicionario_criterios[key][sub_key][sub_sub_key].get('path'), cv_lattes)
                print("Quantidade elementos: ")
                print(conta_elementos)
                print("-"*15)
        # avaliacao_cv_lattes += calcula_valor(criterio, conta_elementos)
    return avaliacao_cv_lattes


nota_lattes = valida_cv_lattes(dicionario_criterios, root)
