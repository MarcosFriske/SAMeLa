#!/usr/bin/env python3
"""
Teste local: preenche o template Excel com dados do banco e gera imagem PNG.
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, Any, Optional

import psycopg2
import psycopg2.extras

from preencheTemplateExcel import ExcelTemplatePreencher

DB_CONFIG = {
    "host": "localhost",
    "database": "valida_lattes",
    "user": "postgres",
    "password": "admin",
    "port": 5432,
}

def obter_dados_para_excel(conn, servidor_id: int, evento_id: Optional[int] = None) -> Dict[str, Any]:
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cur.execute(
        "SELECT id_servidor, nome, matricula, e_mail, lattes_link, data_ultima_atualizacao_lattes "
        "FROM servidores WHERE id_servidor = %s", (servidor_id,)
    )
    servidor = cur.fetchone()
    if not servidor:
        raise ValueError(f"Servidor id={servidor_id} não encontrado.")

    if not evento_id:
        raise ValueError("O parâmetro --evento é obrigatório para gerar o Excel.")

    cur.execute(
        "SELECT id_evento, identificacao, data_inicio, data_fim, fk_id_instrumento_avaliacao, descricao "
        "FROM eventos WHERE id_evento = %s", (evento_id,)
    )
    evento = cur.fetchone()
    if not evento:
        raise ValueError(f"Evento id={evento_id} não encontrado.")

    instrumento_id = evento["fk_id_instrumento_avaliacao"]
    cur.execute(
        "SELECT id_instrumento_avaliacao, nome, descricao FROM instrumentos_avaliacao WHERE id_instrumento_avaliacao = %s",
        (instrumento_id,)
    )
    instrumento = cur.fetchone()
    if not instrumento:
        raise ValueError(f"Instrumento id={instrumento_id} não encontrado.")

    cur.execute(
        "SELECT id_avaliacao FROM avaliacao WHERE fk_id_servidor = %s AND fk_id_evento = %s "
        "ORDER BY data_avaliacao DESC LIMIT 1", (servidor_id, evento_id)
    )
    avaliacao = cur.fetchone()
    if not avaliacao:
        raise ValueError(f"Nenhuma avaliação encontrada para servidor={servidor_id} e evento={evento_id}.")

    avaliacao_id = avaliacao["id_avaliacao"]
    cur.execute(
        "SELECT item, criterios, pontuacao_por_item, pontuacao_maxima, quantidade, pontuacao_atingida "
        "FROM avaliacao_dados WHERE fk_id_avaliacao = %s ORDER BY item ASC", (avaliacao_id,)
    )
    dados = cur.fetchall()

    criterios = []
    for row in dados:
        item_idx = int(row["item"]) + 1 if row["item"] is not None else 0
        criterios.append({
            "NUMERO": item_idx,
            "CRITERIO": row["criterios"] or "",
            "PONTOS": float(row["pontuacao_por_item"]) if row["pontuacao_por_item"] else 0.0,
            "MAX_ITENS": float(row["pontuacao_maxima"]) if row["pontuacao_maxima"] else 0.0,
            "TOTAL_MAX": int(row["quantidade"]) if row["quantidade"] else 0,
        })

    dados_header = {
        "{{NOME_EDITAL}}": instrumento["nome"] or "Edital",
        "{{COORDENADOR_PROJETO}}": servidor["nome"],
        "{{LINK_CURRICULO_LATTES}}": servidor.get("lattes_link") or "",
        "{{DATA_INICIO_EVENTO}}": evento["data_inicio"].strftime("%d/%m/%Y") if evento["data_inicio"] else "",
        "{{DATA_FIM_EVENTO}}": evento["data_fim"].strftime("%d/%m/%Y") if evento["data_fim"] else "",
    }

    return {
        "dados_header": dados_header,
        "criterios": criterios,
        "avaliacao_id": avaliacao_id,
        "instrumento": dict(instrumento),
        "servidor": dict(servidor),
        "evento": dict(evento),
    }


def main():
    parser = argparse.ArgumentParser(description="Preenche template Excel e gera imagem PNG.")
    parser.add_argument("--servidor", "-s", required=True, type=int)
    parser.add_argument("--evento", "-e", required=True, type=int)
    parser.add_argument("--template", "-t", default=r"E:\BSI19\TCC2\master_file.xlsx")
    parser.add_argument("--output", "-o", default=r"E:\BSI19\TCC2\output_preenchido_banco.xlsx")
    args = parser.parse_args()

    tpl = Path(args.template)
    out = Path(args.output)
    out_img = out.parent / "output.png"  # <- imagem salva na mesma pasta que o Excel

    if not tpl.exists():
        print("Template não encontrado:", tpl)
        sys.exit(2)

    if out.resolve() == tpl.resolve():
        print("Erro: arquivo de saída não pode ser igual ao template.")
        sys.exit(3)

    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        payload = obter_dados_para_excel(conn, servidor_id=args.servidor, evento_id=args.evento)

        dados_header = payload["dados_header"]
        criterios = payload["criterios"]

        print("Header carregado:", dados_header)
        print(f"{len(criterios)} critérios carregados da avaliação.")

        pre = ExcelTemplatePreencher(str(tpl))
        pre.substituir_placeholders(dados_header)
        pre.preencher_criterios(criterios)
        pre.salvar(str(out))

        print("\n✅ Arquivo Excel gerado com sucesso em:", out)

        # Gera imagem a partir do arquivo preenchido e salva na mesma pasta
        pre.gerar_imagem(str(out), col_inicio="A", col_fim="F")
        print("✅ Imagem gerada com sucesso em:", out_img)

    except Exception as exc:
        print("Erro durante execução:", exc)
        raise
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    if any(name in sys.modules for name in ("spyder", "IPython")):
        sys.argv = ["TesteLocalPreencheComBanco.py", "--servidor", "53", "--evento", "4"]
        print("⚠️ Execução detectada via ambiente interativo (Spyder/Jupyter).")
        print("⚠️ Argumentos padrão de teste aplicados automaticamente.\n")

    main()
