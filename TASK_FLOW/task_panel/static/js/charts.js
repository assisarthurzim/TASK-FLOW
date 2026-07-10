/* ==========================================================================
   TaskPanel — charts.js
   Gráficos da página de progresso. Lê as cores dos tokens CSS, então o
   gráfico segue o tema (inclusive quando o usuário troca em tempo real).
   ========================================================================== */
(function () {
    'use strict';

    var no = document.getElementById('dados-progresso');
    if (!no) return;

    var dados;
    try { dados = JSON.parse(no.textContent); } catch (e) { return; }

    var corpos = Array.prototype.slice.call(document.querySelectorAll('.chart-card__body'));

    /* Sem Chart.js (offline, bloqueio de CDN): retira o skeleton e avisa. */
    if (typeof window.Chart === 'undefined') {
        corpos.forEach(function (el) {
            el.removeAttribute('data-loading');
            el.innerHTML = '<p class="chart-fallback">Não foi possível carregar os gráficos agora.</p>';
        });
        return;
    }

    var token = function (nome) {
        return getComputedStyle(document.documentElement).getPropertyValue(nome).trim();
    };

    function paleta() {
        return {
            cores: [token('--idle'), token('--active'), token('--done')],
            texto: token('--text-2'),
            grade: token('--border'),
            fundo: token('--surface')
        };
    }

    var rotulos = ['Pendente', 'Em andamento', 'Concluída'];
    var valores = [dados.pendente, dados.em_andamento, dados.concluida];
    var reduzirMovimento = matchMedia('(prefers-reduced-motion: reduce)').matches;

    Chart.defaults.font.family = "'Inter', system-ui, sans-serif";
    Chart.defaults.font.size = 12;
    Chart.defaults.animation = reduzirMovimento ? false : { duration: 600, easing: 'easeOutQuart' };

    var graficos = [];

    var pizza = document.getElementById('grafico-pizza');
    if (pizza) {
        var p = paleta();
        graficos.push(new Chart(pizza, {
            type: 'doughnut',
            data: {
                labels: rotulos,
                datasets: [{
                    data: valores,
                    backgroundColor: p.cores,
                    borderColor: p.fundo,
                    borderWidth: 3,
                    hoverOffset: 10
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '64%',
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { color: p.texto, padding: 16, usePointStyle: true, pointStyle: 'circle' }
                    },
                    tooltip: {
                        callbacks: {
                            label: function (ctx) {
                                var total = ctx.dataset.data.reduce(function (a, b) { return a + b; }, 0);
                                var pct = total ? Math.round((ctx.parsed / total) * 100) : 0;
                                return ' ' + ctx.label + ': ' + ctx.parsed + ' (' + pct + '%)';
                            }
                        }
                    }
                }
            }
        }));
    }

    var barras = document.getElementById('grafico-barras');
    if (barras) {
        var b = paleta();
        graficos.push(new Chart(barras, {
            type: 'bar',
            data: {
                labels: rotulos,
                datasets: [{
                    label: 'Tarefas',
                    data: valores,
                    backgroundColor: b.cores,
                    borderRadius: 8,
                    borderSkipped: false,
                    maxBarThickness: 72
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: { label: function (ctx) { return ' ' + ctx.parsed.y + ' tarefa(s)'; } }
                    }
                },
                scales: {
                    x: { ticks: { color: b.texto }, grid: { display: false }, border: { color: b.grade } },
                    y: {
                        beginAtZero: true,
                        ticks: { color: b.texto, stepSize: 1, precision: 0 },
                        grid: { color: b.grade },
                        border: { display: false }
                    }
                }
            }
        }));
    }

    corpos.forEach(function (el) { el.removeAttribute('data-loading'); });

    /* Troca de tema: repinta sem recriar os gráficos. */
    document.addEventListener('tp:theme', function () {
        var c = paleta();
        graficos.forEach(function (g) {
            g.data.datasets[0].backgroundColor = c.cores;
            if (g.config.type === 'doughnut') {
                g.data.datasets[0].borderColor = c.fundo;
                g.options.plugins.legend.labels.color = c.texto;
            } else {
                g.options.scales.x.ticks.color = c.texto;
                g.options.scales.y.ticks.color = c.texto;
                g.options.scales.y.grid.color = c.grade;
                g.options.scales.x.border.color = c.grade;
            }
            g.update('none');
        });
    });
})();
