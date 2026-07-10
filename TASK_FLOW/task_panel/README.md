# TaskPanel — Painel de Controle de Tarefas com Flask

Aplicação Flask + SQLite para gerenciamento de tarefas, com front-end próprio
(sem frameworks de UI), tema claro/escuro e interações sem recarregar a página.

## Estrutura do Projeto

```
task_panel/
├── app.py                       # Aplicação Flask (rotas, banco, API) — inalterada
├── database.db                  # Gerado automaticamente na primeira execução
├── requirements.txt             # Dependências
├── templates/
│   ├── base.html                # Shell da aplicação (app e autenticação)
│   ├── macros.html              # Componentes server-side (campo, stat, card, switch)
│   ├── partials/
│   │   ├── icons.html           # Sprite SVG (substitui o webfont de ícones)
│   │   ├── sidebar.html         # Navegação lateral colapsável
│   │   ├── topbar.html          # Barra superior
│   │   └── theme_toggle.html    # Alternador de tema
│   ├── login.html
│   ├── registro.html
│   ├── dashboard.html
│   ├── nova_tarefa.html
│   ├── editar_tarefa.html
│   └── progresso.html
└── static/
    ├── css/
    │   ├── tokens.css           # Fonte única de verdade: cores, tipo, espaço, temas
    │   ├── base.css             # Reset, tipografia, foco, utilitários, animações
    │   ├── components.css       # Biblioteca de componentes
    │   ├── layout.css           # Shell, sidebar, topbar, layout de autenticação
    │   └── pages.css            # Composições específicas de cada página
    └── js/
        ├── main.js              # Tema, sidebar, busca, filtros, status AJAX, toasts
        └── charts.js            # Gráficos da página de progresso
```

## Recursos

1. **Gerenciamento de rotas e templates** — Flask + Jinja2
2. **Banco de dados SQLite** — tabelas `usuarios` e `tarefas`
3. **Autenticação** — registro, login, logout com sessão Flask
4. **CRUD completo de tarefas** — criar, listar, editar, excluir
5. **API REST** — `/api/tarefas` (GET/POST/PUT/DELETE) e `/api/progresso`
6. **Página de progresso** — barra geral + gráficos (Chart.js)
7. **Interface própria** — design system em CSS puro, tema claro/escuro persistido,
   busca e filtros instantâneos, mudança de status via AJAX, toasts e atalhos de teclado

## Como executar

```bash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Executar o servidor
python app.py

# 3. Abrir no navegador
http://127.0.0.1:5000
```

> O tema escuro é o padrão. O botão no topo alterna para o claro, e a escolha
> fica salva no navegador. Atalhos: `/` foca a busca, `n` cria uma nova tarefa.

## Banco de dados

As tabelas são criadas automaticamente na primeira execução:

- **usuarios**: id, nome, email, senha (hash)
- **tarefas**: id, titulo, descricao, status, usuario_id (FK)

Status possíveis: `pendente`, `em_andamento`, `concluida`.

## Dependências externas

Carregadas por CDN, apenas no front-end:

- Google Fonts — Space Grotesk, Inter, JetBrains Mono
- Chart.js 4 — somente na página de progresso (a página degrada bem sem ele)
