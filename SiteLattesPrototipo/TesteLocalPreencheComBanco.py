#!/usr/bin/env python3
"""
Teste local: preenche o template Excel com dados do banco, gera imagem PNG,
fragmentos A4 e monta PDF final com logo do estado centralizado na primeira página.
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, Any, Optional

import psycopg2
import psycopg2.extras
from preencheTemplateExcel import ExcelTemplatePreencher

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from PIL import Image

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


def gerar_pdf_com_fragmentos(fragmentos_dir: Path, logo_path: Path, output_pdf: Path,
                             margem_superior=60, margem_lateral=40, espaco_logo_fragmento=10):
    imagens = sorted(fragmentos_dir.glob("fragmento_*.png"))
    if not imagens:
        raise FileNotFoundError("Nenhum fragmento encontrado em: " + str(fragmentos_dir))

    c = canvas.Canvas(str(output_pdf), pagesize=A4)
    largura_a4, altura_a4 = A4

    logo = ImageReader(str(logo_path))
    # Aumenta logo em 50%
    logo_largura = 180
    logo_altura = 90

    primeira_pagina = True
    for img_path in imagens:
        if not primeira_pagina:
            c.showPage()

        img = Image.open(img_path)
        # Largura máxima da imagem
        img_largura = largura_a4 - 2 * margem_lateral
        img_altura = int(img.height * (img_largura / img.width))

        # Determina posição Y
        if primeira_pagina:
            # Logo centralizado no topo, ajustando um pouco para baixo
            pos_x_logo = (largura_a4 - logo_largura) / 2
            pos_y_logo = altura_a4 - margem_superior - 50  # 50 pts para descer o logo
            c.drawImage(logo, pos_x_logo, pos_y_logo, width=logo_largura, height=logo_altura)

            # Imagem começa logo abaixo do logo
            pos_y_img = pos_y_logo - logo_altura + 70 - espaco_logo_fragmento
            primeira_pagina = False
        else:
            pos_y_img = altura_a4 - margem_superior

        # Ajusta altura se exceder o espaço disponível
        if img_altura > pos_y_img - 20:
            img_altura = pos_y_img - 20

        c.drawImage(str(img_path), margem_lateral, pos_y_img - img_altura, width=img_largura, height=img_altura)

    c.save()
    print("✅ PDF final gerado em:", output_pdf)


def main():
    parser = argparse.ArgumentParser(description="Preenche Excel, gera fragmentos A4 e PDF final.")
    parser.add_argument("--servidor", "-s", required=True, type=int)
    parser.add_argument("--evento", "-e", required=True, type=int)
    parser.add_argument("--template", "-t", default=r"E:\BSI19\TCC2\master_file.xlsx")
    parser.add_argument("--output", "-o", default=r"E:\BSI19\TCC2\output_preenchido_banco.xlsx")
    parser.add_argument("--logo", "-l", default=r"E:\BSI19\TCC2\static\logo_estado.png")
    parser.add_argument("--pdf", "-p", default=r"E:\BSI19\TCC2\output_final.pdf")
    args = parser.parse_args()

    tpl = Path(args.template)
    out = Path(args.output)
    logo_path = Path(args.logo)
    output_pdf = Path(args.pdf)

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

        print("✅ Arquivo Excel gerado em:", out)

        # Gera imagem do Excel preenchido
        out_img = pre.gerar_imagem(str(out))
        print("✅ Imagem gerada em:", out_img)

        # Gera fragmentos A4
        fragmentos_dir = out.parent / "static" / "fragmentos"
        fragmentos = pre.gerar_fragmentos_a4(out_img, fragmentos_dir)

        # Gera PDF final com logo centralizado e todos os fragmentos
        gerar_pdf_com_fragmentos(fragmentos_dir, logo_path, output_pdf)

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
