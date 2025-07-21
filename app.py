from flask import Flask, render_template, request, redirect, url_for
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user
import sqlite3

app = Flask(__name__)
app.secret_key = 'chave_super_segura'

# Setup do login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Classe User
class User(UserMixin):
    def __init__(self, id, username, role):
        self.id = str(id)
        self.username = username
        self.role = role

# Função para carregar utilizador
@login_manager.user_loader
def load_user(user_id):
    con = sqlite3.connect('database.db')
    cur = con.cursor()
    cur.execute("SELECT id, username, role FROM users WHERE id=?", (user_id,))
    row = cur.fetchone()
    con.close()
    if row:
        return User(*row)
    return None

# Página de login
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        con = sqlite3.connect('database.db')
        cur = con.cursor()
        cur.execute("SELECT id, username, password, role, ativo FROM users WHERE username=?", (username,))
        row = cur.fetchone()
        con.close()

        if row and password == row[2] and row[4] == 1:  # <--- agora verifica se está ativo
            user = User(row[0], row[1], row[3])
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            return "Login inválido ou utilizador inativo."

    return render_template('login.html')

# Painel principal
@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'admin':
        con = sqlite3.connect('database.db')
        cur = con.cursor()

        cur.execute("SELECT COUNT(*) FROM users WHERE role='funcionario' AND ativo=1")
        total_funcionarios = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM clients WHERE ativo=1")
        total_clientes = cur.fetchone()[0]

        con.close()

        return render_template('dashboard.html', user=current_user,
                               total_funcionarios=total_funcionarios,
                               total_clientes=total_clientes)
    else:
        return render_template('dashboard.html', user=current_user)


# Logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/meu-horario')
@login_required
def meu_horario():
    if current_user.role != 'funcionario':
        return "Acesso não autorizado", 403

    con = sqlite3.connect('database.db')
    cur = con.cursor()
    cur.execute("""
        SELECT s.dia, s.hora_inicio, s.hora_fim, c.nome, c.servico
        FROM schedules s
        JOIN clients c ON s.client_id = c.id
        WHERE s.user_id = ?
        ORDER BY
            CASE s.dia
                WHEN 'Segunda-feira' THEN 1
                WHEN 'Terça-feira' THEN 2
                WHEN 'Quarta-feira' THEN 3
                WHEN 'Quinta-feira' THEN 4
                WHEN 'Sexta-feira' THEN 5
                ELSE 6
            END
    """, (current_user.id,))
    horarios = cur.fetchall()
    con.close()

    return render_template("meu_horario.html", horarios=horarios)


@app.route('/admin/funcionarios')
@login_required
def listar_funcionarios():
    if current_user.role != 'admin':
        return "Acesso não autorizado", 403

    con = sqlite3.connect('database.db')
    cur = con.cursor()
    cur.execute("SELECT id, username FROM users WHERE role = 'funcionario'")
    funcionarios = cur.fetchall()
    con.close()
    
    return render_template("admin_funcionarios.html", funcionarios=funcionarios)

@app.route('/admin/funcionario/<int:funcionario_id>')
@login_required
def ver_horario_funcionario(funcionario_id):
    if current_user.role != 'admin':
        return "Acesso não autorizado", 403

    con = sqlite3.connect('database.db')
    cur = con.cursor()

    # Obter nome do funcionário
    cur.execute("SELECT username FROM users WHERE id=?", (funcionario_id,))
    nome = cur.fetchone()
    if not nome:
        con.close()
        return "Funcionário não encontrado", 404

    cur.execute("""
        SELECT s.id, s.dia, s.hora_inicio, s.hora_fim, c.nome, c.servico
        FROM schedules s
        JOIN clients c ON s.client_id = c.id
        WHERE s.user_id = ?
        ORDER BY
            CASE s.dia
                WHEN 'Segunda-feira' THEN 1
                WHEN 'Terça-feira' THEN 2
                WHEN 'Quarta-feira' THEN 3
                WHEN 'Quinta-feira' THEN 4
                WHEN 'Sexta-feira' THEN 5
                WHEN 'Sábado' THEN 6
                WHEN 'Domingo' THEN 7
            END,
            s.hora_inicio
    """, (funcionario_id,))

    horarios = cur.fetchall()

    con.close()

    return render_template("admin_ver_horarios.html", nome=nome[0], horarios=horarios, funcionario_id=funcionario_id)

@app.route('/admin/usuarios')
@login_required
def gerir_usuarios():
    if current_user.role != 'admin':
        return "Acesso não autorizado", 403

    con = sqlite3.connect('database.db')
    cur = con.cursor()
    cur.execute("SELECT id, username FROM users WHERE role='funcionario' AND ativo=1")
    funcionarios = cur.fetchall()
    con.close()

    return render_template("admin_usuarios.html", funcionarios=funcionarios)

@app.route('/admin/usuarios/novo', methods=['GET', 'POST'])
@login_required
def criar_funcionario():
    if current_user.role != 'admin':
        return "Acesso não autorizado", 403

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm = request.form['confirm']

        if password != confirm:
            return "As palavras-passe não coincidem."

        con = sqlite3.connect('database.db')
        cur = con.cursor()
        try:
            cur.execute("INSERT INTO users (username, password, role) VALUES (?, ?, 'funcionario')", (username, password))
            con.commit()
        except sqlite3.IntegrityError:
            return "Já existe um utilizador com esse nome."
        finally:
            con.close()

        return redirect(url_for('gerir_usuarios'))

    return render_template("admin_criar_funcionario.html")

@app.route('/admin/usuarios/<int:funcionario_id>/password', methods=['GET', 'POST'])
@login_required
def alterar_password(funcionario_id):
    if current_user.role != 'admin':
        return "Acesso não autorizado", 403

    if request.method == 'POST':
        nova_pass = request.form['nova_pass']
        confirmar = request.form['confirmar']

        if nova_pass != confirmar:
            return "As palavras-passe não coincidem."

        con = sqlite3.connect('database.db')
        cur = con.cursor()
        cur.execute("UPDATE users SET password=? WHERE id=?", (nova_pass, funcionario_id))
        con.commit()
        con.close()

        return redirect(url_for('gerir_usuarios'))

    return render_template("admin_alterar_password.html")


@app.route('/admin/usuarios/<int:funcionario_id>/desativar', methods=['POST'])
@login_required
def desativar_funcionario(funcionario_id):
    if current_user.role != 'admin':
        return "Acesso não autorizado", 403

    con = sqlite3.connect('database.db')
    cur = con.cursor()
    cur.execute("UPDATE users SET ativo=0 WHERE id=?", (funcionario_id,))
    con.commit()
    con.close()

    return redirect(url_for('gerir_usuarios'))


@app.route('/admin/usuarios/inativos')
@login_required
def listar_inativos():
    if current_user.role != 'admin':
        return "Acesso não autorizado", 403

    con = sqlite3.connect('database.db')
    cur = con.cursor()
    cur.execute("SELECT id, username FROM users WHERE role='funcionario' AND ativo=0")
    funcionarios = cur.fetchall()
    con.close()

    return render_template("admin_inativos.html", funcionarios=funcionarios)

@app.route('/admin/usuarios/<int:funcionario_id>/reativar', methods=['POST'])
@login_required
def reativar_funcionario(funcionario_id):
    if current_user.role != 'admin':
        return "Acesso não autorizado", 403

    con = sqlite3.connect('database.db')
    cur = con.cursor()
    cur.execute("UPDATE users SET ativo=1 WHERE id=?", (funcionario_id,))
    con.commit()
    con.close()

    return redirect(url_for('listar_inativos'))


@app.route('/admin/clientes/novo', methods=['GET', 'POST'])
@login_required
def adicionar_cliente():
    if current_user.role != 'admin':
        return "Acesso não autorizado", 403

    if request.method == 'POST':
        nome = request.form['nome']
        morada = request.form['morada']
        servico = request.form['servico']

        con = sqlite3.connect('database.db')
        cur = con.cursor()
        cur.execute("INSERT INTO clients (nome, morada, servico, ativo) VALUES (?, ?, ?, 1)", (nome, morada, servico))
        con.commit()
        con.close()

        return redirect(url_for('listar_clientes'))

    return render_template("admin_adicionar_cliente.html")

@app.route('/admin/clientes')
@login_required
def listar_clientes():
    if current_user.role != 'admin':
        return "Acesso não autorizado", 403

    con = sqlite3.connect('database.db')
    cur = con.cursor()
    cur.execute("SELECT id, nome, morada, servico FROM clients WHERE ativo = 1")
    clientes = cur.fetchall()
    con.close()

    return render_template("admin_clientes.html", clientes=clientes)


@app.route('/admin/clientes/<int:cliente_id>/editar', methods=['GET', 'POST'])
@login_required
def editar_cliente(cliente_id):
    if current_user.role != 'admin':
        return "Acesso não autorizado", 403

    con = sqlite3.connect('database.db')
    cur = con.cursor()

    if request.method == 'POST':
        nome = request.form['nome']
        morada = request.form['morada']
        servico = request.form['servico']
        cur.execute("""
            UPDATE clients SET nome=?, morada=?, servico=?
            WHERE id=?
        """, (nome, morada, servico, cliente_id))
        con.commit()
        con.close()
        return redirect(url_for('listar_clientes'))

    cur.execute("SELECT nome, morada, servico FROM clients WHERE id=?", (cliente_id,))
    cliente = cur.fetchone()
    con.close()

    if not cliente:
        return "Cliente não encontrado", 404

    return render_template("admin_editar_cliente.html", cliente=cliente, cliente_id=cliente_id)

@app.route('/admin/clientes/<int:cliente_id>/remover', methods=['POST'])
@login_required
def remover_cliente(cliente_id):
    if current_user.role != 'admin':
        return "Acesso não autorizado", 403

    con = sqlite3.connect('database.db')
    cur = con.cursor()

    # ⚠️ Certifica-te que não há horários associados
    cur.execute("SELECT COUNT(*) FROM schedules WHERE client_id=?", (cliente_id,))
    count = cur.fetchone()[0]

    if count > 0:
        con.close()
        return "Não é possível remover um cliente com horários atribuídos."

    cur.execute("UPDATE clients SET ativo = 0 WHERE id = ?", (cliente_id,))
    con.commit()
    con.close()

    return redirect(url_for('listar_clientes'))

@app.route('/admin/clientes/inativos')
@login_required
def listar_clientes_inativos():
    if current_user.role != 'admin':
        return "Acesso não autorizado", 403

    con = sqlite3.connect('database.db')
    cur = con.cursor()
    cur.execute("SELECT id, nome, morada, servico FROM clients WHERE ativo = 0")
    clientes = cur.fetchall()
    con.close()

    return render_template("admin_clientes_inativos.html", clientes=clientes)

@app.route('/admin/clientes/<int:cliente_id>/reativar', methods=['POST'])
@login_required
def reativar_cliente(cliente_id):
    if current_user.role != 'admin':
        return "Acesso não autorizado", 403

    con = sqlite3.connect('database.db')
    cur = con.cursor()
    cur.execute("UPDATE clients SET ativo = 1 WHERE id = ?", (cliente_id,))
    con.commit()
    con.close()

    return redirect(url_for('listar_clientes_inativos'))

@app.route('/admin/horarios/novo', methods=['GET', 'POST'])
@login_required
def criar_horario():
    if current_user.role != 'admin':
        return "Acesso não autorizado", 403

    con = sqlite3.connect('database.db')
    cur = con.cursor()

    # Obter dados para os dropdowns
    cur.execute("SELECT id, username FROM users WHERE role='funcionario' AND ativo=1")
    funcionarios = cur.fetchall()

    cur.execute("SELECT id, nome FROM clients WHERE ativo=1")
    clientes = cur.fetchall()

    if request.method == 'POST':
        funcionario_id = request.form['funcionario']
        cliente_id = request.form['cliente']
        dia = request.form['dia']
        hora_inicio = request.form['hora_inicio']
        hora_fim = request.form['hora_fim']

        # Inserir horário
        # Validar se já existe horário sobreposto
        cur.execute("""
            SELECT hora_inicio, hora_fim FROM schedules
            WHERE user_id = ? AND dia = ?
        """, (funcionario_id, dia))
        horarios = cur.fetchall()

        from datetime import datetime

        fmt = "%H:%M"
        novo_inicio = datetime.strptime(hora_inicio, fmt)
        novo_fim = datetime.strptime(hora_fim, fmt)

        for h_inicio, h_fim in horarios:
            existente_inicio = datetime.strptime(h_inicio, fmt)
            existente_fim = datetime.strptime(h_fim, fmt)

            if novo_inicio < existente_fim and novo_fim > existente_inicio:
                con.close()
                return "Erro: O funcionário já tem um horário nesse intervalo."

        # Inserir horário (se passou a validação)
        cur.execute("""
            INSERT INTO schedules (user_id, client_id, dia, hora_inicio, hora_fim)
            VALUES (?, ?, ?, ?, ?)
        """, (funcionario_id, cliente_id, dia, hora_inicio, hora_fim))
        con.commit()
        con.close()

        return redirect(url_for('listar_funcionarios'))  # ou dashboard

    con.close()
    return render_template('admin_criar_horario.html', funcionarios=funcionarios, clientes=clientes)


@app.route('/admin/horarios')
@login_required
def ver_horarios():
    if current_user.role != 'admin':
        return "Acesso não autorizado", 403

    con = sqlite3.connect('database.db')
    cur = con.cursor()

    cur.execute("""
        SELECT u.username, c.nome, s.dia, s.hora_inicio, s.hora_fim
        FROM schedules s
        JOIN users u ON s.user_id = u.id
        JOIN clients c ON s.client_id = c.id
        ORDER BY 
            CASE s.dia
                WHEN 'Segunda-feira' THEN 1
                WHEN 'Terça-feira' THEN 2
                WHEN 'Quarta-feira' THEN 3
                WHEN 'Quinta-feira' THEN 4
                WHEN 'Sexta-feira' THEN 5
                WHEN 'Sábado' THEN 6
                WHEN 'Domingo' THEN 7
            END,
            s.hora_inicio
    """)
    horarios = cur.fetchall()
    con.close()

    return render_template("admin_ver_horarios.html", horarios=horarios)


@app.route('/admin/horarios/<int:horario_id>/remover', methods=['POST'])
@login_required
def remover_horario(horario_id):
    if current_user.role != 'admin':
        return "Acesso não autorizado", 403

    con = sqlite3.connect('database.db')
    cur = con.cursor()

    # Saber o user_id para redirecionar
    cur.execute("SELECT user_id FROM schedules WHERE id=?", (horario_id,))
    row = cur.fetchone()
    if not row:
        con.close()
        return "Horário não encontrado", 404

    user_id = row[0]

    cur.execute("DELETE FROM schedules WHERE id=?", (horario_id,))
    con.commit()
    con.close()

    return redirect(url_for('ver_horario_funcionario', funcionario_id=user_id))


@app.route('/admin/horarios')
@login_required
def listar_todos_horarios():
    if current_user.role != 'admin':
        return "Acesso não autorizado", 403

    con = sqlite3.connect('database.db')
    cur = con.cursor()

    cur.execute("""
        SELECT s.id, s.dia, s.hora_inicio, s.hora_fim, c.nome, c.servico
        FROM schedules s
        JOIN clients c ON s.client_id = c.id
        ORDER BY
            CASE s.dia
                WHEN 'Segunda-feira' THEN 1
                WHEN 'Terça-feira' THEN 2
                WHEN 'Quarta-feira' THEN 3
                WHEN 'Quinta-feira' THEN 4
                WHEN 'Sexta-feira' THEN 5
                WHEN 'Sábado' THEN 6
                WHEN 'Domingo' THEN 7
            END, s.hora_inicio
    """)
    horarios = cur.fetchall()
    con.close()

    return render_template("admin_listar_horarios.html", horarios=horarios)

@app.route('/admin/horarios/<int:horario_id>/editar', methods=['GET', 'POST'])
@login_required
def editar_horario(horario_id):
    if current_user.role != 'admin':
        return "Acesso não autorizado", 403

    con = sqlite3.connect('database.db')
    cur = con.cursor()

    cur.execute("SELECT user_id, client_id, dia, hora_inicio, hora_fim FROM schedules WHERE id=?", (horario_id,))
    horario = cur.fetchone()
    if not horario:
        con.close()
        return "Horário não encontrado", 404

    user_id = horario[0]  # <- para usarmos no botão Cancelar

    # Obter nome do funcionário
    cur.execute("SELECT username FROM users WHERE id=?", (user_id,))
    funcionario_nome = cur.fetchone()[0]

    # Obter lista de clientes
    cur.execute("SELECT id, nome FROM clients WHERE ativo=1")
    clientes = cur.fetchall()

    if request.method == 'POST':
        cliente_id = request.form['cliente']
        dia = request.form['dia']
        hora_inicio = request.form['hora_inicio']
        hora_fim = request.form['hora_fim']

        # Verificar sobreposição
        cur.execute("""
            SELECT hora_inicio, hora_fim FROM schedules
            WHERE user_id=? AND dia=? AND id != ?
        """, (user_id, dia, horario_id))
        conflitos = cur.fetchall()

        from datetime import datetime
        fmt = "%H:%M"
        novo_inicio = datetime.strptime(hora_inicio, fmt)
        novo_fim = datetime.strptime(hora_fim, fmt)

        for h_inicio, h_fim in conflitos:
            existente_inicio = datetime.strptime(h_inicio, fmt)
            existente_fim = datetime.strptime(h_fim, fmt)
            if novo_inicio < existente_fim and novo_fim > existente_inicio:
                con.close()
                return "Erro: Sobreposição com outro horário."

        # Atualizar
        cur.execute("""
            UPDATE schedules
            SET client_id=?, dia=?, hora_inicio=?, hora_fim=?
            WHERE id=?
        """, (cliente_id, dia, hora_inicio, hora_fim, horario_id))
        con.commit()
        con.close()

        return redirect(url_for('ver_horario_funcionario', funcionario_id=user_id))

    con.close()
    return render_template("admin_editar_horario.html",
                           horario=horario,
                           clientes=clientes,
                           funcionario_nome=funcionario_nome,
                           user_id=user_id)  # <- importante para o botão Cancelar



if __name__ == '__main__':
    app = Flask(__name__)
