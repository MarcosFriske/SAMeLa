#!/usr/bin/env python3
"""
Teste local: preenche o template Excel com dados vindos do banco (Postgres).

Uso:
    python TesteLocalPreencheComBanco.py --servidor 1 --evento 4

O EVENTO É OBRIGATÓRIO para este fluxo, pois é ele que define:
    - qual é o instrumento utilizado
    - qual avaliação pegar
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional

import psycopg2
import psycopg2.extras

from preencheTemplateExcel import ExcelTemplatePreencher



# ---------------------------------------------------------------------------
# CONFIG LOCAL DO BANCO (temporário)
# ---------------------------------------------------------------------------
DB_CONFIG = {
    "host": "localhost",
    "database": "valida_lattes",
    "user": "postgres",
    "password": "admin",
    "port": 5432,
}



# ---------------------------------------------------------------------------
# FUNÇÃO PRINCIPAL QUE MONTA OS DADOS PARA PREENCHER O EXCEL
# ---------------------------------------------------------------------------
def obter_dados_para_excel(
    conn,
    servidor_id: int,
    evento_id: Optional[int] = None,
    instrumento_id: Optional[int] = None,   # ignorado quando evento é passado
) -> Dict[str, Any]:
    """
    Carrega:

        - dados_header: dict com placeholders -> valores reais
        - criterios: lista no formato esperado pelo ExcelTemplatePreencher
        - metadados diversos (instrumento, servidor, evento)

    Critérios vêm de:

        avaliacao_dados (pontuação por item, quantidade, pontuação máxima)
    """

    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # -----------------------------------------------------------------------
    # 1) Buscar dados do servidor
    # -----------------------------------------------------------------------
    cur.execute(
        """
        SELECT id_servidor, nome, matricula, e_mail, lattes_link,
               data_ultima_atualizacao_lattes
        FROM servidores
        WHERE id_servidor = %s
        """,
        (servidor_id,)
    )
    servidor = cur.fetchone()
    if not servidor:
        raise ValueError(f"Servidor id={servidor_id} não encontrado.")



    # -----------------------------------------------------------------------
    # 2) Evento é obrigatório — dele extraímos o instrumento e a avaliação
    # -----------------------------------------------------------------------
    if not evento_id:
        raise ValueError("O parâmetro --evento é obrigatório para gerar o Excel.")

    cur.execute(
        """
        SELECT id_evento, identificacao, data_inicio, data_fim,
               fk_id_instrumento_avaliacao, descricao
        FROM eventos
        WHERE id_evento = %s
        """,
        (evento_id,)
    )
    evento = cur.fetchone()

    if not evento:
        raise ValueError(f"Evento id={evento_id} não encontrado.")

    instrumento_id = evento["fk_id_instrumento_avaliacao"]



    # -----------------------------------------------------------------------
    # 3) Buscar instrumento
    # -----------------------------------------------------------------------
    cur.execute(
        """
        SELECT id_instrumento_avaliacao, nome, descricao
        FROM instrumentos_avaliacao
        WHERE id_instrumento_avaliacao = %s
        """,
        (instrumento_id,)
    )
    instrumento = cur.fetchone()

    if not instrumento:
        raise ValueError(f"Instrumento id={instrumento_id} não encontrado.")



    # -----------------------------------------------------------------------
    # 4) Buscar AVALIAÇÃO RECENTE para este servidor + evento
    # -----------------------------------------------------------------------
    cur.execute(
        """
        SELECT id_avaliacao
        FROM avaliacao
        WHERE fk_id_servidor = %s
          AND fk_id_evento  = %s
        ORDER BY data_avaliacao DESC
        LIMIT 1
        """,
        (servidor_id, evento_id)
    )
    avaliacao = cur.fetchone()

    if not avaliacao:
        raise ValueError(
            f"Nenhuma avaliação encontrada para servidor={servidor_id} e evento={evento_id}."
        )

    avaliacao_id = avaliacao["id_avaliacao"]



    # -----------------------------------------------------------------------
    # 5) Carregar CRITÉRIOS REAIS a partir de avaliacao_dados
    # -----------------------------------------------------------------------
    cur.execute(
        """
        SELECT
            item,
            criterios,
            pontuacao_por_item,
            pontuacao_maxima,
            quantidade,
            pontuacao_atingida
        FROM avaliacao_dados
        WHERE fk_id_avaliacao = %s
        ORDER BY item ASC
        """,
        (avaliacao_id,)
    )
    dados = cur.fetchall()

    criterios = []
    for row in dados:
        # segurança: valores nulos -> 0 / 0.0 para evitar erros
        item_idx = int(row["item"]) + 1 if row["item"] is not None else 0
        criterio_text = row["criterios"] or ""
        pontos_por_item = float(row["pontuacao_por_item"]) if row["pontuacao_por_item"] is not None else 0.0
    
        # <-- trocados conforme seu pedido: quantidade <-> pontuacao_maxima -->
        quantidade = int(row["quantidade"]) if row["quantidade"] is not None else 0
        pontuacao_maxima = float(row["pontuacao_maxima"]) if row["pontuacao_maxima"] is not None else 0.0
    
        criterios.append({
            "NUMERO": item_idx,
            "CRITERIO": criterio_text,
            "PONTOS": pontos_por_item,
            "MAX_ITENS": pontuacao_maxima,        # pontuação máxima (cap em pontos)
            "TOTAL_MAX": quantidade,   # número máximo de itens permitidos
        })

    # -----------------------------------------------------------------------
    # 6) Preencher placeholders do Excel
    # -----------------------------------------------------------------------
    dados_header = {
        "{{NOME_EDITAL}}": instrumento["nome"] or "Edital",
        "{{COORDENADOR_PROJETO}}": servidor["nome"],
        "{{LINK_CURRICULO_LATTES}}": servidor.get("lattes_link") or "",
        "{{DATA_INICIO_EVENTO}}": (
            evento["data_inicio"].strftime("%d/%m/%Y") if evento["data_inicio"] else ""
        ),
        "{{DATA_FIM_EVENTO}}": (
            evento["data_fim"].strftime("%d/%m/%Y") if evento["data_fim"] else ""
        ),
    }

    return {
        "dados_header": dados_header,
        "criterios": criterios,
        "avaliacao_id": avaliacao_id,
        "instrumento": dict(instrumento),
        "servidor": dict(servidor),
        "evento": dict(evento),
    }



# ---------------------------------------------------------------------------
# ENTRYPOINT
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Preenche template Excel usando dados reais do banco PostgreSQL.")
    parser.add_argument("--servidor", "-s", required=True, type=int, help="ID do servidor no banco.")
    parser.add_argument("--evento", "-e", required=True, type=int, help="ID do evento.")
    parser.add_argument("--template", "-t", default=r"E:\BSI19\TCC2\master_file.xlsx", help="Template Excel.")
    parser.add_argument("--output", "-o", default=r"E:\BSI19\TCC2\output_preenchido_banco.xlsx", help="Arquivo de saída.")
    args = parser.parse_args()

    tpl = Path(args.template)
    out = Path(args.output)

    if not tpl.exists():
        print("Template não encontrado:", tpl)
        sys.exit(2)

    if out.resolve() == tpl.resolve():
        print("Erro: arquivo de saída não pode ser igual ao template.")
        sys.exit(3)

    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)

        payload = obter_dados_para_excel(
            conn,
            servidor_id=args.servidor,
            evento_id=args.evento,
        )

        dados_header = payload["dados_header"]
        criterios = payload["criterios"]

        print("Header carregado:", dados_header)
        print(f"{len(criterios)} critérios carregados da avaliação.")

        pre = ExcelTemplatePreencher(str(tpl))
        pre.substituir_placeholders(dados_header)
        pre.preencher_criterios(criterios)
        pre.salvar(str(out))

        print("\n✅ Arquivo gerado com sucesso em:", out)

    except Exception as exc:
        print("Erro durante execução:", exc)
        raise

    finally:
        if conn:
            conn.close()



if __name__ == "__main__":

    # ------------------------------------------------------
    # Execução em ambiente interativo (Spyder, Jupyter, etc.)
    # ------------------------------------------------------
    if any(name in sys.modules for name in ("spyder", "IPython")):
        # Ajuste SOMENTE para facilitar testes locais.
        # NÃO interfere quando chamado pelo terminal.
        sys.argv = [
            "TesteLocalPreencheComBanco.py",
            "--servidor", "53",
            "--evento", "4",
            # "--template", r"E:\BSI19\TCC2\master_file.xlsx",   # opcional
            # "--output",   r"E:\BSI19\TCC2\output_preenchido_banco.xlsx",
        ]

        print("⚠️ Execução detectada via ambiente interativo (Spyder/Jupyter).")
        print("⚠️ Argumentos padrão de teste foram aplicados automaticamente.\n")

    # ------------------------------------------------------
    # Execução normal
    # ------------------------------------------------------
    main()
