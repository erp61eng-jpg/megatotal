import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from itertools import combinations
from collections import Counter
import math
import time
import re

st.set_page_config(
    page_title="MEGA60 - Cartela de Calor Elliott & Filtros",
    page_icon="🔥",
    layout="wide"
)

# ==============================================================================
# PROPRIEDADES MATRICIAIS E FIBONACCI
# ==============================================================================
FIBONACCI_MEGASENA = {1, 2, 3, 5, 8, 13, 21, 34, 55}
PRIMOS_MEGASENA = {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59}
MOLDURA_SET = (
    set(range(1, 11)) | 
    set(range(51, 61)) | 
    {r * 10 + 1 for r in range(6)} | 
    {r * 10 + 10 for r in range(6)}
)

PROPS = {}
for n in range(1, 61):
    r = (n - 1) // 10
    c = (n - 1) % 10
    PROPS[n] = {
        "r": r,
        "c": c,
        "dc": (c + r) % 10,
        "dd": (c - r) % 10,
        "is_primo": n in PRIMOS_MEGASENA,
        "is_par": n % 2 == 0,
        "is_moldura": n in MOLDURA_SET,
        "is_fib": n in FIBONACCI_MEGASENA
    }

OPCOES_QTD = {
    "Livre (0 a 6)": (0, 6),
    "0 (Nenhuma)": (0, 0),
    "Exatamente 1": (1, 1),
    "Exatamente 2": (2, 2),
    "0 ou 1": (0, 1),
    "1 ou 2": (1, 2),
    "0 a 2": (0, 2),
    "1 a 3": (1, 3)
}

HISTORICO_BASE = [
    [4, 12, 18, 30, 35, 54], [1, 9, 15, 23, 44, 52], [7, 14, 27, 39, 48, 59],
    [10, 11, 25, 33, 42, 58], [3, 16, 28, 37, 45, 60], [5, 20, 22, 34, 49, 56],
    [8, 17, 31, 40, 50, 57], [2, 13, 24, 38, 43, 55], [6, 19, 29, 36, 47, 53],
    [12, 21, 32, 41, 46, 51], [4, 15, 26, 35, 48, 58], [7, 18, 23, 39, 44, 59],
    [1, 10, 27, 34, 42, 54], [9, 14, 30, 37, 50, 60], [3, 16, 25, 38, 49, 57],
    [5, 11, 28, 33, 45, 53], [8, 20, 31, 43, 52, 56], [2, 17, 24, 36, 47, 55],
    [6, 13, 29, 40, 46, 51], [12, 19, 32, 41, 50, 58]
]

# ==============================================================================
# MOTOR TÉRMICO DE ELLIOTT (IMPULSO, RETRAÇÃO & MOMENTUM)
# ==============================================================================
def processar_metricas_elliott(historico):
    total = len(historico)
    atrasos = {n: total for n in range(1, 61)}
    freq_5 = {n: 0 for n in range(1, 61)}
    freq_15 = {n: 0 for n in range(1, 61)}

    for idx_rev, sorteio in enumerate(reversed(historico)):
        for n in sorteio:
            if atrasos[n] == total:
                atrasos[n] = idx_rev
            if idx_rev < 5:
                freq_5[n] += 1
            if idx_rev < 15:
                freq_15[n] += 1

    dados = {}
    for n in range(1, 61):
        atr = atrasos[n]
        dist_fib = min(abs(atr - f) for f in [1, 2, 3, 5, 8, 13, 21])
        score_retracao = max(0.0, 10.0 - (dist_fib * 2.2))
        score_impulso = (freq_5[n] * 6.5) + (freq_15[n] * 2.5)
        score_fib = 3.5 if PROPS[n]["is_fib"] else 0.0
        penalidade = -4.0 if atr > 21 else 0.0

        score_total = max(0.0, score_retracao + score_impulso + score_fib + penalidade)
        dados[n] = {
            "numero": n,
            "score": round(score_total, 1),
            "atraso": atr,
            "impulso": freq_5[n],
            "is_fib": PROPS[n]["is_fib"]
        }

    return dados

# ==============================================================================
# MOTOR DE FILTRAGEM MATRICIAL
# ==============================================================================
def validar_aposta(jogo, cfg):
    soma_j = sum(jogo)
    if not (cfg["faixa_soma"][0] <= soma_j <= cfg["faixa_soma"][1]):
        return False

    pares_cnt = sum(1 for n in jogo if PROPS[n]["is_par"])
    if pares_cnt not in cfg["pares_aceitos"]:
        return False

    primos_cnt = sum(1 for n in jogo if PROPS[n]["is_primo"])
    if primos_cnt not in cfg["primos_aceitos"]:
        return False

    moldura_cnt = sum(1 for n in jogo if PROPS[n]["is_moldura"])
    if moldura_cnt not in cfg["moldura_aceita"]:
        return False

    cols_count = [0] * 10
    dc_count = [0] * 10
    dd_count = [0] * 10
    linhas_count = [0] * 6

    for n in jogo:
        p = PROPS[n]
        linhas_count[p["r"]] += 1
        if linhas_count[p["r"]] > cfg["linhas"][p["r"]][1]:
            return False

        cols_count[p["c"]] += 1
        if cols_count[p["c"]] > cfg["colunas"][p["c"]][1]:
            return False

        dc_count[p["dc"]] += 1
        if dc_count[p["dc"]] > cfg["diag_cresc"][p["dc"]][1]:
            return False

        dd_count[p["dd"]] += 1
        if dd_count[p["dd"]] > cfg["diag_decresc"][p["dd"]][1]:
            return False

    for r in range(6):
        if linhas_count[r] < cfg["linhas"][r][0]:
            return False
    for c in range(10):
        if cols_count[c] < cfg["colunas"][c][0]:
            return False

    return True

# ==============================================================================
# ESTADO DE SESSÃO & CÁLCULOS INICIAIS
# ==============================================================================
if "historico_elliott" not in st.session_state:
    st.session_state.historico_elliott = HISTORICO_BASE

dados_calor = processar_metricas_elliott(st.session_state.historico_elliott)

# Ordena pelo score para definir o ranking top 40 padrão
ranking_ordenado = sorted(dados_calor.values(), key=lambda x: x["score"], reverse=True)
top_40_padrao = {item["numero"] for item in ranking_ordenado[:40]}

if "pool_trabalho" not in st.session_state:
    st.session_state.pool_trabalho = top_40_padrao.copy()

def toggle_dezena(n):
    if n in st.session_state.pool_trabalho:
        st.session_state.pool_trabalho.remove(n)
    else:
        st.session_state.pool_trabalho.add(n)

# Cálculo de limites térmicos para normalização
max_score = max(d["score"] for d in dados_calor.values())
min_score = min(d["score"] for d in dados_calor.values())
delta_score = max(0.1, max_score - min_score)

def obter_estilo_calor(score):
    norm = (score - min_score) / delta_score
    if norm >= 0.70:
        return {"cor_bg": "#fee2e2", "cor_texto": "#991b1b", "borda": "#ef4444", "icone": "🔥", "nivel": "Ultra Quente"}
    elif norm >= 0.45:
        return {"cor_bg": "#ffedd5", "cor_texto": "#9a3412", "borda": "#f97316", "icone": "☀️", "nivel": "Quente"}
    elif norm >= 0.25:
        return {"cor_bg": "#fef9c3", "cor_texto": "#854d0e", "borda": "#eab308", "icone": "🌤️", "nivel": "Morno"}
    else:
        return {"cor_bg": "#f1f5f9", "cor_texto": "#475569", "borda": "#94a3b8", "icone": "❄️", "nivel": "Frio"}

# ==============================================================================
# INTERFACE VISUAL
# ==============================================================================
st.title("🔥 MEGA60: Cartela Térmica de Elliott & Filtros")
st.caption("Matriz 6x10 com Calor Fractal • Introdução/Retirada Clicável • Varredura de Apostas")

# ------------------------------------------------------------------------------
# CARTELA INTERATIVA 6x10 COM CONTROLE DE POOL
# ------------------------------------------------------------------------------
with st.container(border=True):
    st.markdown("### 🎛️ Cartela Interativa de Elliott (Clique para Ativar / Remover)")
    
    # Botões de controle rápido
    b1, b2, b3, b4, b5 = st.columns(5)
    with b1:
        if st.button("🌊 Restaurar Top 40 Elliott", use_container_width=True):
            st.session_state.pool_trabalho = top_40_padrao.copy()
            st.rerun()
    with b2:
        if st.button("🔥 Apenas Quentes (Top 20)", use_container_width=True):
            st.session_state.pool_trabalho = {item["numero"] for item in ranking_ordenado[:20]}
            st.rerun()
    with b3:
        if st.button("⚡ +9 Dezenas Fibonacci", use_container_width=True):
            st.session_state.pool_trabalho.update(FIBONACCI_MEGASENA)
            st.rerun()
    with b4:
        if st.button("✅ Marcar Todas (60)", use_container_width=True):
            st.session_state.pool_trabalho = set(range(1, 61))
            st.rerun()
    with b5:
        if st.button("🧹 Limpar Cartela", use_container_width=True):
            st.session_state.pool_trabalho = set()
            st.rerun()

    st.write("")

    # Grid interativo 6x10
    for r in range(6):
        cols = st.columns(10)
        for c in range(10):
            n = r * 10 + c + 1
            meta = dados_calor[n]
            estilo = obter_estilo_calor(meta["score"])
            ativa = n in st.session_state.pool_trabalho
            
            # Formatação do rótulo
            check = "🟢" if ativa else "⚪"
            rotulo = f"{check} {n:02d}\n{estilo['icone']}{meta['score']:.0f}p"
            
            tipo = "primary" if ativa else "secondary"
            with cols[c]:
                if st.button(rotulo, key=f"btn_calor_{n}", type=tipo, use_container_width=True):
                    toggle_dezena(n)
                    st.rerun()

    # Legenda e status do pool
    st.divider()
    c_status1, c_status2 = st.columns([3, 1])
    with c_status1:
        st.markdown(
            "**Legenda de Calor:** &nbsp; "
            "<span style='color:#dc2626;font-weight:700;'>🔥 Ultra Quente (Onda 3 / Impulso)</span> &nbsp;|&nbsp; "
            "<span style='color:#ea580c;font-weight:700;'>☀️ Quente (Retração Fib Ótima)</span> &nbsp;|&nbsp; "
            "<span style='color:#ca8a04;font-weight:700;'>🌤️ Morno (Acumulação)</span> &nbsp;|&nbsp; "
            "<span style='color:#64748b;font-weight:700;'>❄️ Frio (Repouso)</span>",
            unsafe_allow_html=True
        )
        dezenas_formatadas = " - ".join([f"{n:02d}" for n in sorted(st.session_state.pool_trabalho)])
        st.write(f"**Dezenas Selecionadas no Pool:** `{dezenas_formatadas if dezenas_formatadas else 'Nenhuma'}`")
    
    with c_status2:
        qtd_sel = len(st.session_state.pool_trabalho)
        comb_totais = math.comb(qtd_sel, 6) if qtd_sel >= 6 else 0
        st.metric("Dezenas no Pool", f"{qtd_sel} / 60", delta=f"{qtd_sel - 40} vs Top 40")
        st.caption(f"Espaço: **{comb_totais:,}** combinações")

# ------------------------------------------------------------------------------
# MAPA TÉRMICO VISUAL (RAIO-X CONTINUO)
# ------------------------------------------------------------------------------
with st.expander("🗺️ Ver Mapa Térmico Geral da Matriz 6x10 (Visualização Contínua)", expanded=False):
    celulas_html = ""
    for r in range(6):
        for c in range(10):
            n = r * 10 + c + 1
            meta = dados_calor[n]
            est = obter_estilo_calor(meta["score"])
            ativa = n in st.session_state.pool_trabalho
            
            borda = "3px solid #16a34a" if ativa else f"1px solid {est['borda']}"
            opacidade = "1.0" if ativa else "0.55"
            
            celulas_html += (
                f'<div style="width:58px;height:48px;background:{est["cor_bg"]};color:{est["cor_texto"]};'
                f'border:{borda};border-radius:8px;opacity:{opacidade};display:flex;flex-direction:column;'
                f'align-items:center;justify-content:center;font-family:monospace;box-sizing:border-box;">'
                f'<span style="font-size:13px;font-weight:900;">{n:02d}</span>'
                f'<span style="font-size:10px;font-weight:700;">{est["icone"]} {meta["score"]}</span>'
                f'</div>'
            )

    html_code = f"""
    <!DOCTYPE html><html><head><meta charset="utf-8">
    <style>*{{box-sizing:border-box;}}body{{margin:0;padding:0;background:transparent;display:flex;justify-content:center;}}
    .box{{background:#ffffff;border:2px solid #cbd5e1;border-radius:12px;padding:12px;width:fit-content;}}
    .grid{{display:grid;grid-template-columns:repeat(10,58px);gap:6px;}}</style></head><body>
    <div class="box"><div class="grid">{celulas_html}</div></div></body></html>
    """
    components.html(html_code, height=360, scrolling=False)

# ------------------------------------------------------------------------------
# FILTROS MATRICIAIS E GERAÇÃO DE APOSTAS
# ------------------------------------------------------------------------------
with st.container(border=True):
    st.markdown("### 🎛️ Filtros para o Pool Selecionado")
    
    t_lin_col, t_diag, t_stats = st.tabs(["1️⃣ Linhas e Colunas", "2️⃣ Diagonais", "3️⃣ Primos, Paridade, Moldura e Soma"])
    
    with t_lin_col:
        st.markdown("**Linhas (L01 a L06):**")
        c_l = st.columns(6)
        lim_l = []
        opcoes = list(OPCOES_QTD.keys())
        for r in range(6):
            with c_l[r]:
                esc = st.selectbox(f"L{r+1:02d}", opcoes, index=0, key=f"flt_l_{r}")
                lim_l.append(OPCOES_QTD[esc])

        st.markdown("**Colunas (C01 a C10):**")
        c_c1, c_c2 = st.columns(5), st.columns(5)
        lim_c = []
        for c in range(10):
            alvo = c_c1[c] if c < 5 else c_c2[c - 5]
            with alvo:
                esc = st.selectbox(f"C{c+1:02d}", opcoes, index=4, key=f"flt_c_{c}")
                lim_c.append(OPCOES_QTD[esc])

    with t_diag:
        cd1, cd2 = st.columns(2)
        with cd1:
            st.markdown("**Diagonais Crescentes (DC01 a DC10 /):**")
            lim_dc = [OPCOES_QTD[st.selectbox(f"DC{d+1:02d}", opcoes, index=4, key=f"flt_dc_{d}")] for d in range(10)]
        with cd2:
            st.markdown("**Diagonais Decrescentes (DD01 a DD10 \\):**")
            lim_dd = [OPCOES_QTD[st.selectbox(f"DD{d+1:02d}", opcoes, index=4, key=f"flt_dd_{d}")] for d in range(10)]

    with t_stats:
        p1, p2, p3, p4 = st.columns(4)
        with p1:
            sel_primos = st.multiselect("Primos:", list(range(7)), default=[1, 2, 3], key="flt_primos")
        with p2:
            par_map = {"3P / 3I": 3, "2P / 4I": 2, "4P / 2I": 4, "1P / 5I": 1, "5P / 1I": 5}
            sel_pares_txt = st.multiselect("Paridade:", list(par_map.keys()), default=["3P / 3I", "2P / 4I", "4P / 2I"], key="flt_pares")
            sel_pares = {par_map[k] for k in sel_pares_txt}
        with p3:
            sel_moldura = st.multiselect("Moldura:", list(range(7)), default=[2, 3, 4], key="flt_moldura")
        with p4:
            faixa_soma = st.slider("Faixa de Soma:", 60, 310, (110, 240), key="flt_soma")

    cfg_varredura = {
        "linhas": lim_l,
        "colunas": lim_c,
        "diag_cresc": lim_dc,
        "diag_decresc": lim_dd,
        "primos_aceitos": set(sel_primos),
        "pares_aceitos": sel_pares,
        "moldura_aceita": set(sel_moldura),
        "faixa_soma": faixa_soma
    }

    st.divider()
    
    col_run, col_lim = st.columns([3, 1])
    with col_lim:
        teto_apostas = st.number_input("Teto de Jogos Aprovados:", min_value=10, max_value=20000, value=250, step=50)

    with col_run:
        pode_gerar = len(st.session_state.pool_trabalho) >= 6
        if st.button("🚀 Gerar e Filtrar Apostas do Pool Selecionado", type="primary", use_container_width=True, disabled=not pode_gerar):
            with st.spinner("Processando combinações contra os filtros..."):
                t0 = time.time()
                jogos_validos = []
                pool_lista = sorted(list(st.session_state.pool_trabalho))
                testadas = 0

                for c in combinations(pool_lista, 6):
                    testadas += 1
                    if validar_aposta(c, cfg_varredura):
                        jogos_validos.append(c)
                        if len(jogos_validos) >= teto_apostas:
                            break

                delta_t = time.time() - t0
                st.success(f"Filtro concluído em {delta_t:.2f}s! Combinações testadas: {testadas:,} | **Jogos aprovados: {len(jogos_validos):,}**")

                if jogos_validos:
                    txt_out = "\n".join([" ".join([f"{n:02d}" for n in j]) for j in jogos_validos])
                    
                    st.download_button(
                        "📥 Baixar Arquivo de Jogos (.TXT)",
                        data=txt_out,
                        file_name=f"apostas_mega60_calor_{len(jogos_validos)}.txt",
                        mime="text/plain",
                        use_container_width=True
                    )
                    
                    with st.expander("Visualizar Apostas Geradas", expanded=True):
                        for idx, aposta in enumerate(jogos_validos[:15], start=1):
                            scores_jogo = [f"{n:02d}" for n in aposta]
                            st.write(f"**Jogo #{idx:03d}:** `{' - '.join(scores_jogo)}` | Soma: `{sum(aposta)}`")
