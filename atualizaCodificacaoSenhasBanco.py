# -*- coding: utf-8 -*-
"""
Created on Thu Mar 16 03:53:47 2023

@author: Marcos
"""

import psycopg2
import bcrypt

# Conecte-se ao banco de dados PostgreSQL
conn = psycopg2.connect(
        host="localhost",
        database="valida_lattes",
        user="postgres",
        password="admin"
)

# Crie um cursor para executar comandos SQL
cur = conn.cursor()

# Recupere todas as senhas armazenadas no banco de dados
cur.execute("SELECT id_servidor, senha FROM servidores")
rows = cur.fetchall()

# Para cada senha recuperada
for row in rows:
    user_id = row[0]
    senha = row[1]

    # Converta o objeto memoryview em bytes
    senha_bytes = bytes(senha)
    
    # Converta os bytes em uma string
    senha_str = senha_bytes.decode('utf-8')
    
    # Agora você pode usar o método encode na string
    senha_encoded = senha_str.encode('utf-8')

    # Gere um novo hash da senha usando a biblioteca bcrypt
    senha_hash = bcrypt.hashpw(senha_encoded, bcrypt.gensalt())

    # Atualize o registro do usuário no banco de dados com o novo hash da senha
    cur.execute("UPDATE servidores SET senha=%s WHERE id_servidor=%s", (senha_hash, user_id))

# Faça commit das alterações no banco de dados
conn.commit()

# Feche o cursor e a conexão com o banco de dados
cur.close()
conn.close()