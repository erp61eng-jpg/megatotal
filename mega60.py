import streamlit as st
import pandas as pd
import numpy as np
from itertools import combinations
from collections import Counter
import math
import time
import json
import re

st.set_page_config(
    page_title="MEGA60 - Sistema de Elliott & Filtros Combinatórios",
    page_icon="🌊",
    layout="wide"
)

# ==============================================================================
# CONSTANTES & ESTRUTURA DA MATRIZ 6x10
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

# Histórico base para cálculo de ondas e atrasos
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
# MOTOR DE ONDAS DE ELLIOTT (CICLOS, RETRAÇÕES & MOMENTUM)
# ==============================================================================
def calcular_ranking_elliott(historico):
    """
    Avalia os 60 números segundo a dinâmica de ondas:
    1. Atraso (Delay): proximidade com níveis de retração de Fibonacci (2, 3, 5, 8, 13 concursos).
    2. Onda de Impulso: aceleração nos últimos 5 e 15 sorteios (curto prazo).
    3. Ressonância Fractal: status nativo na sequência de Fibonacci.
    """
    total_concursos = len(historico)
    atrasos = {n: total_concursos for n in range(1, 61)}
    freq_5 = {n: 0 for n in range(1, 61)}
    freq_15 = {n: 0 for n in range(1, 61)}

    # Varredura do histórico do mais recente ao mais antigo
    for idx_rev, sorteio in enumerate(reversed(historico)):
        for n in sorteio:
            if atrasos[n] == total_concursos:
                atrasos[n] = idx_rev
            if idx_rev < 5:
                freq_5[n] += 1
            if idx_rev < 15:
                freq_15[n] += 1

    scores = {}
    for n in range(1, 61):
        atr = atrasos[n]
        
        # Pontuação de retração: bônus quando o atraso coincide com nós de onda (Fibonacci)
        dist_fib = min(abs(atr - f) for f in [1, 2, 3, 5, 8, 13, 21])
        score_retracao = max(0.0, 10.0 - (dist_fib * 2.2))
        
        # Pontuação de impulso: momentum recente (Onda 3 em andamento)
        score_impulso = (freq_5[n] * 6.0) + (freq_15[n] * 2.5)
        
        # Bônus harmônico de Fibonacci
        score_fractal = 3.5 if PROPS[n]["is_fib"] else 0.0

        # Penalidade por exaustão (> 22 concursos em repouso)
        penalidade_sono = -4.0 if atr > 21 else 0.0

        score_total = score_retracao + score_impulso + score_fractal + penalidade_sono
        
        scores[n] = {
            "numero": n,
            "score": round(score_total, 2),
            "atraso": atr,
            "fase": "Impulso (Onda 3)" if freq_5[n] >= 2 else ("Retração Ótima" if dist_fib <= 1 else "Acumulação"),
            "fibonacci": "Sim" if PROPS[n]["is_fib"] else "Não"
        }

    df_elliott = pd.DataFrame(scores.values()).sort_values(by="score", ascending=False).reset_index(drop=True)
    return df_elliott

# ==============================================================================
# MOTOR COMBINATÓRIO E FILTROS MATRICIAIS
# ==============================================================================
def validar_combinacao(jogo, cfg):
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
# INTERFACE E ESTADO
# ==============================================================================
if "historico_elliott" not in st.session_state:
    st.session_state.historico_elliott = HISTORICO_BASE

df_elliott = calcular_ranking_elliott(st.session_state.historico_elliott)
top_40_iniciais = sorted(df_elliott.head(40)["numero"].tolist())

if "pool_trabalho" not in st.session_state:
    st.session_state.pool_trabalho = top_40_iniciais

st.title("🌊 MEGA60: Rotina de Elliott & Gestão do Pool de Dezenas")
st.caption("Classificação Fractal • Ajuste Dinâmico do Pool • Validação por Filtros Matriciais")

# ==============================================================================
# SEÇÃO 1: PAINEL DE ONDAS E GERENCIADOR DO POOL
# ==============================================================================
with st.container(border=True):
    st.markdown("### 📊 1. Ranking dos 40 Melhores Números (Sistema de Elliott)")
    
    col_tabela, col_controles = st.columns([3, 2])
    
    with col_tabela:
        st.dataframe(
            df_elliott.head(40),
            column_config={
                "numero": st.column_config.NumberColumn("Dezena", format="%02d"),
                "score": st.column_config.ProgressColumn("Score Elliott", format="%.2f", min_value=0, max_value=30),
                "atraso": st.column_config.NumberColumn("Atraso Atual"),
                "fase": st.column_config.TextColumn("Fase de Ciclo"),
                "fibonacci": st.column_config.TextColumn("Fibonacci?")
            },
            height=320,
            use_container_width=True
        )

    with col_controles:
        st.markdown("**🔧 Modificar / Acrescentar Números:**")
        
        # Ações rápidas
        c_act1, c_act2, c_act3 = st.columns(3)
        with c_act1:
            if st.button("Restaurar Top 40", use_container_width=True):
                st.session_state.pool_trabalho = top_40_iniciais
                st.rerun()
        with c_act2:
            if st.button("+5 Próximos", use_container_width=True):
                extras = df_elliott.iloc[40:45]["numero"].tolist()
                st.session_state.pool_trabalho = sorted(list(set(st.session_state.pool_trabalho + extras)))
                st.rerun()
        with c_act3:
            if st.button("Limpar Pool", use_container_width=True):
                st.session_state.pool_trabalho = []
                st.rerun()

        # Seleção granular
        pool_selecionado = st.multiselect(
            "Dezenas Ativas no Pool de Filtros:",
            options=list(range(1, 61)),
            default=st.session_state.pool_trabalho,
            format_func=lambda x: f"{x:02d}"
        )
        st.session_state.pool_trabalho = sorted(pool_selecionado)

        # Entrada textual livre para colar números
        entrada_livre = st.text_input("Inserir Dezenas Manualmente (ex: 04, 18, 33):", "")
        if st.button("Adicionar Dezenas Informadas"):
            nums_parse = [int(x) for x in re.findall(r"\b\d+\b", entrada_livre)]
            validos = [n for n in nums_parse if 1 <= n <= 60]
            st.session_state.pool_trabalho = sorted(list(set(st.session_state.pool_trabalho + validos)))
            st.rerun()

    qtd_ativas = len(st.session_state.pool_trabalho)
    total_combinacoes_brutas = math.comb(qtd_ativas, 6) if qtd_ativas >= 6 else 0
    st.info(f"🎯 **Status Atual do Pool:** **{qtd_ativas} dezenas ativas** | Combinações possíveis de 6 números: **{total_combinacoes_brutas:,}**")

# ==============================================================================
# SEÇÃO 2: CONFIGURAÇÃO DOS FILTROS E GERAÇÃO
# ==============================================================================
with st.container(border=True):
    st.markdown("### 🎛️ 2. Filtros Matriciais para o Pool Ativo")
    
    tab_f1, tab_f2, tab_f3 = st.tabs(["Linhas & Colunas", "Diagonais", "Primos, Moldura & Soma"])
    
    with tab_f1:
        st.markdown("**Limites por Linha (L01 a L06):**")
        cols_l = st.columns(6)
        lim_linhas = []
        opcoes = list(OPCOES_QTD.keys())
        for r in range(6):
            with cols_l[r]:
                esc = st.selectbox(f"L{r+1:02d}", opcoes, index=0, key=f"el_l_{r}")
                lim_linhas.append(OPCOES_QTD[esc])

        st.markdown("**Limites por Coluna (C01 a C10):**")
        cols_c1, cols_c2 = st.columns(5), st.columns(5)
        lim_colunas = []
        for c in range(10):
            alvo = cols_c1[c] if c < 5 else cols_c2[c - 5]
            with alvo:
                esc = st.selectbox(f"C{c+1:02d}", opcoes, index=4, key=f"el_c_{c}")
                lim_colunas.append(OPCOES_QTD[esc])

    with tab_f2:
        c_dc, c_dd = st.columns(2)
        with c_dc:
            st.markdown("**Diagonais Crescentes (DC01 a DC10 /):**")
            lim_dc = [OPCOES_QTD[st.selectbox(f"DC{d+1:02d}", opcoes, index=4, key=f"el_dc_{d}")] for d in range(10)]
        with c_dd:
            st.markdown("**Diagonais Decrescentes (DD01 a DD10 \\):**")
            lim_dd = [OPCOES_QTD[st.selectbox(f"DD{d+1:02d}", opcoes, index=4, key=f"el_dd_{d}")] for d in range(10)]

    with tab_f3:
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            sel_primos = st.multiselect("Primos:", list(range(7)), default=[1, 2, 3], key="el_primos")
        with c2:
            opcoes_par = {"3P / 3I": 3, "2P / 4I": 2, "4P / 2I": 4, "1P / 5I": 1, "5P / 1I": 5}
            sel_pares_txt = st.multiselect("Paridade:", list(opcoes_par.keys()), default=["3P / 3I", "2P / 4I", "4P / 2I"], key="el_pares")
            sel_pares = {opcoes_par[k] for k in sel_pares_txt}
        with c3:
            sel_moldura = st.multiselect("Moldura:", list(range(7)), default=[2, 3, 4], key="el_moldura")
        with c4:
            faixa_soma = st.slider("Faixa de Soma:", 60, 310, (120, 240), key="el_soma")

    cfg_ativa = {
        "linhas": lim_linhas,
        "colunas": lim_colunas,
        "diag_cresc": lim_dc,
        "diag_decresc": lim_dd,
        "primos_aceitos": set(sel_primos),
        "pares_aceitos": sel_pares,
        "moldura_aceita": set(sel_moldura),
        "faixa_soma": faixa_soma
    }

    st.divider()
    
    # Execução do motor
    col_exec, col_max = st.columns([3, 1])
    with col_max:
        max_apostas = st.number_input("Limite Máximo de Apostas:", min_value=10, max_value=50000, value=500, step=50)

    if st.button("🚀 Processar Apostas com Filtros", type="primary", use_container_width=True, disabled=qtd_ativas < 6):
        with st.spinner("Executando motor de varredura..."):
            t_inicio = time.time()
            jogos_aprovados = []
            testadas = 0

            for comb in combinations(st.session_state.pool_trabalho, 6):
                testadas += 1
                if validar_combinacao(comb, cfg_ativa):
                    jogos_aprovados.append(comb)
                    if len(jogos_aprovados) >= max_apostas:
                        break

            delta = time.time() - t_inicio
            st.success(f"Finalizado em {delta:.2f}s! Combinações testadas: {testadas:,} | **Jogos aprovados: {len(jogos_aprovados):,}**")

            if jogos_aprovados:
                txt_export = "\n".join([" ".join([f"{n:02d}" for n in j]) for j in jogos_aprovados])
                
                c_down, c_prev = st.columns([1, 2])
                with c_down:
                    st.download_button(
                        "📥 Baixar Apostas (.TXT)",
                        data=txt_export,
                        file_name=f"mega60_elliott_{len(jogos_aprovados)}.txt",
                        mime="text/plain",
                        use_container_width=True
                    )
                with c_prev:
                    with st.expander("Visualizar Primeiras Apostas Geradas"):
                        for i, j in enumerate(jogos_aprovados[:10], start=1):
                            st.write(f"**Aposta #{i:03d}:** `{' - '.join([f'{n:02d}' for n in j])}`")
