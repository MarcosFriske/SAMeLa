import openpyxl
from openpyxl.styles import Alignment
from copy import copy
from typing import List, Dict, Any, Union
from pathlib import Path


class ExcelTemplatePreencher:
    """
    Classe responsável por preencher o template Excel com critérios e 
    substituir placeholders do cabeçalho.
    """

    def __init__(self, template_path: Union[str, Path]):
        self.template_path = Path(template_path)

        if not self.template_path.exists():
            raise FileNotFoundError(f"Template não encontrado em: {self.template_path}")

        self.wb = openpyxl.load_workbook(self.template_path)
        self.ws = self.wb.active

    def substituir_placeholders(self, dados: Dict[str, str]) -> None:
        """
        Substitui placeholders no cabeçalho do Excel.

        :param dados: dicionário com chave = placeholder e valor = substituição
        """
        for row in self.ws.iter_rows(min_row=3, max_row=7, min_col=1, max_col=6):
            for cell in row:
                if isinstance(cell.value, str):
                    for placeholder, novo_valor in dados.items():
                        if placeholder in cell.value:
                            cell.value = cell.value.replace(placeholder, novo_valor)

    def encontrar_linha_inicial(self) -> int:
        """
        Localiza a linha onde começa a área de critérios.
        Retorna o número da linha.
        """
        for row in self.ws.iter_rows(min_row=9, max_row=self.ws.max_row):
            if isinstance(row[0].value, str) and "{{LINHA_INICIAL_CRITERIOS_ITEM}}" in row[0].value:
                return row[0].row

        raise ValueError("Linha inicial dos critérios não encontrada no template.")

    def copiar_formatacao(self, origem: int, destino: int) -> None:
        """
        Copia valores e formatação da linha origem para a linha destino.

        :param origem: número da linha origem
        :param destino: número da linha destino
        """
        for col in range(1, self.ws.max_column + 1):
            celula_origem = self.ws.cell(row=origem, column=col)
            celula_destino = self.ws.cell(row=destino, column=col)

            if celula_origem.coordinate not in self.ws.merged_cells:
                celula_destino.value = celula_origem.value

            celula_destino.font = copy(celula_origem.font)
            celula_destino.fill = copy(celula_origem.fill)
            celula_destino.border = copy(celula_origem.border)
            celula_destino.alignment = copy(celula_origem.alignment)
            celula_destino.number_format = celula_origem.number_format

    def preencher_criterios(self, criterios: List[Dict[str, Any]]) -> None:
        """
        Insere os critérios dinamicamente no template, preservando formatação e fórmulas.

        :param criterios: lista de dicionários contendo NUMERO, CRITERIO, PONTOS, MAX_ITENS, TOTAL_MAX
        """
        linha_inicial = self.encontrar_linha_inicial()
        qtd_novas = len(criterios)

        linha_primeira_movida = linha_inicial + 1

        # Desfazer merges abaixo do somatório
        for merged in list(self.ws.merged_cells.ranges):
            if merged.min_row >= linha_primeira_movida:
                self.ws.unmerge_cells(str(merged))

        # Inserir novas linhas (menos 2 pois já existem placeholder + linha exemplo)
        self.ws.insert_rows(idx=linha_inicial + 1, amount=qtd_novas - 2)

        # Preencher critérios
        for i, criterio in enumerate(criterios):
            linha_atual = linha_inicial + i
            self.copiar_formatacao(linha_inicial, linha_atual)

            self.ws.cell(row=linha_atual, column=1, value=criterio["NUMERO"])
            self.ws.cell(row=linha_atual, column=2, value=criterio["CRITERIO"])
            self.ws.cell(row=linha_atual, column=3, value=criterio["PONTOS"])
            self.ws.cell(row=linha_atual, column=4, value=criterio["MAX_ITENS"])
            self.ws.cell(row=linha_atual, column=5, value=criterio["TOTAL_MAX"])

            formula = (
                f"=IF((E{linha_atual}*C{linha_atual})>D{linha_atual},"
                f"D{linha_atual},"
                f"(E{linha_atual}*C{linha_atual}))"
            )

            self.ws.cell(row=linha_atual, column=6, value=formula)

        # Calcular linhas finais
        linha_somatorio = linha_inicial + qtd_novas
        linha_declaracao = linha_somatorio + 1

        # Somatório
        self.ws.merge_cells(start_row=linha_somatorio, start_column=1, end_row=linha_somatorio, end_column=5)
        celula = self.ws.cell(row=linha_somatorio, column=1)
        celula.value = "Somatório dos pontos"
        celula.alignment = Alignment(horizontal="center", vertical="center")

        self.ws.cell(
            row=linha_somatorio,
            column=6,
            value=f"=SUM(F{linha_inicial}:F{linha_somatorio - 1})"
        )

        # Declaração
        self.ws.merge_cells(start_row=linha_declaracao, start_column=1, end_row=linha_declaracao, end_column=6)
        celula_dec = self.ws.cell(row=linha_declaracao, column=1)
        celula_dec.alignment = Alignment(horizontal="center", vertical="center")

    def salvar(self, output_path: Union[str, Path]) -> None:
        """
        Salva o arquivo Excel no destino especificado.
        """
        output_path = Path(output_path)
        self.wb.save(output_path)
