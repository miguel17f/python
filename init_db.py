import sqlite3

con = sqlite3.connect('database.db')
cur = con.cursor()

# Tabela de utilizadores
cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('admin', 'funcionario'))
)
""")

# Tabela de clientes
cur.execute("""
CREATE TABLE IF NOT EXISTS clients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    morada TEXT,
    servico TEXT NOT NULL
)
""")

# Tabela de horários
cur.execute("""
CREATE TABLE IF NOT EXISTS schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    client_id INTEGER NOT NULL,
    dia TEXT NOT NULL,
    hora_inicio TEXT NOT NULL,
    hora_fim TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (client_id) REFERENCES clients(id)
)
""")

# Inserir dados de teste (ignora duplicados)
cur.execute("INSERT OR IGNORE INTO users (username, password, role) VALUES (?, ?, ?)", ("admin", "admin", "admin"))
cur.execute("INSERT OR IGNORE INTO users (username, password, role) VALUES (?, ?, ?)", ("joao", "joao", "funcionario"))

cur.execute("INSERT OR IGNORE INTO clients (id, nome, morada, servico) VALUES (1, 'Dona Maria', 'Rua das Flores 123', 'Cuidados a idosos')")

cur.execute("""
INSERT OR IGNORE INTO schedules (user_id, client_id, dia, hora_inicio, hora_fim)
VALUES (2, 1, 'Segunda-feira', '09:00', '12:00')
""")

con.commit()
con.close()
print("Base de dados atualizada com clientes e horários.")
