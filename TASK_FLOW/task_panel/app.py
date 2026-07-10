from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3
import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.secret_key = 'chave_secreta_flask_2024'

# ─── Banco de Dados ───────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS tarefas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            descricao TEXT,
            status TEXT DEFAULT 'pendente',
            usuario_id INTEGER NOT NULL,
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        )
    ''')
    conn.commit()
    conn.close()

# ─── Decorador de Autenticação ────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'usuario_id' not in session:
            flash('Faça login para acessar esta página.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

# ─── Dica do Dia (sistema interno, 100% em português) ────────────────────────
# Lista de frases motivacionais fixas. Uma frase diferente é escolhida
# automaticamente a cada dia, mas permanece a mesma durante todo o dia,
# mesmo que a página seja recarregada várias vezes.

FRASES_DO_DIA = [
    "A jornada de mil quilômetros começa com um único passo.",
    "O sucesso é a soma de pequenos esforços repetidos dia após dia.",
    "Não espere por uma crise para descobrir o que é importante na sua vida.",
    "A disciplina é a ponte entre metas e realizações.",
    "Cada tarefa concluída é um passo mais perto do seu objetivo.",
    "Organização não é um talento, é um hábito que se constrói.",
    "Faça hoje o que outros não querem fazer; amanhã você terá o que outros não têm.",
    "O foco de hoje constrói a vitória de amanhã.",
    "Produtividade é fazer escolhas inteligentes sobre onde investir seu tempo.",
    "Pequenos progressos diários levam a grandes resultados.",
    "Comece onde você está, use o que você tem, faça o que você pode.",
    "A persistência realiza o impossível.",
    "Planejar é trazer o futuro para o presente, para que você possa agir agora.",
    "Quem tem um propósito forte suporta quase qualquer método.",
    "Grandes conquistas exigem tempo, paciência e organização.",
    "Você não precisa ser perfeito, só precisa ser consistente.",
    "A clareza sobre o que fazer hoje nasce de um bom planejamento.",
    "Cada passo pequeno conta quando você está construindo algo grande.",
    "Termine o que começou: a sensação de dever cumprido não tem preço.",
    "O segredo de progredir é começar.",
]

DICA_PADRAO = "Continue firme: cada tarefa concluída é uma vitória conquistada."

def obter_dica_do_dia():
    """Retorna a frase motivacional do dia, sempre a mesma durante 24h."""
    try:
        indice = datetime.date.today().toordinal() % len(FRASES_DO_DIA)
        return FRASES_DO_DIA[indice]
    except Exception:
        return DICA_PADRAO

# ─── Rotas de Autenticação ────────────────────────────────────────────────────

@app.route('/')
def index():
    if 'usuario_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nome = request.form['nome'].strip()
        email = request.form['email'].strip().lower()
        senha = generate_password_hash(request.form['senha'])
        try:
            conn = get_db()
            conn.execute('INSERT INTO usuarios (nome, email, senha) VALUES (?, ?, ?)',
                         (nome, email, senha))
            conn.commit()
            conn.close()
            flash('Conta criada com sucesso! Faça login para continuar.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Este e-mail já está cadastrado.', 'danger')
    return render_template('registro.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        senha = request.form['senha']
        conn = get_db()
        usuario = conn.execute('SELECT * FROM usuarios WHERE email = ?', (email,)).fetchone()
        conn.close()
        if usuario and check_password_hash(usuario['senha'], senha):
            session['usuario_id'] = usuario['id']
            session['usuario_nome'] = usuario['nome']
            return redirect(url_for('dashboard'))
        flash('E-mail ou senha incorretos.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Você saiu com sucesso.', 'info')
    return redirect(url_for('login'))

# ─── Dashboard ────────────────────────────────────────────────────────────────

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db()
    tarefas = conn.execute(
        'SELECT * FROM tarefas WHERE usuario_id = ? ORDER BY id DESC',
        (session['usuario_id'],)
    ).fetchall()
    conn.close()

    dica = obter_dica_do_dia()

    total = len(tarefas)
    pendentes = sum(1 for t in tarefas if t['status'] == 'pendente')
    em_andamento = sum(1 for t in tarefas if t['status'] == 'em_andamento')
    concluidas = sum(1 for t in tarefas if t['status'] == 'concluida')

    return render_template('dashboard.html',
                           tarefas=tarefas,
                           dica=dica,
                           total=total,
                           pendentes=pendentes,
                           em_andamento=em_andamento,
                           concluidas=concluidas)

# ─── Atualização de status via AJAX (sem recarregar a página) ────────────────

@app.route('/tarefas/status/<int:id>', methods=['POST'])
@login_required
def atualizar_status(id):
    dados = request.get_json(silent=True) or {}
    novo_status = dados.get('status')
    status_validos = ('pendente', 'em_andamento', 'concluida')

    if novo_status not in status_validos:
        return jsonify({'sucesso': False, 'mensagem': 'Status inválido.'}), 400

    conn = get_db()
    tarefa = conn.execute(
        'SELECT id FROM tarefas WHERE id = ? AND usuario_id = ?',
        (id, session['usuario_id'])
    ).fetchone()

    if not tarefa:
        conn.close()
        return jsonify({'sucesso': False, 'mensagem': 'Tarefa não encontrada.'}), 404

    conn.execute(
        'UPDATE tarefas SET status = ? WHERE id = ? AND usuario_id = ?',
        (novo_status, id, session['usuario_id'])
    )
    conn.commit()
    conn.close()

    return jsonify({'sucesso': True, 'status': novo_status, 'mensagem': 'Status atualizado!'})

# ─── CRUD de Tarefas ──────────────────────────────────────────────────────────

@app.route('/tarefas/nova', methods=['GET', 'POST'])
@login_required
def nova_tarefa():
    if request.method == 'POST':
        titulo = request.form['titulo'].strip()
        descricao = request.form['descricao'].strip()
        conn = get_db()
        conn.execute(
            'INSERT INTO tarefas (titulo, descricao, usuario_id) VALUES (?, ?, ?)',
            (titulo, descricao, session['usuario_id'])
        )
        conn.commit()
        conn.close()
        flash('Tarefa criada com sucesso!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('nova_tarefa.html')

@app.route('/tarefas/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_tarefa(id):
    conn = get_db()
    tarefa = conn.execute(
        'SELECT * FROM tarefas WHERE id = ? AND usuario_id = ?',
        (id, session['usuario_id'])
    ).fetchone()
    if not tarefa:
        conn.close()
        flash('Tarefa não encontrada.', 'danger')
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        titulo = request.form['titulo'].strip()
        descricao = request.form['descricao'].strip()
        status = request.form['status']
        conn.execute(
            'UPDATE tarefas SET titulo=?, descricao=?, status=? WHERE id=?',
            (titulo, descricao, status, id)
        )
        conn.commit()
        conn.close()
        flash('Tarefa atualizada com sucesso!', 'success')
        return redirect(url_for('dashboard'))
    conn.close()
    return render_template('editar_tarefa.html', tarefa=tarefa)

@app.route('/tarefas/deletar/<int:id>')
@login_required
def deletar_tarefa(id):
    conn = get_db()
    conn.execute(
        'DELETE FROM tarefas WHERE id = ? AND usuario_id = ?',
        (id, session['usuario_id'])
    )
    conn.commit()
    conn.close()
    flash('Tarefa removida com sucesso.', 'info')
    return redirect(url_for('dashboard'))


# ─── API REST — Tarefas em JSON (Desafio Avançado) ───────────────────────────

@app.route('/api/tarefas', methods=['GET'])
@login_required
def api_listar_tarefas():
    """Retorna todas as tarefas do usuário logado em JSON."""
    status_filtro = request.args.get('status')
    conn = get_db()
    if status_filtro and status_filtro in ('pendente', 'em_andamento', 'concluida'):
        tarefas = conn.execute(
            'SELECT * FROM tarefas WHERE usuario_id = ? AND status = ? ORDER BY id DESC',
            (session['usuario_id'], status_filtro)
        ).fetchall()
    else:
        tarefas = conn.execute(
            'SELECT * FROM tarefas WHERE usuario_id = ? ORDER BY id DESC',
            (session['usuario_id'],)
        ).fetchall()
    conn.close()
    return jsonify([dict(t) for t in tarefas])

@app.route('/api/tarefas/<int:id>', methods=['GET'])
@login_required
def api_obter_tarefa(id):
    """Retorna uma tarefa específica em JSON."""
    conn = get_db()
    tarefa = conn.execute(
        'SELECT * FROM tarefas WHERE id = ? AND usuario_id = ?',
        (id, session['usuario_id'])
    ).fetchone()
    conn.close()
    if not tarefa:
        return jsonify({'erro': 'Tarefa não encontrada.'}), 404
    return jsonify(dict(tarefa))

@app.route('/api/tarefas', methods=['POST'])
@login_required
def api_criar_tarefa():
    """Cria uma nova tarefa via JSON."""
    dados = request.get_json(silent=True) or {}
    titulo = (dados.get('titulo') or '').strip()
    descricao = (dados.get('descricao') or '').strip()
    if not titulo:
        return jsonify({'sucesso': False, 'mensagem': 'O título é obrigatório.'}), 400
    conn = get_db()
    cursor = conn.execute(
        'INSERT INTO tarefas (titulo, descricao, usuario_id) VALUES (?, ?, ?)',
        (titulo, descricao, session['usuario_id'])
    )
    conn.commit()
    tarefa = conn.execute('SELECT * FROM tarefas WHERE id = ?', (cursor.lastrowid,)).fetchone()
    conn.close()
    return jsonify({'sucesso': True, 'tarefa': dict(tarefa)}), 201

@app.route('/api/tarefas/<int:id>', methods=['PUT'])
@login_required
def api_atualizar_tarefa(id):
    """Atualiza título, descrição e/ou status via JSON."""
    dados = request.get_json(silent=True) or {}
    conn = get_db()
    tarefa = conn.execute(
        'SELECT * FROM tarefas WHERE id = ? AND usuario_id = ?',
        (id, session['usuario_id'])
    ).fetchone()
    if not tarefa:
        conn.close()
        return jsonify({'sucesso': False, 'mensagem': 'Tarefa não encontrada.'}), 404

    titulo = (dados.get('titulo') or tarefa['titulo']).strip()
    descricao = (dados.get('descricao') if dados.get('descricao') is not None else tarefa['descricao'] or '').strip()
    status = dados.get('status') or tarefa['status']

    if status not in ('pendente', 'em_andamento', 'concluida'):
        conn.close()
        return jsonify({'sucesso': False, 'mensagem': 'Status inválido.'}), 400

    conn.execute(
        'UPDATE tarefas SET titulo=?, descricao=?, status=? WHERE id=?',
        (titulo, descricao, status, id)
    )
    conn.commit()
    tarefa = conn.execute('SELECT * FROM tarefas WHERE id = ?', (id,)).fetchone()
    conn.close()
    return jsonify({'sucesso': True, 'tarefa': dict(tarefa)})

@app.route('/api/tarefas/<int:id>', methods=['DELETE'])
@login_required
def api_deletar_tarefa(id):
    """Remove uma tarefa via JSON."""
    conn = get_db()
    tarefa = conn.execute(
        'SELECT id FROM tarefas WHERE id = ? AND usuario_id = ?',
        (id, session['usuario_id'])
    ).fetchone()
    if not tarefa:
        conn.close()
        return jsonify({'sucesso': False, 'mensagem': 'Tarefa não encontrada.'}), 404
    conn.execute('DELETE FROM tarefas WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return jsonify({'sucesso': True, 'mensagem': 'Tarefa removida com sucesso.'})

# ─── API REST — Progresso (item 10, Chart.js) ─────────────────────────────────

@app.route('/api/progresso', methods=['GET'])
@login_required
def api_progresso():
    """Retorna contagem de tarefas por status para o gráfico."""
    conn = get_db()
    rows = conn.execute(
        """SELECT status, COUNT(*) as total
           FROM tarefas WHERE usuario_id = ?
           GROUP BY status""",
        (session['usuario_id'],)
    ).fetchall()
    conn.close()

    dados = {'pendente': 0, 'em_andamento': 0, 'concluida': 0}
    for row in rows:
        if row['status'] in dados:
            dados[row['status']] = row['total']
    return jsonify(dados)

# ─── Página de Progresso — Dashboard Visual (item 10) ────────────────────────

@app.route('/progresso')
@login_required
def progresso():
    """Página com gráficos de progresso das tarefas."""
    conn = get_db()
    tarefas = conn.execute(
        'SELECT * FROM tarefas WHERE usuario_id = ?',
        (session['usuario_id'],)
    ).fetchall()
    conn.close()

    total = len(tarefas)
    pendentes = sum(1 for t in tarefas if t['status'] == 'pendente')
    em_andamento = sum(1 for t in tarefas if t['status'] == 'em_andamento')
    concluidas = sum(1 for t in tarefas if t['status'] == 'concluida')
    pct = round((concluidas / total * 100) if total > 0 else 0)

    return render_template('progresso.html',
                           total=total,
                           pendentes=pendentes,
                           em_andamento=em_andamento,
                           concluidas=concluidas,
                           pct=pct)

# ─── Inicialização ────────────────────────────────────────────────────────────

if __name__ == '__main__':
    init_db()
    app.run(debug=True)

# ─── Segurança (item 7) ───────────────────────────────────────────────────────
# SECRET_KEY já configurada. DEBUG=False em produção via variável de ambiente.
# Uso: FLASK_DEBUG=0 python app.py

