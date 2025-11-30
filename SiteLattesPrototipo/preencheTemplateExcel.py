import openpyxl
from openpyxl.styles import Alignment, Font, Border, Side, PatternFill
from copy import copy

print("\U0001F680 Iniciando processamento...")

# Abrir a planilha
wb = openpyxl.load_workbook(r"E:\BSI19\TCC2\master_file.xlsx")
ws = wb.active

# Substituição de placeholders no cabeçalho
dados = {
    "{{NOME_EDITAL}}": "Edital 2025",
    "{{COORDENADOR_PROJETO}}": "Dr. João Silva",
    "{{LINK_CURRICULO_LATTES}}": "http://lattes.cnpq.br/123456789",
    "{{DATA_INICIO_EVENTO}}": "30/11/2025",
    "{{DATA_FIM_EVENTO}}": "30/12/2025",
}

print("✍️ Substituindo placeholders no cabeçalho...")
for row in ws.iter_rows(min_row=3, max_row=7, min_col=1, max_col=6):
    for cell in row:
        if isinstance(cell.value, str):
            for placeholder, novo_valor in dados.items():
                if placeholder in cell.value:
                    cell.value = cell.value.replace(placeholder, novo_valor)

print("✅ Placeholders substituídos!")

# Encontrar a linha inicial dos critérios
print("🔍 Procurando linha inicial dos critérios...")
linha_inicial = None
for row in ws.iter_rows(min_row=9, max_row=ws.max_row):
    if isinstance(row[0].value, str) and "{{LINHA_INICIAL_CRITERIOS_ITEM}}" in row[0].value:
        linha_inicial = row[0].row
        break

if not linha_inicial:
    print("❌ Linha inicial não encontrada!")
    wb.close()
    exit()

print(f"✅ Linha inicial encontrada na linha {linha_inicial}.")

# Lista de critérios
criterios = [
    {"NUMERO": 1, "CRITERIO": "Titulação - Doutorado", "PONTOS": 25, "MAX_ITENS": 2, "TOTAL_MAX": 1},
    {"NUMERO": 2, "CRITERIO": "Livro com ISBN", "PONTOS": 8, "MAX_ITENS": 40, "TOTAL_MAX": 40},
    {"NUMERO": 3, "CRITERIO": "Capítulo de livro", "PONTOS": 4, "MAX_ITENS": 24, "TOTAL_MAX": 24},
    {"NUMERO": 4, "CRITERIO": "Capítulo de livro2", "PONTOS": 4, "MAX_ITENS": 24, "TOTAL_MAX": 24},
    {"NUMERO": 5, "CRITERIO": "Capítulo de livro3", "PONTOS": 4, "MAX_ITENS": 24, "TOTAL_MAX": 24},
    {"NUMERO": 6, "CRITERIO": "Capítulo de livro4", "PONTOS": 4, "MAX_ITENS": 24, "TOTAL_MAX": 24},
    {"NUMERO": 7, "CRITERIO": "Capítulo de livro5", "PONTOS": 4, "MAX_ITENS": 24, "TOTAL_MAX": 24},
    {"NUMERO": 8, "CRITERIO": "Capítulo de livro6", "PONTOS": 4, "MAX_ITENS": 24, "TOTAL_MAX": 24},
]

qtd_novas_linhas = len(criterios)

# Função para copiar formatação
def copiar_formatacao(origem, destino):
    for col in range(1, ws.max_column + 1):
        celula_origem = ws.cell(row=origem, column=col)
        celula_destino = ws.cell(row=destino, column=col)

        if not celula_origem.coordinate in ws.merged_cells:
            celula_destino.value = celula_origem.value

        celula_destino.font = copy(celula_origem.font)
        celula_destino.fill = copy(celula_origem.fill)
        celula_destino.border = copy(celula_origem.border)
        celula_destino.alignment = copy(celula_origem.alignment)
        celula_destino.number_format = celula_origem.number_format

# Determinar as linhas que serão movidas
linha_primeira_movida = linha_inicial + 1  
linha_ultima_movida = linha_inicial + 2

# Remover mesclagens abaixo do somatório
print("📌 Desmesclando células abaixo do somatório...")
for merged_range in list(ws.merged_cells.ranges):
    if merged_range.min_row >= linha_primeira_movida:
        ws.unmerge_cells(str(merged_range))

# Inserir linhas novas
ws.insert_rows(idx=linha_inicial+1, amount=qtd_novas_linhas-2)

# Inserir os critérios
print("✍️ Inserindo critérios com formatação...")
for i, criterio in enumerate(criterios):
    linha_atual = linha_inicial + i
    copiar_formatacao(linha_inicial, linha_atual)

    ws.cell(row=linha_atual, column=1, value=criterio["NUMERO"])
    ws.cell(row=linha_atual, column=2, value=criterio["CRITERIO"])
    ws.cell(row=linha_atual, column=3, value=criterio["PONTOS"])
    ws.cell(row=linha_atual, column=4, value=criterio["MAX_ITENS"])
    ws.cell(row=linha_atual, column=5, value=criterio["TOTAL_MAX"])

    formula = (
        f"=IF((E{linha_atual}*C{linha_atual})>D{linha_atual},"
        f"D{linha_atual},"
        f"(E{linha_atual}*C{linha_atual}))"
    )
    
    print(f'Formula sendo preenchida: {formula}')
    
    ws.cell(row=linha_atual, column=6).value = formula
    
print("✅ Critérios adicionados com sucesso!")

# Pegar nova linha do somatorio
linha_somatorio = linha_inicial + qtd_novas_linhas
linha_declaracao = linha_somatorio + 1



# Restaurar mesclagem e formatação do somatório
ws.merge_cells(start_row=linha_somatorio, start_column=1, end_row=linha_somatorio, end_column=5)
celula_somatorio = ws.cell(row=linha_somatorio, column=1)
celula_somatorio.value = "Somatório dos pontos"
celula_somatorio.alignment = Alignment(horizontal="center", vertical="center")
print(f'Formula somatorio preenchida: "=SUM(F{linha_inicial}:F{linha_somatorio-1})"')
ws.cell(row=linha_somatorio, column=6, value=f"=SUM(F{linha_inicial}:F{linha_somatorio-1})")

# Restaurar mesclagem da declaração
ws.merge_cells(start_row=linha_declaracao, start_column=1, end_row=linha_declaracao, end_column=6)
celula_declaracao = ws.cell(row=linha_declaracao, column=1)
celula_declaracao.alignment = Alignment(horizontal="center", vertical="center")


# Salvar e fechar
output_path = r"E:\BSI19\TCC2\output.xlsx"
wb.save(output_path)
print(f"🎉 Processamento concluído! Arquivo salvo em: {output_path}")
