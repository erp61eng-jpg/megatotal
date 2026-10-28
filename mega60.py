import streamlit as st
import streamlit.components.v1 as components
import requests
from itertools import combinations, product
from collections import Counter
import time

st.set_page_config(
    page_title="MEGA60 - Laboratório Estrutural Granular",
    page_icon="🍀",
    layout="wide"
)

TOTAL_NUMS = 60
TAMANHO_JOGO = 6
PRIMOS_MEGASENA = {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59}

# 28 Dezenas Periféricas (Moldura da matriz 6x10)
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
    r = (n - 1) // 10       # Linha 0 a 5
    c = (n - 1) % 10        # Coluna 0 a 9
    dc = (c + r) % 10       # Diag Crescente 0 a 9
    dd = (c - r) % 10       # Diag Decrescente 0 a 9
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
# MOTOR MATEMÁTICO POR PARTICIONAMENTO EFICIENTE
# ==============================================================================
def gerar_particoes_linha(limites_linhas, alvo=6):
    """Gera todas as distribuições (k0, k1, k2, k3, k4, k5) onde sum(k) == 6."""
    val_ranges = [list(range(limites_linhas[i][0], limites_linhas[i][1] + 1)) for i in range(6)]
    particoes = []
    
    def backtrack(idx, soma_acumulada, tupla_atual):
        if idx == 6:
            if soma_acumulada == alvo:
                particoes.append(tupla_atual)
            return
        min_restante = sum(limites_linhas[j][0] for j in range(idx + 1, 6))
        max_restante = sum(limites_linhas[j][1] for j in range(idx + 1, 6))
        
        for qtd in val_ranges[idx]:
            nova_soma = soma_acumulada + qtd
            if nova_soma + min_restante <= alvo <= nova_soma + max_restante:
                backtrack(idx + 1, nova_soma, tupla_atual + (qtd,))

    backtrack(0, 0, ())
    return particoes

def motor_varredura_individual(cfg, bar_progresso, container_status, ticker_metricas):
    t_inicio = time.time()
    
    # 1. Filtra as dezenas disponíveis por linha eliminando colunas/diagonais proibidas (máx = 0)
    dezenas_por_linha = []
    for r in range(6):
        dezenas_l = []
        for c in range(10):
            n = r * 10 + c + 1
            prop = PROPS[n]
            # Descarta dezena se sua coluna ou diagonal estiver travada em 0
            if cfg["colunas"][prop["c"]][1] == 0:
                continue
            if cfg["diag_cresc"][prop["dc"]][1] == 0:
                continue
            if cfg["diag_decresc"][prop["dd"]][1] == 0:
                continue
            dezenas_l.append(n)
        dezenas_por_linha.append(dezenas_l)

    # 2. Partições válidas entre as 6 linhas
    particoes = gerar_particoes_linha(cfg["linhas"], alvo=6)
    
    if not particoes:
        container_status.error("Combinação impossível: Os limites mínimos e máximos das linhas não somam 6.")
        return []

    # 3. Calcula o total exato de combinações que serão geradas
    import math
    total_combinacoes = 0
    particoes_viaveis = []
    for part in particoes:
        possivel = True
        comb_part = 1
        for r in range(6):
            n_disp = len(dezenas_por_linha[r])
            k = part[r]
            if k > n_disp:
                possivel = False
                break
            comb_part *= math.comb(n_disp, k)
        if possivel and comb_part > 0:
            particoes_viaveis.append(part)
            total_combinacoes += comb_part

    if total_combinacoes == 0:
        container_status.error("Nenhuma combinação viável com as restrições individuais escolhidas.")
        return []

    container_status.write(
        f"📊 **Plano de Varredura:** {len(particoes_viaveis)} partições de linhas identificadas. "
        f"Universo exato a inspecionar: **{total_combinacoes:,} jogos**."
    )

    # 4. Loop de Execução com a Linha de Acompanhamento de Serviço
    jogos_aprovados = []
    testadas = 0
    lote_update = max(1000, total_combinacoes // 80)
    
    cfg_col = cfg["colunas"]
    cfg_dc = cfg["diag_cresc"]
    cfg_dd = cfg["diag_decresc"]
    soma_min, soma_max = cfg["faixa_soma"]
    pares_aceitos = cfg["pares_aceitos"]
    primos_aceitos = cfg["primos_aceitos"]
    moldura_aceita = cfg["moldura_aceita"]

    for part in particoes_viaveis:
        geradores_linha = [combinations(dezenas_por_linha[r], part[r]) for r in range(6)]
        
        for combinacao_fatiada in product(*geradores_linha):
            testadas += 1
            
            # Reconstrói a aposta de 6 números
            jogo = []
            for pedaco in combinacao_fatiada:
                jogo.extend(pedaco)

            # Teste 1: Soma Geral
            soma_j = sum(jogo)
            if not (soma_min <= soma_j <= soma_max):
                continue

            # Teste 2: Primos
            primos_cnt = sum(1 for n in jogo if PROPS[n]["is_primo"])
            if primos_cnt not in primos_aceitos:
                continue

            # Teste 3: Pares
            pares_cnt = sum(1 for n in jogo if PROPS[n]["is_par"])
            if pares_cnt not in pares_aceitos:
                continue

            # Teste 4: Moldura
            moldura_cnt = sum(1 for n in jogo if PROPS[n]["is_moldura"])
            if moldura_cnt not in moldura_aceita:
                continue

            # Teste 5: Colunas Individuais
            cols_count = [0] * 10
            dc_count = [0] * 10
            dd_count = [0] * 10
            valido = True

            for n in jogo:
                prop = PROPS[n]
                c_idx = prop["c"]
                cols_count[c_idx] += 1
                if cols_count[c_idx] > cfg_col[c_idx][1]:
                    valido = False
                    break
                
                dc_idx = prop["dc"]
                dc_count[dc_idx] += 1
                if dc_count[dc_idx] > cfg_dc[dc_idx][1]:
                    valido = False
                    break

                dd_idx = prop["dd"]
                dd_count[dd_idx] += 1
                if dd_count[dd_idx] > cfg_dd[dd_idx][1]:
                    valido = False
                    break

            if not valido:
                continue

            # Verifica mínimos por coluna e diagonal
            for c in range(10):
                if cols_count[c] < cfg_col[c][0]:
                    valido = False
                    break
            if not valido:
                continue

            for d in range(10):
                if dc_count[d] < cfg_dc[d][0] or dd_count[d] < cfg_dd[d][0]:
                    valido = False
                    break
            if not valido:
                continue

            jogos_aprovados.append(jogo)

            # Atualização visual da Linha de Serviço
            if testadas % lote_update == 0:
                prog = testadas / total_combinacoes
                bar_progresso.progress(prog)
                delta_t = max(0.001, time.time() - t_inicio)
                velocidade = int(testadas / delta_t)
                ticker_metricas.markdown(
                    f"**Linha de Serviço:** `{testadas:,}` de `{total_combinacoes:,}` ({prog*100:.1f}%) | "
                    f"Aprovados: `{len(jogos_aprovados):,}` | "
                    f"Velocidade: `{velocidade:,} comb/s` | Tempo: `{delta_t:.2f}s`"
                )

    bar_progresso.progress(1.0)
    return jogos_aprovados

# ==============================================================================
# INICIALIZAÇÃO DE ESTADO
# ==============================================================================
if "historico" not in st.session_state:
    st.session_state.historico = [list(j) for j in FALLBACK_MEGASENA]
    st.session_state.origem = "Base Local Offline (Carregamento Rápido)"

if "jogos_aprovados" not in st.session_state:
    st.session_state.jogos_aprovados = []

# ==============================================================================
# CABEÇALHO & ABAS PRINCIPAIS
# ==============================================================================
st.title("🍀 MEGA60: Seleção Individual de Linhas, Colunas e Diagonais")
st.caption("Filtros Granulares Elemento por Elemento • Varredura Completa com Acompanhamento de Serviço")

tab_config, tab_volante, tab_historico = st.tabs([
    "🎛️ Configuração Individual dos Quadros",
    "🗺️ Volante Visual & Raio-X do Jogo",
    "📊 Histórico & Conexão Caixa"
])

# ==============================================================================
# ABA 1: CONFIGURAÇÃO INDIVIDUAL
# ==============================================================================
with tab_config:
    st.markdown("### 🎛️ Defina a Quantidade Exata para Cada Linha, Coluna e Diagonal")
    
    # QUADRO 1: LINHAS INDIVIDUAIS (L01 a L06)
    with st.container(border=True):
        st.markdown("#### 1️⃣ Configuração Individual das 6 Linhas")
        st.caption("Defina individualmente quantas dezenas cada linha deve conter (ex: Linha 1 = 2 números, Linha 4 = 1 número).")
        cols_l = st.columns(6)
        limites_linhas = []
        opcoes_nomes = list(OPCOES_QUANTIDADE.keys())
        
        for r in range(6):
            with cols_l[r]:
                escolha_l = st.selectbox(
                    f"Linha {r+1:02d} ({r*10+1:02d} a {r*10+10:02d})",
                    opcoes_nomes,
                    index=2,  # Padrão: "Exatamente 1"
                    key=f"sel_l_{r}"
                )
                limites_linhas.append(OPCOES_QUANTIDADE[escolha_l])

    # QUADRO 2: COLUNAS INDIVIDUAIS (C01 a C10)
    with st.container(border=True):
        st.markdown("#### 2️⃣ Configuração Individual das 10 Colunas")
        st.caption("Defina se uma coluna deve ter 0, 1, 2, 3 ou quantidade livre de dezenas.")
        cols_c_up = st.columns(5)
        cols_c_dw = st.columns(5)
        limites_colunas = []

        for c in range(10):
            alvo_col = cols_c_up[c] if c < 5 else cols_c_dw[c - 5]
            with alvo_col:
                terminacao = "0" if c == 9 else str(c + 1)
                escolha_c = st.selectbox(
                    f"Coluna {c+1:02d} (Final {terminacao})",
                    opcoes_nomes,
                    index=6,  # Padrão: "0 ou 1"
                    key=f"sel_c_{c}"
                )
                limites_colunas.append(OPCOES_QUANTIDADE[escolha_c])

    # QUADRO 3: DIAGONAIS INDIVIDUAIS (CRESCENTES E DECRESCENTES)
    c_diag1, c_diag2 = st.columns(2)
    with c_diag1:
        with st.container(border=True):
            st.markdown("#### 3️⃣ Diagonais Crescentes (DC01 a DC10 /)")
            with st.expander("Abrir Controle das 10 Diagonais Crescentes", expanded=False):
                limites_dc = []
                for d in range(10):
                    escolha_dc = st.selectbox(
                        f"Diag Crescente DC{d+1:02d}",
                        opcoes_nomes,
                        index=6,  # "0 ou 1"
                        key=f"sel_dc_{d}"
                    )
                    limites_dc.append(OPCOES_QUANTIDADE[escolha_dc])
    with c_diag2:
        with st.container(border=True):
            st.markdown("#### 4️⃣ Diagonais Decrescentes (DD01 a DD10 \\)")
            with st.expander("Abrir Controle das 10 Diagonais Decrescentes", expanded=False):
                limites_dd = []
                for d in range(10):
                    escolha_dd = st.selectbox(
                        f"Diag Decrescente DD{d+1:02d}",
                        opcoes_nomes,
                        index=6,  # "0 ou 1"
                        key=f"sel_dd_{d}"
                    )
                    limites_dd.append(OPCOES_QUANTIDADE[escolha_dd])

    # QUADRO 4: PRIMOS, PARES, MOLDURA E SOMA
    with st.container(border=True):
        st.markdown("#### 5️⃣ Primos, Pares, Ímpares, Moldura e Faixa de Soma")
        c_p1, c_p2, c_p3, c_p4 = st.columns(4)
        with c_p1:
            primos_sel = st.multiselect("Quantidade de Primos:", [0, 1, 2, 3, 4, 5, 6], default=[1, 2])
        with c_p2:
            opcoes_par = {
                "3P / 3I": 3, "2P / 4I": 2, "4P / 2I": 4, 
                "1P / 5I": 1, "5P / 1I": 5, "0P / 6I": 0, "6P / 0I": 6
            }
            par_sel = st.multiselect("Pares / Ímpares:", list(opcoes_par.keys()), default=["3P / 3I", "2P / 4I", "4P / 2I"])
            pares_valores = {opcoes_par[k] for k in par_sel}
        with c_p3:
            moldura_sel = st.multiselect("Dezenas na Moldura:", [0, 1, 2, 3, 4, 5, 6], default=[2, 3, 4])
        with c_p4:
            faixa_soma = st.slider("Faixa de Soma:", 50, 320, (110, 240))

    # Consolida a configuração
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

    # ==============================================================================
    # LINHA DE ACOMPANHAMENTO DE SERVIÇO EM TEMPO REAL
    # ==============================================================================
    st.markdown("### 📡 Linha de Acompanhamento de Serviço")
    placeholder_metricas = st.empty()
    barra_progresso = st.progress(0, text="Aguardando início do serviço...")

    if st.button("🚀 Iniciar Varredura com Parâmetros Granulares", use_container_width=True):
        if not primos_sel:
            st.error("Selecione pelo menos uma quantidade aceita de Primos.")
        elif not par_sel:
            st.error("Selecione pelo menos uma proporção de Pares/Ímpares.")
        elif not moldura_sel:
            st.error("Selecione pelo menos uma quantidade de Moldura.")
        else:
            with st.status("🛠️ Processando Varredura Granular...", expanded=True) as status_box:
                t0 = time.time()
                resultados = motor_varredura_individual(
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
                        label=f"✅ Serviço Finalizado com Sucesso! {total_gerado:,} jogos encontrados em {t_fim:.2f}s.",
                        state="complete",
                        expanded=False
                    )
                else:
                    status_box.update(
                        label=f"⚠️ Processamento finalizado em {t_fim:.2f}s, mas nenhuma aposta atende todos os critérios configurados.",
                        state="error",
                        expanded=True
                    )

    # Exportação e Visualização
    if st.session_state.jogos_aprovados:
        qtd_aprov = len(st.session_state.jogos_aprovados)
        st.success(f"🎯 **Total Aprovado:** {qtd_aprov:,} apostas prontas para download!")
        
        txt_saida = "\n".join([" ".join([f"{n:02d}" for n in j]) for j in st.session_state.jogos_aprovados])
        
        c_btn, c_qtd = st.columns([3, 1])
        with c_btn:
            st.download_button(
                "📥 Baixar Arquivo de Jogos (.TXT)",
                data=txt_saida,
                file_name=f"mega60_apostas_granulares_{qtd_aprov}.txt",
                mime="text/plain",
                use_container_width=True
            )
        with c_qtd:
            st.metric("Total em Memória", f"{qtd_aprov:,}")

        amostra = min(qtd_aprov, 50)
        with st.expander(f"Visualizar Conferência Inicial ({amostra} de {qtd_aprov:,})", expanded=True):
            for i, j in enumerate(st.session_state.jogos_aprovados[:amostra]):
                p = sum(1 for n in j if PROPS[n]["is_primo"])
                par = sum(1 for n in j if PROPS[n]["is_par"])
                mold = sum(1 for n in j if PROPS[n]["is_moldura"])
                st.markdown(
                    f"**Jogo #{i+1:04d}:** `{' - '.join([f'{n:02d}' for n in j])}` | "
                    f"**{par}P/{6-par}I** | **{p} Primos** | **{mold} Moldura** | Soma: `{sum(j)}`"
                )

# ==============================================================================
# ABA 2: VOLANTE VISUAL & RAIO-X DO JOGO SELECIONADO
# ==============================================================================
with tab_volante:
    st.subheader("Dissecação da Cartela Oficial")
    if st.session_state.jogos_aprovados:
        sel_idx = st.slider("Escolha a aposta para inspecionar:", 1, len(st.session_state.jogos_aprovados), 1)
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
                st.markdown("#### 🔬 Raio-X Detalhado do Jogo")
                
                cnt_linhas = Counter(PROPS[n]["r"] + 1 for n in jogo_ativo)
                cnt_colunas = Counter(PROPS[n]["c"] + 1 for n in jogo_ativo)
                cnt_dc = Counter(PROPS[n]["dc"] + 1 for n in jogo_ativo)
                cnt_dd = Counter(PROPS[n]["dd"] + 1 for n in jogo_ativo)

                st.markdown("**Linhas:** " + " • ".join([f"L{k}: `{v}x`" for k, v in sorted(cnt_linhas.items())]))
                st.markdown("**Colunas:** " + " • ".join([f"C{k:02d}: `{v}x`" for k, v in sorted(cnt_colunas.items())]))
                st.markdown("**Diagonais Cresc. (D01-D10):** " + " • ".join([f"DC{k:02d}: `{v}x`" for k, v in sorted(cnt_dc.items())]))
                st.markdown("**Diagonais Decresc. (D01-D10):** " + " • ".join([f"DD{k:02d}: `{v}x`" for k, v in sorted(cnt_dd.items())]))
                
                pr = sum(1 for n in jogo_ativo if PROPS[n]["is_primo"])
                pa = sum(1 for n in jogo_ativo if PROPS[n]["is_par"])
                mo = sum(1 for n in jogo_ativo if PROPS[n]["is_moldura"])
                
                st.divider()
                st.markdown(f"**Pares/Ímpares:** `{pa}P / {6-pa}I` | **Primos:** `{pr}` | **Moldura:** `{mo}` | **Soma:** `{sum(jogo_ativo)}`")
    else:
        st.info("Execute a varredura na primeira aba para inspecionar no volante.")

# ==============================================================================
# ABA 3: HISTÓRICO E CONEXÃO CAIXA
# ==============================================================================
with tab_historico:
    st.subheader("Base de Sorteios Oficiais")
    st.write(f"Concursos ativos em memória: **{len(st.session_state.historico)}** ({st.session_state.origem})")
    
    if st.button("🌐 Sincronizar Histórico com a Caixa Agora"):
        with st.spinner("Conectando ao servidor oficial da Caixa..."):
            url = "https://servicebus2.caixa.gov.br/portaldeloterias/api/megasena"
            headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
            try:
                r = requests.get(url, headers=headers, timeout=5)
                if r.status_code == 200:
                    ult = r.json()
                    st.success(f"Conexão bem-sucedida! Último concurso oficial: #{ult['numero']}")
                else:
                    st.warning("Servidor da Caixa indisponível no momento.")
            except Exception as e:
                st.error(f"Erro ao conectar: {e}")
