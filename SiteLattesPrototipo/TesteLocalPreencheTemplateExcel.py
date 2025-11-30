from preencheTemplateExcel import ExcelTemplatePreencher

def testar_preenchimento():
    # Caminho do template e caminho de saída
    template = r"E:\BSI19\TCC2\master_file.xlsx"
    output = r"E:\BSI19\TCC2\output_teste.xlsx"

    # Placeholders para testar
    dados_header = {
        "{{NOME_EDITAL}}": "Edital 2025",
        "{{COORDENADOR_PROJETO}}": "Dr. João Silva",
        "{{LINK_CURRICULO_LATTES}}": "http://lattes.cnpq.br/123456789",
        "{{DATA_INICIO_EVENTO}}": "30/11/2025",
        "{{DATA_FIM_EVENTO}}": "30/12/2025",
    }

    # Lista de critérios mockada
    criterios_mock = [
        {"NUMERO": 1, "CRITERIO": "Titulação - Doutorado", "PONTOS": 25, "MAX_ITENS": 2, "TOTAL_MAX": 1},
        {"NUMERO": 2, "CRITERIO": "Livro com ISBN", "PONTOS": 8, "MAX_ITENS": 40, "TOTAL_MAX": 40},
        {"NUMERO": 3, "CRITERIO": "Capítulo de livro", "PONTOS": 4, "MAX_ITENS": 24, "TOTAL_MAX": 24},
        {"NUMERO": 4, "CRITERIO": "Capítulo de livro2", "PONTOS": 4, "MAX_ITENS": 24, "TOTAL_MAX": 24},
        {"NUMERO": 5, "CRITERIO": "Capítulo de livro3", "PONTOS": 4, "MAX_ITENS": 24, "TOTAL_MAX": 24},
        {"NUMERO": 6, "CRITERIO": "Capítulo de livro4", "PONTOS": 4, "MAX_ITENS": 24, "TOTAL_MAX": 24},
        {"NUMERO": 7, "CRITERIO": "Capítulo de livro5", "PONTOS": 4, "MAX_ITENS": 24, "TOTAL_MAX": 24},
        {"NUMERO": 8, "CRITERIO": "Capítulo de livro6", "PONTOS": 4, "MAX_ITENS": 24, "TOTAL_MAX": 24},
    ]

    # Instanciar a classe usando o template
    preenchedor = ExcelTemplatePreencher(template)

    # Testar substituição do cabeçalho
    preenchedor.substituir_placeholders(dados_header)

    # Testar inserção dos critérios
    preenchedor.preencher_criterios(criterios_mock)

    # Salvar em outro arquivo para não sobrescrever o original
    preenchedor.salvar(output)

    print(f"Arquivo de teste gerado com sucesso em: {output}")


if __name__ == "__main__":
    testar_preenchimento()