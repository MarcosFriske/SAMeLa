import openpyxl
from openpyxl.styles import PatternFill, Font, Border, Alignment

print("\U0001F680 Iniciando processamento...")

# Abrir a planilha
print("\U0001F4C2 Abrindo planilha...")
wb = openpyxl.load_workbook(r"E:\BSI19\TCC2\master_file.xlsx")
ws = wb.active

# Dicionário com os valores para preencher no cabeçalho (linhas 4-8)
dados = {
    "{{NOME_EDITAL}}": "Edital 2025",
    "{{TITULO_PROJETO}}": "Pesquisa em IA",
    "{{COORDENADOR_PROJETO}}": "Dr. João Silva",
    "{{LINK_CURRICULO_LATTES}}": "http://lattes.cnpq.br/123456789",
    "{{SOLICITACAO_BOLSA_MEDIO}}": "X",
    "{{SOLICITACAO_BOLSA_GRADUACAO}}": "",
}

print("✍️ Substituindo placeholders no cabeçalho (linhas 4-8)...")
for row in ws.iter_rows(min_row=4, max_row=8, min_col=1, max_col=26):
    for cell in row:
        if isinstance(cell.value, str):
            for placeholder, novo_valor in dados.items():
                if placeholder in cell.value:
                    cell.value = cell.value.replace(placeholder, novo_valor)

print("✅ Placeholders no cabeçalho substituídos com sucesso!")

# Encontrar a linha inicial dos critérios (linha 13)
print("🔍 Procurando linha inicial dos critérios...")
linha_inicial = None
for row in ws.iter_rows(min_row=1, max_row=ws.max_row):
    valor_celula = row[0].value
    if isinstance(valor_celula, str) and "{{LINHA_INICIAL_CRITERIOS_ITEM}}" in valor_celula:
        linha_inicial = row[0].row
        break

if not linha_inicial:
    print("❌ Linha inicial dos critérios não encontrada!")
    wb.close()
    exit()

print(f"✅ Linha inicial dos critérios encontrada na linha {linha_inicial}.")

# Lista de critérios
criterios = [
    {"NUMERO": 3, "CRITERIO": "Titulação - Doutorado", "PONTOS": 25, "MAX_ITENS": 2, "TOTAL_MAX": 1},
    {"NUMERO": 4, "CRITERIO": "Livro com ISBN", "PONTOS": 8, "MAX_ITENS": 40, "TOTAL_MAX": 40},
    {"NUMERO": 5, "CRITERIO": "Capítulo de livro", "PONTOS": 4, "MAX_ITENS": 24, "TOTAL_MAX": 24},
]

# Quantidade de novas linhas que serão inseridas
qtd_novas_linhas = len(criterios)

# Função para copiar formatação de uma linha para outra
def copiar_formatacao(origem, destino):
    for col in range(1, ws.max_column + 1):
        celula_origem = ws.cell(row=origem, column=col)
        celula_destino = ws.cell(row=destino, column=col)

        # Copiar valor (se houver)
        celula_destino.value = celula_origem.value

        # Copiar estilos
        if celula_origem.font:
            celula_destino.font = celula_origem.font.copy()
        if celula_origem.fill:
            celula_destino.fill = celula_origem.fill.copy()
        if celula_origem.border:
            celula_destino.border = celula_origem.border.copy()
        if celula_origem.alignment:
            celula_destino.alignment = celula_origem.alignment.copy()
        if celula_origem.number_format:
            celula_destino.number_format = celula_origem.number_format

# Determinar a faixa de linhas que precisam ser movidas
linha_primeira_movida = linha_inicial + 2  # Linha 15
linha_ultima_movida = linha_primeira_movida + 4  # Linha 19

# Remover mesclagens antes de mover
print("📌 Desmesclando células antes de mover...")
for merged_range in list(ws.merged_cells.ranges):
    if merged_range.min_row >= linha_primeira_movida and merged_range.max_row <= linha_ultima_movida:
        ws.unmerge_cells(str(merged_range))

# Mover a faixa de linhas 15 a 19 para baixo na mesma quantidade de novas linhas
print(f"📌 Movendo linhas {linha_primeira_movida}-{linha_ultima_movida} para baixo...")
ws.move_range(f"A{linha_primeira_movida}:Z{linha_ultima_movida}", rows=qtd_novas_linhas)

# Inserir os novos critérios na linha 13 e abaixo
print("✍️ Inserindo critérios mantendo formatação...")
for i, criterio in enumerate(criterios):
    linha_atual = linha_inicial + i

    # Criar espaço para a nova linha copiando a formatação da linha 13
    copiar_formatacao(linha_inicial, linha_atual)

    # Inserir valores nos critérios
    ws.cell(row=linha_atual, column=1, value=criterio["NUMERO"])
    ws.cell(row=linha_atual, column=2, value=criterio["CRITERIO"])
    ws.cell(row=linha_atual, column=3, value=criterio["PONTOS"])
    ws.cell(row=linha_atual, column=4, value=criterio["MAX_ITENS"])
    ws.cell(row=linha_atual, column=5, value=criterio["TOTAL_MAX"])

    # Adicionando a fórmula na última coluna
    ws.cell(row=linha_atual, column=6, value=f"=MIN(E{linha_atual}*C{linha_atual},D{linha_atual})")

print("✅ Critérios adicionados mantendo a formatação!")

# Verificar se as linhas que movemos precisam ser mescladas novamente
print("🔄 Restaurando mesclagem nas novas posições...")
for row in range(linha_primeira_movida + qtd_novas_linhas, linha_ultima_movida + qtd_novas_linhas + 1):
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=6)

# Ajustar a posição da fórmula do somatório (se necessário)
linha_somatorio = linha_ultima_movida + qtd_novas_linhas + 1
ws.cell(row=linha_somatorio, column=6, value=f"=SUM(F{linha_inicial}:F{linha_somatorio-1})")

print("✅ Mesclagens restauradas corretamente!")

# Salvar e fechar
output_path = r"E:\BSI19\TCC2\output.xlsx"
wb.save(output_path)

print(f"🎉 Processamento concluído! Arquivo salvo em: {output_path}")
