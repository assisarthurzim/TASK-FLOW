from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import psycopg2
import psycopg2.extras
import os
import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'chave_secreta_flask_2024')

# --- Banco de Dados (PostgreSQL) ---

DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id SERIAL PRIMARY KEY,
            nome TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS tarefas (
            id SERIAL PRIMARY KEY,
            titulo TEXT NOT NULL,
            descricao TEXT,
            status TEXT DEFAULT 'pendente',
            usuario_id INTEGER NOT NULL REFERENCES usuarios(id)
        )
    ''')
    conn.commit()
    cur.close()
    conn.close()

# --- Decorador de Autenticacao ---

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'usuario_id' not in session:
            flash('Faca login para acessar esta pagina.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

# --- Dica do Dia (sistema interno, 100% em portugues) ---

FRASES_DO_DIA = [
    "A jornada de mil quilometros comeca com um unico passo.",
    "O sucesso e a soma de pequenos esforcos repetidos dia apos dia.",
    "Nao espere por uma crise para descobrir o que e importante na sua vida.",
    "A disciplina e a ponte entre metas e realizacoes.",
    "Cada tarefa concluida e um passo mais perto do seu objetivo.",
    "Organizacao nao e um talento, e um habito que se constroi.",
    "Faca hoje o que outros nao querem fazer; amanha voce tera o que outros nao tem.",
    "O foco de hoje constroi a vitoria de amanha.",
    "Produtividade e fazer escolhas inteligentes sobre onde investir seu tempo.",
    "Pequenos progressos diarios levam a grandes resultados.",
    "Comece onde voce esta, use o que voce tem, faca o que voce pode.",
    "A persistencia realiza o impossivel.",
    "Planejar e trazer o futuro para o presente, para que voce possa agir agora.",
    "Quem tem um proposito forte suporta quase qualquer metodo.",
    "Grandes conquistas exigem tempo, paciencia e organizacao.",
    "Voce nao precisa ser perfeito, so precisa ser consistente.",
    "A clareza sobre o que fazer hoje nasce de um bom planejamento.",
    "Cada passo pequeno conta quando voce esta construindo algo grande.",
    "Termine o que comecou: a sensacao de dever cumprido nao tem preco.",
    "O segredo de progredir e comecar.",
]

DICA_PADRAO = "Continue firme: cada tarefa concluida e uma vitoria conquistada."

def obter_dica_do_dia():
    """Retorna a frase motivacional do dia, sempre a mesma durante 24h."""
    try:
        indice = datetime.date.today().toordinal() % len(FRASES_DO_DIA)
        return FRASES_DO_DIA[indice]
    except Exception:
        return DICA_PADRAO

# --- Rotas de Autenticacao ---

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
        conn = get_db()
        cur = conn.cursor()
        try:
            cur.execute('INSERT INTO usuarios (nome, email, senha) VALUES (%s, %s, %s)',
                        (nome, email, senha))
            conn.commit()
            flash('Conta criada com sucesso! Faca login para continuar.', 'success')
            return redirect(url_for('login'))
        except psycopg2.IntegrityError:
            conn.rollback()
            flash('Este e-mail ja esta cadastrado.', 'danger')
        finally:
            cur.close()
            conn.close()
    return render_template('registro.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        senha = request.form['senha']
        conn = get_db()
        cur = conn.cursor()
        cur.execute('SELECT * FROM usuarios WHERE email = %s', (email,))
        usuario = cur.fetchone()
        cur.close()
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
    flash('Voce saiu com sucesso.', 'info')
    return redirect(url_for('login'))

# --- Dashboard ---

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        'SELECT * FROM tarefas WHERE usuario_id = %s ORDER BY id DESC',
        (session['usuario_id'],)
    )
    tarefas = cur.fetchall()
    cur.close()
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

# --- Atualizacao de status via AJAX ---

@app.route('/tarefas/status/<int:id>', methods=['POST'])
@login_required
def atualizar_status(id):
    dados = request.get_json(silent=True) or {}
    novo_status = dados.get('status')
    status_validos = ('pendente', 'em_andamento', 'concluida')

    if novo_status not in status_validos:
        return jsonify({'sucesso': False, 'mensagem': 'Status invalido.'}), 400

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        'SELECT id FROM tarefas WHERE id = %s AND usuario_id = %s',
        (id, session['usuario_id'])
    )
    tarefa = cur.fetchone()

    if not tarefa:
        cur.close()
        conn.close()
        return jsonify({'sucesso': False, 'mensagem': 'Tarefa nao encontrada.'}), 404

    cur.execute(
        'UPDATE tarefas SET status = %s WHERE id = %s AND usuario_id = %s',
        (novo_status, id, session['usuario_id'])
    )
    conn.commit()
    cur.close()
    conn.close()

    return jsonify({'sucesso': True, 'status': novo_status, 'mensagem': 'Status atualizado!'})

# --- CRUD de Tarefas ---

@app.route('/tarefas/nova', methods=['GET', 'POST'])
@login_required
def nova_tarefa():
    if request.method == 'POST':
        titulo = request.form['titulo'].strip()
        descricao = request.form['descricao'].strip()
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            'INSERT INTO tarefas (titulo, descricao, usuario_id) VALUES (%s, %s, %s)',
            (titulo, descricao, session['usuario_id'])
        )
        conn.commit()
        cur.close()
        conn.close()
        flash('Tarefa criada com sucesso!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('nova_tarefa.html')

@app.route('/tarefas/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_tarefa(id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        'SELECT * FROM tarefas WHERE id = %s AND usuario_id = %s',
        (id, session['usuario_id'])
    )
    tarefa = cur.fetchone()
    if not tarefa:
        cur.close()
        conn.close()
        flash('Tarefa nao encontrada.', 'danger')
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        titulo = request.form['titulo'].strip()
        descricao = request.form['descricao'].strip()
        status = request.form['status']
        cur.execute(
            'UPDATE tarefas SET titulo=%s, descricao=%s, status=%s WHERE id=%s',
            (titulo, descricao, status, id)
        )
        conn.commit()
        cur.close()
        conn.close()
        flash('Tarefa atualizada com sucesso!', 'success')
        return redirect(url_for('dashboard'))
    cur.close()
    conn.close()
    return render_template('editar_tarefa.html', tarefa=tarefa)

@app.route('/tarefas/deletar/<int:id>')
@login_required
def deletar_tarefa(id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        'DELETE FROM tarefas WHERE id = %s AND usuario_id = %s',
        (id, session['usuario_id'])
    )
    conn.commit()
    cur.close()
    conn.close()
    flash('Tarefa removida com sucesso.', 'info')
    return redirect(url_for('dashboard'))

# --- API REST - Tarefas em JSON ---

@app.route('/api/tarefas', methods=['GET'])
@login_required
def api_listar_tarefas():
    """Retorna todas as tarefas do usuario logado em JSON."""
    status_filtro = request.args.get('status')
    conn = get_db()
    cur = conn.cursor()
    if status_filtro and status_filtro in ('pendente', 'em_andamento', 'concluida'):
        cur.execute(
            'SELECT * FROM tarefas WHERE usuario_id = %s AND status = %s ORDER BY id DESC',
            (session['usuario_id'], status_filtro)
        )
    else:
        cur.execute(
            'SELECT * FROM tarefas WHERE usuario_id = %s ORDER BY id DESC',
            (session['usuario_id'],)
        )
    tarefas = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([dict(t) for t in tarefas])

@app.route('/api/tarefas/<int:id>', methods=['GET'])
@login_required
def api_obter_tarefa(id):
    """Retorna uma tarefa especifica em JSON."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        'SELECT * FROM tarefas WHERE id = %s AND usuario_id = %s',
        (id, session['usuario_id'])
    )
    tarefa = cur.fetchone()
    cur.close()
    conn.close()
    if not tarefa:
        return jsonify({'erro': 'Tarefa nao encontrada.'}), 404
    return jsonify(dict(tarefa))

@app.route('/api/tarefas', methods=['POST'])
@login_required
def api_criar_tarefa():
    """Cria uma nova tarefa via JSON."""
    dados = request.get_json(silent=True) or {}
    titulo = (dados.get('titulo') or '').strip()
    descricao = (dados.get('descricao') or '').strip()
    if not titulo:
        return jsonify({'sucesso': False, 'mensagem': 'O titulo e obrigatorio.'}), 400
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        'INSERT INTO tarefas (titulo, descricao, usuario_id) VALUES (%s, %s, %s) RETURNING id',
        (titulo, descricao, session['usuario_id'])
    )
    novo_id = cur.fetchone()['id']
    conn.commit()
    cur.execute('SELECT * FROM tarefas WHERE id = %s', (novo_id,))
    tarefa = cur.fetchone()
    cur.close()
    conn.close()
    return jsonify({'sucesso': True, 'tarefa': dict(tarefa)}), 201

@app.route('/api/tarefas/<int:id>', methods=['PUT'])
@login_required
def api_atualizar_tarefa(id):
    """Atualiza titulo, descricao e/ou status via JSON."""
    dados = request.get_json(silent=True) or {}
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        'SELECT * FROM tarefas WHERE id = %s AND usuario_id = %s',
        (id, session['usuario_id'])
    )
    tarefa = cur.fetchone()
    if not tarefa:
        cur.close()
        conn.close()
        return jsonify({'sucesso': False, 'mensagem': 'Tarefa nao encontrada.'}), 404

    titulo = (dados.get('titulo') or tarefa['titulo']).strip()
    descricao = (dados.get('descricao') if dados.get('descricao') is not None else tarefa['descricao'] or '').strip()
    status = dados.get('status') or tarefa['status']

    if status not in ('pendente', 'em_andamento', 'concluida'):
        cur.close()
        conn.close()
        return jsonify({'sucesso': False, 'mensagem': 'Status invalido.'}), 400

    cur.execute(
        'UPDATE tarefas SET titulo=%s, descricao=%s, status=%s WHERE id=%s',
        (titulo, descricao, status, id)
    )
    conn.commit()
    cur.execute('SELECT * FROM tarefas WHERE id = %s', (id,))
    tarefa = cur.fetchone()
    cur.close()
    conn.close()
    return jsonify({'sucesso': True, 'tarefa': dict(tarefa)})

@app.route('/api/tarefas/<int:id>', methods=['DELETE'])
@login_required
def api_deletar_tarefa(id):
    """Remove uma tarefa via JSON."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        'SELECT id FROM tarefas WHERE id = %s AND usuario_id = %s',
        (id, session['usuario_id'])
    )
    tarefa = cur.fetchone()
    if not tarefa:
        cur.close()
        conn.close()
        return jsonify({'sucesso': False, 'mensagem': 'Tarefa nao encontrada.'}), 404
    cur.execute('DELETE FROM tarefas WHERE id = %s', (id,))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({'sucesso': True, 'mensagem': 'Tarefa removida com sucesso.'})

# --- API REST - Progresso (Chart.js) ---

@app.route('/api/progresso', methods=['GET'])
@login_required
def api_progresso():
    """Retorna contagem de tarefas por status para o grafico."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """SELECT status, COUNT(*) as total
           FROM tarefas WHERE usuario_id = %s
           GROUP BY status""",
        (session['usuario_id'],)
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    dados = {'pendente': 0, 'em_andamento': 0, 'concluida': 0}
    for row in rows:
        if row['status'] in dados:
            dados[row['status']] = row['total']
    return jsonify(dados)

# --- Pagina de Progresso - Dashboard Visual ---

@app.route('/progresso')
@login_required
def progresso():
    """Pagina com graficos de progresso das tarefas."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        'SELECT * FROM tarefas WHERE usuario_id = %s',
        (session['usuario_id'],)
    )
    tarefas = cur.fetchall()
    cur.close()
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

# --- Inicializacao ---

if __name__ == '__main__':
    init_db()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
else:
    init_db()
