import streamlit as st
import streamlit.components.v1 as components
import requests
from itertools import combinations, product
from collections import Counter
import math
import time
import re
import random
import pandas as pd

st.set_page_config(
    page_title="MEGA60 - Cartela Virtual & Filtros Estruturais",
    page_icon="🍀",
    layout="wide"
)

TOTAL_NUMS = 60
TAMANHO_JOGO_FINAL = 6
PRIMOS_MEGASENA = {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59}

MOLDURA_SET = (
    set(range(1, 11)) | 
    set(range(51, 61)) | 
    {r * 10 + 1 for r in range(6)} | 
    {r * 10 + 10 for r in range(6)}
)

FALLBACK_MEGASENA = [
    [4, 12, 18, 30, 35, 54], [1, 9, 15, 23, 44, 52], [7, 14, 27, 39, 48, 59],
    [10, 11, 25, 33, 42, 58], [3, 16, 28, 37, 45, 60], [5, 20, 22, 34, 49, 56],
    [8, 17, 31, 40, 50, 57], [2, 13, 24, 38, 43, 55], [6, 19, 29, 36, 47, 53],
    [12, 21, 32, 41, 46, 51], [4, 15, 26, 35, 48, 58], [7, 18, 23, 39, 44, 59],
    [1, 10, 27, 34, 42, 54], [9, 14, 30, 37, 50, 60], [3, 16, 25, 38, 49, 57],
    [5, 11, 28, 33, 45, 53], [8, 20, 31, 43, 52, 56], [2, 17, 24, 36, 47, 55],
    [6, 13, 29, 40, 46, 51], [12, 19, 32, 41, 50, 58]
]

# ==============================================================================
# TABELA PRÉ-COMPUTADA DA MATRIZ 6x10
# ==============================================================================
PROPS = {}
for n in range(1, 61):
    r = (n - 1) // 10
    c = (n - 1) % 10
    dc = (c + r) % 10
    dd = (c - r) % 10
    PROPS[n] = {
        "r": r,
        "c": c,
        "dc": dc,
        "dd": dd,
        "is_primo": n in PRIMOS_MEGASENA,
        "is_par": n % 2 == 0,
        "is_moldura": n in MOLDURA_SET
    }

OPCOES_QUANTIDADE = {
    "Livre (0 a 6)": (0, 6),
    "0 (Nenhuma)": (0, 0),
    "Exatamente 1": (1, 1),
    "Exatamente 2": (2, 2),
    "Exatamente 3": (3, 3),
    "Exatamente 4": (4, 4),
    "0 ou 1": (0, 1),
    "1 ou 2": (1, 2),
    "0 a 2": (0, 2),
    "2 a 3": (2, 3),
    "1 a 3": (1, 3)
}

# ==============================================================================
# MOTOR MATEMÁTICO: VALIDAÇÃO DOS JOGOS DE 6 NÚMEROS
# ==============================================================================
def validar_aposta_final_6(jogo, cfg):
    soma_j = sum(jogo)
    if not (cfg["faixa_soma"][0] <= soma_j <= cfg["faixa_soma"][1]):
        return False

    primos_cnt = sum(1 for n in jogo if PROPS[n]["is_primo"])
    if primos_cnt not in cfg["primos_aceitos"]:
        return False

    pares_cnt = sum(1 for n in jogo if PROPS[n]["is_par"])
    if pares_cnt not in cfg["pares_aceitos"]:
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
        r_idx, c_idx, dc_idx, dd_idx = p["r"], p["c"], p["dc"], p["dd"]

        linhas_count[r_idx] += 1
        if linhas_count[r_idx] > cfg["linhas"][r_idx][1]:
            return False

        cols_count[c_idx] += 1
        if cols_count[c_idx] > cfg["colunas"][c_idx][1]:
            return False

        dc_count[dc_idx] += 1
        if dc_count[dc_idx] > cfg["diag_cresc"][dc_idx][1]:
            return False

        dd_count[dd_idx] += 1
        if dd_count[dd_idx] > cfg["diag_decresc"][dd_idx][1]:
            return False

    for r in range(6):
        if linhas_count[r] < cfg["linhas"][r][0]:
            return False

    for c in range(10):
        if cols_count[c] < cfg["colunas"][c][0]:
            return False

    for d in range(10):
        if dc_count[d] < cfg["diag_cresc"][d][0] or dd_count[d] < cfg["diag_decresc"][d][0]:
            return False

    return True

def executar_varredura_pool(pool_dezenas, cfg, bar_progresso, container_status, ticker_metricas):
    """Combina apenas as dezenas selecionadas na cartela e filtra com os 7 quadros."""
    t_inicio = time.time()
    dezenas_candidatas = sorted(list(pool_dezenas))
    k_escolhidas = len(dezenas_candidatas)

    if k_escolhidas < 6:
        container_status.error("Selecione pelo menos 6 dezenas na Cartela Virtual para gerar apostas.")
        return []

    total_combinacoes = math.comb(k_escolhidas, 6)
    container_status.write(
        f"🎯 **Varredura Ativa:** {k_escolhidas} dezenas selecionadas na cartela. "
        f"Total de combinações de 6 a testar: **{total_combinacoes:,} jogos**."
    )

    jogos_aprovados = []
    testadas = 0
    lote_update = max(1, min(1000, total_combinacoes // 50))

    for comb in combinations(dezenas_candidatas, 6):
        testadas += 1
        if validar_aposta_final_6(comb, cfg):
            jogos_aprovados.append(list(comb))

        if testadas % lote_update == 0:
            prog = testadas / total_combinacoes
            bar_progresso.progress(prog)
            delta_t = max(0.001, time.time() - t_inicio)
            velocidade = int(testadas / delta_t)
            ticker_metricas.markdown(
                f"**Linha de Serviço:** `{testadas:,}` de `{total_combinacoes:,}` ({prog*100:.1f}%) | "
                f"Apostas aprovadas: `{len(jogos_aprovados):,}` | "
                f"Velocidade: `{velocidade:,} comb/s` | Tempo: `{delta_t:.2f}s`"
            )

    bar_progresso.progress(1.0)
    delta_final = max(0.001, time.time() - t_inicio)
    ticker_metricas.markdown(
        f"**Linha de Serviço:** `{testadas:,}` combinações testadas | "
        f"Aprovados finais: `{len(jogos_aprovados):,}` jogos de 6 dezenas | "
        f"Tempo total: `{delta_final:.2f}s`"
    )
    return jogos_aprovados

# ==============================================================================
# FUNÇÕES DE UPLOAD E CONFERÊNCIA
# ==============================================================================
def processar_arquivo_upload(conteudo_bytes):
    texto = conteudo_bytes.decode("utf-8", errors="ignore")
    linhas = texto.strip().splitlines()
    jogos = []
    invalidos = 0
    for linha in linhas:
        l = linha.strip()
        if not l: continue
        nums = [int(x) for x in re.findall(r"\b\d+\b", l)]
        nums_validos = sorted(list(set([n for n in nums if 1 <= n <= 60])))
        if len(nums_validos) == 6:
            jogos.append(nums_validos)
        else:
            invalidos += 1
    return jogos, invalidos

def conferir_apostas_contra_sorteio(lista_jogos, dezenas_sorteadas):
    sorteio_set = set(dezenas_sorteadas)
    placar = {6: [], 5: [], 4: [], 3: [], 2: [], 1: [], 0: []}
    relatorio = []
    for idx, jogo in enumerate(lista_jogos):
        acertos = sorted(list(set(jogo) & sorteio_set))
        qtd = len(acertos)
        placar[qtd].append(idx + 1)
        relatorio.append({
            "num_aposta": idx + 1,
            "jogo": jogo,
            "qtd_acertos": qtd,
            "acertos": acertos
        })
    return relatorio, placar

# ==============================================================================
# INICIALIZAÇÃO DE ESTADO
# ==============================================================================
if "historico" not in st.session_state:
    st.session_state.historico = [list(j) for j in FALLBACK_MEGASENA]
    st.session_state.origem = "Base Local Offline"

if "jogos_aprovados" not in st.session_state:
    st.session_state.jogos_aprovados = []

if "jogos_upload" not in st.session_state:
    st.session_state.jogos_upload = []

if "cartela_selecao" not in st.session_state:
    # Inicia com as 60 selecionadas por padrão
    st.session_state.cartela_selecao = set(range(1, 61))

def alternar_dezena(n):
    if n in st.session_state.cartela_selecao:
        st.session_state.cartela_selecao.remove(n)
    else:
        st.session_state.cartela_selecao.add(n)

# ==============================================================================
# INTERFACE PRINCIPAL
# ==============================================================================
st.title("🍀 MEGA60: Cartela Virtual & Filtros Estruturais")
st.caption("Marque as dezenas na Cartela Interativa • Filtre pelos 7 Quadros • Confira Resultados")

tab_cartela, tab_config, tab_volante, tab_upload, tab_historico = st.tabs([
    "🎟️ Cartela Virtual (Selecione os Números)",
    "🎛️ Configuração dos 7 Quadros",
    "🗺️ Volante Visual & Raio-X",
    "📥 Upload, Estatísticas & Conferência",
    "📊 Histórico & Conexão Caixa"
])

# ==============================================================================
# ABA 1: CARTELA VIRTUAL INTERATIVA
# ==============================================================================
with tab_cartela:
    st.subheader("🎟️ Cartela Virtual Interativa (Matriz 6x10)")
    st.markdown("Clique nos números que deseja jogar. O sistema gerará as combinações **apenas a partir das dezenas ativas**.")

    # BOTÕES DE AÇÃO RÁPIDA
    c_btn1, c_btn2, c_btn3, c_btn4, c_btn5 = st.columns(5)
    with c_btn1:
        if st.button("🧹 Limpar Cartela", use_container_width=True):
            st.session_state.cartela_selecao = set()
            st.rerun()
    with c_btn2:
        if st.button("✅ Marcar Todas (60)", use_container_width=True):
            st.session_state.cartela_selecao = set(range(1, 61))
            st.rerun()
    with c_btn3:
        if st.button("🔢 Apenas Primos (17)", use_container_width=True):
            st.session_state.cartela_selecao = set(PRIMOS_MEGASENA)
            st.rerun()
    with c_btn4:
        if st.button("🖼️ Apenas Moldura (28)", use_container_width=True):
            st.session_state.cartela_selecao = set(MOLDURA_SET)
            st.rerun()
    with c_btn5:
        if st.button("🎲 15 Aleatórias", use_container_width=True):
            st.session_state.cartela_selecao = set(random.sample(range(1, 61), 15))
            st.rerun()

    st.divider()

    # RENDERIZAÇÃO DA CARTELA VIRTUAL (10 COLUNAS X 6 LINHAS)
    for r in range(6):
        cols = st.columns(10)
        for c in range(10):
            n = r * 10 + c + 1
            esta_marcada = n in st.session_state.cartela_selecao
            tipo_btn = "primary" if esta_marcada else "secondary"
            rotulo = f"🟢 {n:02d}" if esta_marcada else f"{n:02d}"
            
            with cols[c]:
                if st.button(rotulo, key=f"btn_num_{n}", type=tipo_btn, use_container_width=True):
                    alternar_dezena(n)
                    st.rerun()

    qtd_sel = len(st.session_state.cartela_selecao)
    st.divider()

    # PAINEL DE STATUS DA SELEÇÃO
    col_inf1, col_inf2 = st.columns([2, 1])
    with col_inf1:
        if qtd_sel < 6:
            st.warning(f"⚠️ Você selecionou **{qtd_sel} dezenas**. Selecione pelo menos 6 números para poder combinar.")
        else:
            total_comb = math.comb(qtd_sel, 6)
            dezenas_txt = " - ".join([f"{n:02d}" for n in sorted(list(st.session_state.cartela_selecao))])
            st.success(f"✅ **{qtd_sel} Dezenas Ativas:** `{dezenas_txt}`")
            st.info(f"📊 Espaço Amostral: Esta seleção produz **{total_comb:,} combinações brutas de 6 números** antes dos filtros.")

    with col_inf2:
        st.metric("Dezenas Selecionadas", f"{qtd_sel} / 60")

# ==============================================================================
# ABA 2: CONFIGURAÇÃO DOS 7 QUADROS & EXECUÇÃO DO FILTRO
# ==============================================================================
with tab_config:
    st.markdown("### 🎛️ Filtros Estruturais para Aplicar Sobre as Dezenas Selecionadas")

    # QUADRO 1: LINHAS
    with st.container(border=True):
        st.markdown("#### 1️⃣ Linhas Individuais (01 a 06)")
        cols_l = st.columns(6)
        limites_linhas = []
        opcoes_nomes = list(OPCOES_QUANTIDADE.keys())
        for r in range(6):
            with cols_l[r]:
                esc = st.selectbox(f"Linha {r+1:02d}", opcoes_nomes, index=0, key=f"sel_l_{r}")
                limites_linhas.append(OPCOES_QUANTIDADE[esc])

    # QUADRO 2: COLUNAS
    with st.container(border=True):
        st.markdown("#### 2️⃣ Colunas Individuais (01 a 10)")
        cols_c_up, cols_c_dw = st.columns(5), st.columns(5)
        limites_colunas = []
        for c in range(10):
            alvo = cols_c_up[c] if c < 5 else cols_c_dw[c - 5]
            with alvo:
                esc = st.selectbox(f"Coluna {c+1:02d}", opcoes_nomes, index=6, key=f"sel_c_{c}")
                limites_colunas.append(OPCOES_QUANTIDADE[esc])

    # QUADRO 3: DIAGONAIS
    c_diag1, c_diag2 = st.columns(2)
    with c_diag1:
        with st.container(border=True):
            st.markdown("#### 3️⃣ Diag. Crescentes (DC01 a DC10 /)")
            with st.expander("Abrir Diagonais Crescentes", expanded=False):
                limites_dc = []
                for d in range(10):
                    esc = st.selectbox(f"DC{d+1:02d}", opcoes_nomes, index=6, key=f"sel_dc_{d}")
                    limites_dc.append(OPCOES_QUANTIDADE[esc])
    with c_diag2:
        with st.container(border=True):
            st.markdown("#### 4️⃣ Diag. Decrescentes (DD01 a DD10 \\)")
            with st.expander("Abrir Diagonais Decrescentes", expanded=False):
                limites_dd = []
                for d in range(10):
                    esc = st.selectbox(f"DD{d+1:02d}", opcoes_nomes, index=6, key=f"sel_dd_{d}")
                    limites_dd.append(OPCOES_QUANTIDADE[esc])

    # QUADRO 4: PRIMOS, PARES, MOLDURA E SOMA
    with st.container(border=True):
        st.markdown("#### 5️⃣ Primos, Pares, Moldura e Faixa de Soma")
        c_p1, c_p2, c_p3, c_p4 = st.columns(4)
        with c_p1:
            primos_sel = st.multiselect("Quantidade de Primos:", [0, 1, 2, 3, 4, 5, 6], default=[1, 2])
        with c_p2:
            opcoes_par = {"3P / 3I": 3, "2P / 4I": 2, "4P / 2I": 4, "1P / 5I": 1, "5P / 1I": 5, "0P / 6I": 0, "6P / 0I": 6}
            par_sel = st.multiselect("Pares / Ímpares:", list(opcoes_par.keys()), default=["3P / 3I", "2P / 4I", "4P / 2I"])
            pares_valores = {opcoes_par[k] for k in par_sel}
        with c_p3:
            moldura_sel = st.multiselect("Dezenas na Moldura:", [0, 1, 2, 3, 4, 5, 6], default=[2, 3, 4])
        with c_p4:
            faixa_soma = st.slider("Faixa de Soma:", 50, 320, (110, 240))

    config_total = {
        "linhas": limites_linhas,
        "colunas": limites_colunas,
        "diag_cresc": limites_dc,
        "diag_decresc": limites_dd,
        "primos_aceitos": set(primos_sel),
        "pares_aceitos": pares_valores,
        "moldura_aceita": set(moldura_sel),
        "faixa_soma": faixa_soma
    }

    st.divider()

    # LINHA DE ACOMPANHAMENTO DE SERVIÇO
    st.markdown("### 📡 Linha de Acompanhamento de Serviço")
    placeholder_metricas = st.empty()
    barra_progresso = st.progress(0, text="Aguardando comando de execução...")

    pode_processar = len(st.session_state.cartela_selecao) >= 6

    if st.button("🚀 Gerar e Filtrar Apostas das Dezenas da Cartela", use_container_width=True, disabled=not pode_processar):
        if not primos_sel:
            st.error("Selecione pelo menos uma quantidade aceita de Primos.")
        elif not par_sel:
            st.error("Selecione pelo menos uma proporção de Pares/Ímpares.")
        elif not moldura_sel:
            st.error("Selecione pelo menos uma quantidade de Moldura.")
        else:
            with st.status("🛠️ Processando Motor Combinatório...", expanded=True) as status_box:
                t0 = time.time()
                resultados = executar_varredura_pool(
                    st.session_state.cartela_selecao,
                    config_total,
                    barra_progresso,
                    status_box,
                    placeholder_metricas
                )
                t_fim = time.time() - t0
                st.session_state.jogos_aprovados = resultados
                total_gerado = len(resultados)

                if total_gerado > 0:
                    status_box.update(
                        label=f"✅ Sucesso! {total_gerado:,} apostas oficiais de 6 dezenas aprovadas em {t_fim:.2f}s.",
                        state="complete",
                        expanded=False
                    )
                else:
                    status_box.update(
                        label=f"⚠️ Concluído em {t_fim:.2f}s: Nenhuma combinação das dezenas selecionadas atendeu todos os filtros simultaneamente.",
                        state="error",
                        expanded=True
                    )

    if st.session_state.jogos_aprovados:
        qtd_aprov = len(st.session_state.jogos_aprovados)
        st.success(f"🎯 **Total Aprovado:** {qtd_aprov:,} apostas oficiais de 6 dezenas prontas!")
        txt_saida = "\n".join([" ".join([f"{n:02d}" for n in j]) for j in st.session_state.jogos_aprovados])
        
        c_d1, c_d2 = st.columns([3, 1])
        with c_d1:
            st.download_button(
                "📥 Baixar Arquivo com Jogos Aprovados (.TXT)",
                data=txt_saida,
                file_name=f"mega60_cartela_filtrada_{qtd_aprov}.txt",
                mime="text/plain",
                use_container_width=True
            )
        with c_d2:
            st.metric("Apostas Geradas", f"{qtd_aprov:,}")

        amostra = min(qtd_aprov, 50)
        with st.expander(f"Visualizar Conferência Inicial ({amostra} de {qtd_aprov:,})", expanded=True):
            for i, j in enumerate(st.session_state.jogos_aprovados[:amostra]):
                p = sum(1 for n in j if PROPS[n]["is_primo"])
                par = sum(1 for n in j if PROPS[n]["is_par"])
                mold = sum(1 for n in j if PROPS[n]["is_moldura"])
                st.markdown(f"**Jogo #{i+1:04d}:** `{' - '.join([f'{n:02d}' for n in j])}` | {par}P/{6-par}I | {p} Primos | {mold} Moldura | Soma: {sum(j)}")

# ==============================================================================
# ABA 3: VOLANTE VISUAL & RAIO-X
# ==============================================================================
with tab_volante:
    st.subheader("Dissecação da Cartela Oficial")
    if st.session_state.jogos_aprovados:
        total_jogos = len(st.session_state.jogos_aprovados)
        sel_idx = st.slider("Escolha a aposta para inspecionar:", 1, total_jogos, 1) if total_jogos > 1 else 1
        jogo_ativo = st.session_state.jogos_aprovados[sel_idx - 1]
        marcadas = set(jogo_ativo)

        c_v1, c_v2 = st.columns([1, 1])
        with c_v1:
            celulas = ""
            for r in range(6):
                for c in range(10):
                    n = r * 10 + c + 1
                    if n in marcadas:
                        celulas += f'<div style="width:36px;height:36px;background:linear-gradient(135deg,#16a34a,#15803d);color:#fff;border:2px solid #0f5132;font-weight:800;border-radius:8px;display:flex;align-items:center;justify-content:center;font-family:monospace;font-size:13px;box-sizing:border-box;">{n:02d}</div>'
                    else:
                        bg = "#f1f5f9" if n in MOLDURA_SET else "#ffffff"
                        celulas += f'<div style="width:36px;height:36px;background:{bg};color:#64748b;border:1px solid #cbd5e1;font-weight:600;border-radius:8px;display:flex;align-items:center;justify-content:center;font-family:monospace;font-size:13px;box-sizing:border-box;">{n:02d}</div>'
            
            html_cartela = f"""
            <!DOCTYPE html><html><head><meta charset="utf-8">
            <style>*{{box-sizing:border-box;}}body{{margin:0;padding:0;display:flex;justify-content:center;background:transparent;font-family:sans-serif;}}
            .box{{background:#fff;border:2px solid #16a34a;border-radius:12px;padding:12px;box-shadow:0 4px 12px rgba(22,163,74,0.12);width:fit-content;}}
            .grid{{display:grid;grid-template-columns:repeat(10,36px);gap:5px;}}</style></head><body>
            <div class="box"><div style="font-weight:800;font-size:14px;margin-bottom:10px;color:#15803d;text-align:center;">Jogo #{sel_idx:04d}: {' - '.join([f'{n:02d}' for n in jogo_ativo])}</div>
            <div class="grid">{celulas}</div></div></body></html>
            """
            components.html(html_cartela, height=330, scrolling=False)

        with c_v2:
            with st.container(border=True):
                st.markdown("#### 🔬 Raio-X Detalhado do Jogo de 6 Dezenas")
                cnt_linhas = Counter(PROPS[n]["r"] + 1 for n in jogo_ativo)
                cnt_colunas = Counter(PROPS[n]["c"] + 1 for n in jogo_ativo)
                cnt_dc = Counter(PROPS[n]["dc"] + 1 for n in jogo_ativo)
                cnt_dd = Counter(PROPS[n]["dd"] + 1 for n in jogo_ativo)

                st.markdown("**Linhas:** " + " • ".join([f"L{k}: `{v}x`" for k, v in sorted(cnt_linhas.items())]))
                st.markdown("**Colunas:** " + " • ".join([f"C{k:02d}: `{v}x`" for k, v in sorted(cnt_colunas.items())]))
                st.markdown("**Diagonais Cresc.:** " + " • ".join([f"DC{k:02d}: `{v}x`" for k, v in sorted(cnt_dc.items())]))
                st.markdown("**Diagonais Decresc.:** " + " • ".join([f"DD{k:02d}: `{v}x`" for k, v in sorted(cnt_dd.items())]))
                
                pr = sum(1 for n in jogo_ativo if PROPS[n]["is_primo"])
                pa = sum(1 for n in jogo_ativo if PROPS[n]["is_par"])
                mo = sum(1 for n in jogo_ativo if PROPS[n]["is_moldura"])
                st.divider()
                st.markdown(f"**Pares/Ímpares:** `{pa}P / {6-pa}I` | **Primos:** `{pr}` | **Moldura:** `{mo}` | **Soma:** `{sum(jogo_ativo)}`")
    else:
        st.info("Gere jogos na aba anterior para inspecionar no volante interativo.")

# ==============================================================================
# ABA 4: UPLOAD & CONFERÊNCIA
# ==============================================================================
with tab_upload:
    st.subheader("📥 Upload, Estatísticas & Conferência de Resultados")
    arquivo_enviado = st.file_uploader("Carregue seu arquivo de apostas (.txt ou .csv):", type=["txt", "csv"])

    if arquivo_enviado is not None:
        conteudo = arquivo_enviado.read()
        jogos_carregados, invalidos = processar_arquivo_upload(conteudo)
        st.session_state.jogos_upload = jogos_carregados
        if invalidos > 0:
            st.warning(f"⚠️ {invalidos} linha(s) ignoradas por não conterem 6 dezenas válidas (1 a 60).")

    if st.session_state.jogos_upload:
        jogos_up = st.session_state.jogos_upload
        total_up = len(jogos_up)
        st.success(f"✅ **Arquivo Ativo:** **{total_up:,} apostas** carregadas.")

        col_diag_left, col_conf_right = st.columns([1, 1], gap="large")

        # COLUNA 1: DIAGNÓSTICO
        with col_diag_left:
            st.markdown("### 📊 Diagnóstico das Apostas")
            cnt_nums = Counter()
            somas = []
            for j in jogos_up:
                cnt_nums.update(j)
                somas.append(sum(j))

            m1, m2, m3 = st.columns(3)
            m1.metric("Total", f"{total_up:,}")
            m2.metric("Soma Média", f"{sum(somas)/len(somas):.1f}")
            m3.metric("Mais Frequente", f"{cnt_nums.most_common(1)[0][0]:02d}")

            v_min, v_max = min(cnt_nums.values()), max(cnt_nums.values())
            delta_v = max(1, v_max - v_min)
            celulas_up_heat = ""
            for r in range(6):
                for c in range(10):
                    n = r * 10 + c + 1
                    freq = cnt_nums[n]
                    ratio = (freq - v_min) / delta_v
                    bg = "#f8fafc" if freq == 0 else ("#bbf7d0" if ratio < 0.35 else ("#fed7aa" if ratio < 0.70 else "#fca5a5"))
                    color = "#94a3b8" if freq == 0 else ("#166534" if ratio < 0.35 else ("#9a3412" if ratio < 0.70 else "#991b1b"))
                    celulas_up_heat += f'<div style="width:38px;height:38px;background:{bg};color:{color};border-radius:6px;display:flex;flex-direction:column;align-items:center;justify-content:center;font-family:monospace;border:1px solid rgba(0,0,0,0.08);box-sizing:border-box;"><span style="font-size:12px;font-weight:900;">{n:02d}</span><span style="font-size:9px;font-weight:700;">{freq}x</span></div>'

            html_up = f'<!DOCTYPE html><html><head><meta charset="utf-8"><style>*{{box-sizing:border-box;}}body{{margin:0;padding:0;background:transparent;display:flex;justify-content:center;font-family:sans-serif;}}.box{{background:#fff;border:2px solid #cbd5e1;border-radius:12px;padding:10px;width:fit-content;}}.grid{{display:grid;grid-template-columns:repeat(10,38px);gap:4px;}}</style></head><body><div class="box"><div class="grid">{celulas_up_heat}</div></div></body></html>'
            components.html(html_up, height=290, scrolling=False)

        # COLUNA 2: CONFERIDOR
        with col_conf_right:
            st.markdown("### 🎯 Conferência de Resultados")
            ult_sorteio = st.session_state.historico[-1] if st.session_state.historico else [4, 12, 18, 30, 35, 54]
            txt_padrao = " ".join([f"{n:02d}" for n in ult_sorteio])

            modo_origem = st.radio("Origem do Sorteio:", ["Último Sorteio Oficial", "Digitar Manualmente"], horizontal=True)
            if modo_origem == "Último Sorteio Oficial":
                dezenas_conf = ult_sorteio
                st.info(f"🏆 Concurso Oficial: **{' - '.join([f'{n:02d}' for n in dezenas_conf])}**")
            else:
                entrada_manual = st.text_input("6 Dezenas Sorteadas (separadas por espaço):", value=txt_padrao)
                nums_man = [int(x) for x in re.findall(r"\b\d+\b", entrada_manual)]
                dezenas_conf = sorted(list(set([n for n in nums_man if 1 <= n <= 60])))

            if len(dezenas_conf) == 6:
                relatorio_conf, placar_conf = conferir_apostas_contra_sorteio(jogos_up, dezenas_conf)
                c_s, c_q, c_qd, c_t = st.columns(4)
                c_s.metric("Sena (6)", f"{len(placar_conf[6])}")
                c_q.metric("Quina (5)", f"{len(placar_conf[5])}")
                c_qd.metric("Quadra (4)", f"{len(placar_conf[4])}")
                c_t.metric("Terno (3)", f"{len(placar_conf[3])}")

                tot_prem = len(placar_conf[6]) + len(placar_conf[5]) + len(placar_conf[4])
                if tot_prem > 0:
                    st.balloons()
                    st.success(f"🎉 **{tot_prem} aposta(s) premiada(s)** (Quadra, Quina ou Sena)!")

                filtro_ex = st.selectbox("Filtrar:", ["Apenas Premiadas (4, 5, 6)", "Todas as Apostas"], index=0 if tot_prem > 0 else 1)
                sorteio_set = set(dezenas_conf)
                for item in relatorio_conf[:30]:
                    qtd_a = item["qtd_acertos"]
                    if filtro_ex == "Apenas Premiadas (4, 5, 6)" and qtd_a < 4: continue
                    badge = "🏆 SENA!" if qtd_a == 6 else ("🥈 QUINA!" if qtd_a == 5 else ("🥉 QUADRA!" if qtd_a == 4 else ""))
                    bolinhas = "".join([f"<span style='display:inline-flex;align-items:center;justify-content:center;width:28px;height:28px;background:{'#16a34a' if n in sorteio_set else '#f1f5f9'};color:{'#ffffff' if n in sorteio_set else '#475569'};font-weight:800;font-size:12px;border-radius:50%;margin:0 2px;font-family:monospace;'>{n:02d}</span>" for n in item["jogo"]])
                    st.markdown(f"<div style='background:#fff;border-left:4px solid {'#16a34a' if qtd_a >= 4 else '#cbd5e1'};padding:6px 12px;margin:4px 0;display:flex;justify-content:space-between;align-items:center;'><div><span style='font-weight:700;'>#{item['num_aposta']:03d}</span> {bolinhas}</div><div><span style='font-weight:700;color:#16a34a;'>{qtd_a} acertos {badge}</span></div></div>", unsafe_allow_html=True)

# ==============================================================================
# ABA 5: HISTÓRICO
# ==============================================================================
with tab_historico:
    st.subheader("Base de Sorteios Oficiais")
    st.write(f"Concursos ativos em memória: **{len(st.session_state.historico)}** ({st.session_state.origem})")
    if st.button("🌐 Sincronizar Histórico com a Caixa Agora"):
        with st.spinner("Conectando à Caixa..."):
            try:
                r = requests.get("https://servicebus2.caixa.gov.br/portaldeloterias/api/megasena", headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
                if r.status_code == 200:
                    ult = r.json()
                    st.success(f"Conectado com sucesso! Último concurso oficial: #{ult['numero']}")
                else:
                    st.warning("Servidor da Caixa indisponível no momento.")
            except Exception as e:
                st.error(f"Erro ao conectar: {e}")
