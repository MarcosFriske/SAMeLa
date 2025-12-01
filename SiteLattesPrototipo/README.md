# ValidaLattes - Sistema de Avaliação

Este projeto é uma aplicação Flask para gerenciamento e avaliação de critérios, com geração de PDFs a partir de templates Excel e imagens geradas. O sistema utiliza PostgreSQL como banco de dados e inclui um dump com dados de exemplo.

## Estrutura do Projeto

SiteLattesPrototipo/
│
├─ app.py # Aplicação principal Flask que deve ser executada para rodar o site.
├─ preencheTemplateExcel.py # Lógica de preenchimento de Excel e geração de imagens/PDF.
├─ algoritmoPontuacaoBD.py # Lógica de pontuação usando os XPATHS dos curriculos Lattes que o site utiliza para gerar as avaliações.
├─ templates/ # Templates HTML do Flask que são usados para apresentar as páginas do site.
├─ static/ # Arquivos estáticos (CSS, JS, imagens)
├─ testes/ # Scripts usados durante desenvolvimento, muitos já podem não estar funcionando mas salvos como referencia.
├─ db/
│ └─ dump_valida_lattes.dump # Dump do banco PostgreSQL mais atualizado no momento
├─ requirements.txt # Dependências Python que devem ser instaladas
└─ README.md # Este arquivo


## 1. Requisitos

- Python 3.10 ou superior
- PostgreSQL 14 ou superior
- pip
- Git (opcional, para clonar o projeto)

---

## 2. Instalação do Projeto

### 2.1. Clonar o projeto
```bash
git clone https://github.com/MarcosFriske/SAMeLa.git
```

### 2.2. Criar ambiente virtual
```bash
python -m venv venv
source venv/bin/activate    # Linux / MacOS
venv\Scripts\activate       # Windows
```

### 2.3. Instalar dependências
```bash
pip install -r requirements.txt
```

O requirements.txt contém todas as bibliotecas necessárias, incluindo:

Flask

pandas

psycopg2-binary

Pillow

fpdf

openpyxl

## 3. Configuração do Banco de Dados

### 3.1. Criar banco vazio

Certifique-se de ter PostgreSQL rodando e criar o banco

```bash
createdb -h localhost -p 5432 -U postgres valida_lattes
```

### 3.2. Restaurar dump

```
pg_restore -h localhost -p 5432 -U postgres -d valida_lattes db/dump_valida_lattes.dump
```

Usuário padrão: postgres
Senha: admin
Porta: 5432

## 4. Configuração do App

Verifique o arquivo app.py com as configurações do banco:

```Python
DB_CONFIG = {
    "host": "localhost",
    "database": "valida_lattes",
    "user": "postgres",
    "password": "admin",
    "port": 5432,
}
```

Altere se necessário para o ambiente local.

## 5. Executando o Projeto

Com o ambiente virtual ativo:

```bash
python app.py
```

O servidor Flask estará disponível por padrão em:

```cpp
http://127.0.0.1:5000
```

## 6. Uso do Sistema

Abra o navegador no endereço acima.

Faça login (usuários de exemplo já inclusos no dump do banco).

Acesse os módulos de avaliação, critérios e geração de PDFs.

Para gerar PDFs, a aplicação utiliza os templates Excel em template/.

## 7. Observações

Todas as páginas HTML estão em templates/ e seguem o layout padrão.

Arquivos estáticos (CSS, JS, imagens) estão em static/.

PDFs são gerados dinamicamente e podem ser baixados através da interface do sistema.

É recomendado usar venv para isolar as dependências.




