/* ==========================================================================
   TaskPanel — main.js
   Módulos independentes, cada um inicializado só se seus nós existirem.
   Nenhum contrato de API foi alterado: as mesmas rotas, os mesmos payloads.
   ========================================================================== */
(function () {
    'use strict';

    var html = document.documentElement;
    var STATUS = ['pendente', 'em_andamento', 'concluida'];
    var $ = function (sel, ctx) { return (ctx || document).querySelector(sel); };
    var $$ = function (sel, ctx) { return Array.prototype.slice.call((ctx || document).querySelectorAll(sel)); };

    var guardar = function (chave, valor) {
        try { localStorage.setItem(chave, valor); } catch (e) { /* modo privado */ }
    };

    /* ─── Toasts ─────────────────────────────────────────────────────── */
    var Toasts = (function () {
        var box = $('#toasts');
        var ICONES = { success: 'check-circle', danger: 'x-circle', warning: 'alert', info: 'info' };

        function dispensar(el) {
            if (!el || el.dataset.leaving) return;
            el.dataset.leaving = 'true';
            setTimeout(function () { el.remove(); }, 220);
        }

        function agendar(el) {
            var t = setTimeout(function () { dispensar(el); }, 5000);
            el.addEventListener('mouseenter', function () { clearTimeout(t); });
            var fechar = $('.toast__close', el);
            if (fechar) fechar.addEventListener('click', function () { dispensar(el); });
        }

        function criar(mensagem, tipo) {
            if (!box) return;
            var el = document.createElement('div');
            el.className = 'toast toast--' + (tipo || 'info');
            el.innerHTML =
                '<svg class="icon" aria-hidden="true"><use href="#i-' + (ICONES[tipo] || 'info') + '"></use></svg>' +
                '<span class="toast__msg"></span>' +
                '<button type="button" class="toast__close" aria-label="Dispensar">' +
                '<svg class="icon" aria-hidden="true"><use href="#i-x"></use></svg></button>';
            $('.toast__msg', el).textContent = mensagem;
            box.appendChild(el);
            agendar(el);
        }

        if (box) $$('.toast', box).forEach(agendar);
        return { criar: criar };
    })();

    /* ─── Tema ───────────────────────────────────────────────────────── */
    function alternarTema() {
        var novo = html.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
        html.setAttribute('data-theme', novo);
        guardar('tp-tema', novo);
        document.dispatchEvent(new CustomEvent('tp:theme', { detail: { tema: novo } }));
    }
    var btnTema = $('#btn-tema');
    if (btnTema) btnTema.addEventListener('click', alternarTema);
    window.alternarTema = alternarTema; // compatibilidade com chamadas antigas

    /* ─── Sidebar: colapso (desktop) e gaveta (mobile) ───────────────── */
    (function () {
        var btnColapsar = $('#btn-colapsar');
        var btnGaveta = $('#btn-gaveta');
        var scrim = $('#scrim');

        if (btnColapsar) {
            var sincronizar = function () {
                var fechada = html.getAttribute('data-sidebar') === 'collapsed';
                btnColapsar.setAttribute('aria-expanded', String(!fechada));
                btnColapsar.setAttribute('aria-label', fechada ? 'Expandir menu' : 'Recolher menu');
            };
            sincronizar();
            btnColapsar.addEventListener('click', function () {
                var fechada = html.getAttribute('data-sidebar') === 'collapsed';
                html.setAttribute('data-sidebar', fechada ? 'expanded' : 'collapsed');
                guardar('tp-sidebar', fechada ? 'expanded' : 'collapsed');
                sincronizar();
            });
        }

        function fecharGaveta() {
            html.removeAttribute('data-drawer');
            if (btnGaveta) {
                btnGaveta.setAttribute('aria-expanded', 'false');
                btnGaveta.focus();
            }
        }

        if (btnGaveta) {
            btnGaveta.addEventListener('click', function () {
                html.setAttribute('data-drawer', 'open');
                btnGaveta.setAttribute('aria-expanded', 'true');
                var primeiro = $('.nav__link');
                if (primeiro) primeiro.focus();
            });
        }
        if (scrim) scrim.addEventListener('click', fecharGaveta);
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' && html.getAttribute('data-drawer') === 'open') fecharGaveta();
        });
    })();

    /* ─── Botões: iluminação no hover e estado de carregamento ───────── */
    $$('.btn').forEach(function (btn) {
        btn.addEventListener('pointermove', function (e) {
            var r = btn.getBoundingClientRect();
            btn.style.setProperty('--mx', (e.clientX - r.left) + 'px');
            btn.style.setProperty('--my', (e.clientY - r.top) + 'px');
        }, { passive: true });
    });

    $$('form').forEach(function (form) {
        form.addEventListener('submit', function () {
            if (!form.checkValidity()) return;
            var btn = $('[data-submit]', form);
            if (btn) btn.dataset.loading = 'true';
        });
    });

    /* ─── Confirmação de exclusão ────────────────────────────────────── */
    (function () {
        var dlg = $('#dialogo-confirmar');
        if (!dlg || typeof dlg.showModal !== 'function') return;

        var alvo = $('[data-dlg-alvo]', dlg);
        var confirmar = $('[data-dlg-confirmar]', dlg);
        var cancelar = $('[data-dlg-cancelar]', dlg);

        document.addEventListener('click', function (e) {
            var link = e.target.closest ? e.target.closest('a[data-confirm]') : null;
            if (!link) return;
            e.preventDefault();
            alvo.textContent = link.dataset.confirm;
            confirmar.href = link.href;
            dlg.showModal();
        });

        cancelar.addEventListener('click', function () { dlg.close(); });
        confirmar.addEventListener('click', function () { confirmar.dataset.loading = 'true'; });
    })();

    /* ─── Atalhos de teclado ─────────────────────────────────────────── */
    document.addEventListener('keydown', function (e) {
        if (e.metaKey || e.ctrlKey || e.altKey) return;
        var alvo = e.target;
        if (alvo.matches && alvo.matches('input, textarea, select, [contenteditable]')) return;
        if (document.querySelector('dialog[open]')) return;

        if (e.key === '/') {
            var busca = $('#campo-busca');
            if (busca) { e.preventDefault(); busca.focus(); busca.select(); }
        } else if (e.key === 'n') {
            var nova = $('.nav__link[href*="nova"]');
            if (nova) { e.preventDefault(); window.location.href = nova.href; }
        }
    });

    /* ═══ Dashboard ═══════════════════════════════════════════════════ */
    var grid = document.getElementById('tarefas-grid');
    if (!grid) return;

    var tarefas = $$('.task', grid);
    var campoBusca = $('#campo-busca');
    var chips = $$('#filtros .chip');
    var vazio = $('#vazio-busca');
    var colecao = $('#tarefas');

    /* Sinônimos para que a busca por texto também encontre o status. */
    var TERMOS = {
        pendente: 'pendente pendentes',
        em_andamento: 'em andamento andamento fazendo',
        concluida: 'concluida concluída concluido concluído feito pronto'
    };

    function filtroAtivo() {
        var chip = chips.filter(function (c) { return c.getAttribute('aria-pressed') === 'true'; })[0];
        return chip ? chip.dataset.filtro : 'todos';
    }

    function aplicarFiltros() {
        var termo = campoBusca ? campoBusca.value.trim().toLowerCase() : '';
        var status = filtroAtivo();
        var visiveis = 0;

        tarefas.forEach(function (card) {
            var st = card.dataset.status;
            var texto = card.dataset.titulo + ' ' + card.dataset.desc + ' ' + (TERMOS[st] || '');
            var casaTexto = !termo || texto.indexOf(termo) !== -1;
            var casaStatus = status === 'todos' || st === status;
            var mostrar = casaTexto && casaStatus;

            card.hidden = !mostrar;
            /* Zebra só conta linhas visíveis — senão o padrão quebra ao filtrar. */
            card.classList.toggle('task--par', mostrar && visiveis % 2 === 1);
            if (mostrar) visiveis++;
        });

        if (vazio) vazio.hidden = visiveis > 0;
        if (colecao) colecao.hidden = visiveis === 0;
    }

    if (campoBusca) campoBusca.addEventListener('input', aplicarFiltros);

    chips.forEach(function (chip) {
        chip.addEventListener('click', function () {
            chips.forEach(function (c) { c.setAttribute('aria-pressed', 'false'); });
            chip.setAttribute('aria-pressed', 'true');
            aplicarFiltros();
        });
    });

    var limpar = $('#limpar-busca');
    if (limpar) {
        limpar.addEventListener('click', function () {
            if (campoBusca) campoBusca.value = '';
            chips.forEach(function (c, i) { c.setAttribute('aria-pressed', i === 0 ? 'true' : 'false'); });
            aplicarFiltros();
            if (campoBusca) campoBusca.focus();
        });
    }

    /* ─── Troca de visão (cartões ⇄ lista) ───────────────────────────── */
    (function () {
        var botoes = $$('#troca-visao .segmented__btn');
        if (!botoes.length || !colecao) return;

        function definir(visao, persistir) {
            colecao.dataset.view = visao;
            botoes.forEach(function (b) {
                b.setAttribute('aria-pressed', String(b.dataset.visao === visao));
            });
            if (persistir) guardar('tp-visao', visao);
        }

        var salva;
        try { salva = localStorage.getItem('tp-visao'); } catch (e) { salva = null; }
        if (salva === 'lista' || salva === 'cards') definir(salva, false);

        botoes.forEach(function (b) {
            b.addEventListener('click', function () { definir(b.dataset.visao, true); });
        });
    })();

    /* ─── Contadores, sem recarregar a página ────────────────────────── */
    function atualizarContadores() {
        var contagem = { pendente: 0, em_andamento: 0, concluida: 0 };
        tarefas.forEach(function (c) { contagem[c.dataset.status]++; });

        var mapa = {
            'stat-total': tarefas.length,
            'stat-pendente': contagem.pendente,
            'stat-andamento': contagem.em_andamento,
            'stat-concluida': contagem.concluida
        };
        Object.keys(mapa).forEach(function (id) {
            var el = document.getElementById(id);
            if (el) el.textContent = mapa[id];
        });
    }

    /* ═══ ASSINATURA — Status Switch ══════════════════════════════════
       Atualiza a interface na hora (otimista) e desfaz se o servidor
       recusar. O usuário nunca espera o round-trip para ver o resultado.
       ================================================================ */
    function pintar(card, sw, status) {
        card.dataset.status = status;
        sw.style.setProperty('--slot', STATUS.indexOf(status));
        $$('.status-switch__opt', sw).forEach(function (opt) {
            var ativo = opt.dataset.value === status;
            opt.setAttribute('aria-checked', String(ativo));
            opt.tabIndex = ativo ? 0 : -1;
        });
    }

    function salvarStatus(card, sw, novo) {
        var anterior = card.dataset.status;
        if (anterior === novo) return;

        pintar(card, sw, novo);
        atualizarContadores();
        sw.dataset.busy = 'true';

        fetch('/tarefas/status/' + sw.dataset.id, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: novo })
        })
            .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, dados: d }; }); })
            .then(function (res) {
                delete sw.dataset.busy;
                if (!res.ok || !res.dados.sucesso) throw new Error(res.dados.mensagem || 'Falha ao atualizar.');

                var ack = $('.task__ack', card);
                if (ack) {
                    ack.hidden = false;
                    setTimeout(function () { ack.hidden = true; }, 1200);
                }
                aplicarFiltros();
            })
            .catch(function (erro) {
                delete sw.dataset.busy;
                pintar(card, sw, anterior);
                atualizarContadores();
                Toasts.criar(erro.message === 'Failed to fetch'
                    ? 'Sem conexão com o servidor. O status não foi alterado.'
                    : erro.message, 'danger');
            });
    }

    $$('.status-switch', grid).forEach(function (sw) {
        var card = sw.closest('.task');
        var opcoes = $$('.status-switch__opt', sw);

        opcoes.forEach(function (opt, i) {
            opt.addEventListener('click', function () { salvarStatus(card, sw, opt.dataset.value); });

            /* Radiogroup navegável por setas, como manda o padrão ARIA. */
            opt.addEventListener('keydown', function (e) {
                var passo = e.key === 'ArrowRight' || e.key === 'ArrowDown' ? 1
                    : e.key === 'ArrowLeft' || e.key === 'ArrowUp' ? -1 : 0;
                if (!passo) return;
                e.preventDefault();
                var alvo = opcoes[(i + passo + opcoes.length) % opcoes.length];
                alvo.focus();
                salvarStatus(card, sw, alvo.dataset.value);
            });
        });
    });

    aplicarFiltros();
})();
