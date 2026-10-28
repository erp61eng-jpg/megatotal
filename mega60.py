import streamlit as st
import streamlit.components.v1 as components
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from itertools import combinations, permutations
from collections import Counter
import time

st.set_page_config(
    page_title="MEGA60 - Laboratório de Filtros Estruturais",
    page_icon="🍀",
    layout="wide"
)

TOTAL_NUMS = 60
TAMANHO_JOGO = 6
PRIMOS_MEGASENA = {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59}

# 28 Dezenas da Moldura (Bordas externas da matriz 6x10)
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
# MAPEAMENTO DA MATRIZ 6x10
# ==============================================================================
def obter_indices_matriz(n):
    """Retorna (linha_0_a_5, coluna_0_a_9, diag_cresc_1_a_10, diag_decresc_1_a_10)"""
    r = (n - 1) // 10
    c = (n - 1) % 10
    dc = ((c + r) % 10) + 1
    dd = ((c - r) % 10) + 1
    return r, c, dc, dd

# Pré-computação das propriedades de cada dezena (1 a 60)
PROPRIEDADES_DEZENAS = {}
for n in range(1, 61):
    r, c, dc, dd = obter_indices_matriz(n)
    PROPRIEDADES_DEZENAS[n] = {
        "linha": r + 1,
        "coluna": c + 1,
        "diag_cresc": dc,
        "diag_decresc": dd,
        "is_par": (n % 2 == 0),
        "is_primo": (n in PRIMOS_MEGASENA),
        "is_moldura": (n in MOLDURA_SET)
    }

# ==============================================================================
# MOTOR MATEMÁTICO COM ACOMPANHAMENTO DE SERVIÇO EM TEMPO REAL
# ==============================================================================
def validar_jogo_personalizado(jogo, cfg):
    # 1. Soma
    soma = sum(jogo)
    if not (cfg["soma_min"] <= soma <= cfg["soma_max"]):
        return False
        
    # 2. Primos
    qtd_primos = sum(1 for n in jogo if PROPRIEDADES_DEZENAS[n]["is_primo"])
    if qtd_primos not in cfg["primos_escolhidos"]:
        return False

    # 3. Pares / Ímpares
    qtd_pares = sum(1 for n in jogo if PROPRIEDADES_DEZENAS[n]["is_par"])
    if qtd_pares not in cfg["pares_escolhidos"]:
        return False

    # 4. Moldura
    qtd_moldura = sum(1 for n in jogo if PROPRIEDADES_DEZENAS[n]["is_moldura"])
    if qtd_moldura not in cfg["moldura_escolhidos"]:
        return False

    # 5. Linhas, Colunas e Diagonais
    linhas = [0] * 7
    colunas = [0] * 11
    diag_cresc = [0] * 11
    diag_decresc = [0] * 11

    for n in jogo:
        prop = PROPRIEDADES_DEZENAS[n]
        l = prop["linha"]
        c = prop["coluna"]
        dc = prop["diag_cresc"]
        dd = prop["diag_decresc"]

        # Se cair em linha/coluna/diagonal desativada pelo usuário
        if l not in cfg["linhas_ativas"]:
            return False
        if c not in cfg["colunas_ativas"]:
            return False
        if dc not in cfg["diag_cresc_ativas"]:
            return False
        if dd not in cfg["diag_decresc_ativas"]:
            return False

        linhas[l] += 1
        if linhas[l] > cfg["max_por_linha"]:
            return False

        colunas[c] += 1
        if colunas[c] > cfg["max_por_coluna"]:
            return False

        diag_cresc[dc] += 1
        if diag_cresc[dc] > cfg["max_por_diag_cresc"]:
            return False

        diag_decresc[dd] += 1
        if diag_decresc[dd] > cfg["max_por_diag_decresc"]:
            return False

    # Se usuário exigiu que TODAS as linhas ativas tenham pelo menos 1 dezena
    if cfg["exigir_linhas_marcadas"]:
        for l in cfg["linhas_ativas"]:
            if linhas[l] == 0:
                return False

    return True

def executar_servico_varredura(cfg, progress_bar, status_monitor, metrics_placeholder):
    """Executa a filtragem emitindo métricas e progresso no painel de serviço."""
    t_inicio = time.time()
    
    # Pré-seleção atômica: descarta dezenas que violam as regras básicas
    dezenas_candidatas = [
        n for n in range(1, 61)
        if PROPRIEDADES_DEZENAS[n]["linha"] in cfg["linhas_ativas"]
        and PROPRIEDADES_DEZENAS[n]["coluna"] in cfg["colunas_ativas"]
        and PROPRIEDADES_DEZENAS[n]["diag_cresc"] in cfg["diag_cresc_ativas"]
        and PROPRIEDADES_DEZENAS[n]["diag_decresc"] in cfg["diag_decresc_ativas"]
    ]

    if len(dezenas_candidatas) < 6:
        status_monitor.error(f"Filtro muito restritivo: apenas {len(dezenas_candidatas)} dezenas atendem aos critérios. São necessárias pelo menos 6.")
        return []

    # Caso especial ultrarrápido: Exatamente 1 por Linha e 1 por Coluna (com 6 linhas ativas)
    if (cfg["max_por_linha"] == 1 and cfg["max_por_coluna"] == 1 
            and len(cfg["linhas_ativas"]) == 6 and cfg["exigir_linhas_marcadas"]):
        
        status_monitor.write("⚡ Modo Determinístico MEGA60 Ativado: Varrendo permutações perfeitas 1x1...")
        
        cols_pares = [c - 1 for c in cfg["colunas_ativas"] if c % 2 == 0]
        cols_impares = [c - 1 for c in cfg["colunas_ativas"] if c % 2 != 0]
        linhas_indices = [l - 1 for l in sorted(list(cfg["linhas_ativas"]))]
        
        aprovados = []
        total_estimado = 151200
        testadas = 0
        lote_update = 5000

        for q_par in cfg["pares_escolhidos"]:
            q_impar = 6 - q_par
            if len(cols_pares) < q_par or len(cols_impares) < q_impar:
                continue

            for linhas_par in combinations(linhas_indices, q_par):
                linhas_par_set = set(linhas_par)
                linhas_impar = [l for l in linhas_indices if l not in linhas_par_set]

                for perm_par in permutations(cols_pares, q_par):
                    for perm_impar in permutations(cols_impares, q_impar):
                        testadas += 1
                        colunas = [0] * 6
                        for idx, l in enumerate(linhas_par):
                            colunas[l] = perm_par[idx]
                        for idx, l in enumerate(linhas_impar):
                            colunas[l] = perm_impar[idx]

                        jogo = [r * 10 + colunas[r] + 1 for r in range(6)]
                        if validar_jogo_personalizado(jogo, cfg):
                            aprovados.append(jogo)

                        if testadas % lote_update == 0:
                            progresso = min(1.0, testadas / total_estimado)
                            progress_bar.progress(progresso)
                            tempo_decorrido = max(0.001, time.time() - t_inicio)
                            vel = int(testadas / tempo_decorrido)
                            metrics_placeholder.markdown(
                                f"**Linha de Serviço:** `{testadas:,}` testadas | "
                                f"`{len(aprovados):,}` aprovadas | "
                                f"Velocidade: `{vel:,} comb/s` | Tempo: `{tempo_decorrido:.2f}s`"
                            )

        progress_bar.progress(1.0)
        return aprovados

    # Modo Geral Combinatório sobre as dezenas candidatas
    total_combinacoes = 1
    # Cálculo de combinações C(len(dezenas_candidatas), 6)
    n_cand = len(dezenas_candidatas)
    import math
    total_combinacoes = math.comb(n_cand, 6)
    status_monitor.write(f"🔍 Dezenas qualificadas: **{n_cand} de 60** | Universo a varrer: **{total_combinacoes:,} jogos**")

    aprovados = []
    testadas = 0
    lote_update = max(1000, total_combinacoes // 100)

    for comb in combinations(dezenas_candidatas, 6):
        testadas += 1
        if validar_jogo_personalizado(comb, cfg):
            aprovados.append(list(comb))

        if testadas % lote_update == 0:
            prog = testadas / total_combinacoes
            progress_bar.progress(prog)
            t_passado = max(0.001, time.time() - t_inicio)
            vel = int(testadas / t_passado)
            metrics_placeholder.markdown(
                f"**Linha de Serviço:** `{testadas:,}` de `{total_combinacoes:,}` ({prog*100:.1f}%) | "
                f"`{len(aprovados):,}` aprovadas | "
                f"Velocidade: `{vel:,} comb/s` | Tempo: `{t_passado:.2f}s`"
            )

    progress_bar.progress(1.0)
    return aprovados

# ==============================================================================
# INICIALIZAÇÃO E HISTÓRICO
# ==============================================================================
if "historico" not in st.session_state:
    st.session_state.historico = [list(j) for j in FALLBACK_MEGASENA]
    st.session_state.origem = "Base Local Offline (Carregamento Imediato)"

if "jogos_aprovados" not in st.session_state:
    st.session_state.jogos_aprovados = []

# ==============================================================================
# INTERFACE PRINCIPAL
# ==============================================================================
st.title("🍀 MEGA60: Painel de Controle e Seleção dos 7 Quadros")
st.caption("Seleção individual de Linhas, Colunas, Diagonais, Paridade, Primos e Moldura • Acompanhamento em Tempo Real")

tab_quadros, tab_volante, tab_historico = st.tabs([
    "🎛️ Configuração dos Quadros & Varredura",
    "🗺️ Volante Visual & Raio-X",
    "📊 Histórico & Concursos Caixa"
])

# ==============================================================================
# ABA 1: CONFIGURAÇÃO INDIVIDUAL DOS QUADROS
# ==============================================================================
with tab_quadros:
    st.markdown("### 🎛️ Escolha Exatamente Quais Elementos Devem Participar")

    c_esq, c_dir = st.columns(2)

    with c_esq:
        # QUADRO 1: LINHAS
        with st.container(border=True):
            st.markdown("#### 1️⃣ Quadro: Linhas (01 a 06)")
            col_l1, col_l2 = st.columns([3, 2])
            with col_l1:
                linhas_sel = st.multiselect(
                    "Quais linhas podem conter dezenas?",
                    options=[1, 2, 3, 4, 5, 6],
                    default=[1, 2, 3, 4, 5, 6],
                    format_func=lambda x: f"Linha {x:02d}"
                )
            with col_l2:
                max_l = st.number_input("Máximo por Linha:", min_value=1, max_value=6, value=1)
                exigir_linhas = st.checkbox("Exigir pelo menos 1 dezena em cada linha marcada", value=True)

        # QUADRO 2: COLUNAS
        with st.container(border=True):
            st.markdown("#### 2️⃣ Quadro: Colunas (01 a 10)")
            colunas_sel = st.multiselect(
                "Quais colunas podem conter dezenas?",
                options=list(range(1, 11)),
                default=list(range(1, 11)),
                format_func=lambda x: f"Coluna {x:02d}"
            )
            max_c = st.slider("Máximo de Dezenas por Coluna:", 1, 6, 1)

        # QUADRO 3: PARES E ÍMPARES
        with st.container(border=True):
            st.markdown("#### 3️⃣ Quadro: Pares & Ímpares")
            st.caption("Marque as divisões permitidas:")
            opcoes_paridade = {
                "3 Pares / 3 Ímpares": 3,
                "4 Pares / 2 Ímpares": 4,
                "2 Pares / 4 Ímpares": 2,
                "5 Pares / 1 Ímpar": 5,
                "1 Par / 5 Ímpares": 1,
                "6 Pares / 0 Ímpares": 6,
                "0 Pares / 6 Ímpares": 0
            }
            paridades_sel = st.multiselect(
                "Combinações de Paridade Aceitas:",
                options=list(opcoes_paridade.keys()),
                default=["3 Pares / 3 Ímpares", "4 Pares / 2 Ímpares", "2 Pares / 4 Ímpares"]
            )
            pares_permitidos = {opcoes_paridade[k] for k in paridades_sel}

    with c_dir:
        # QUADRO 4: DIAGONAIS CRESCENTES (D01 a D10)
        with st.container(border=True):
            st.markdown("#### 4️⃣ Quadro: Diagonais Crescentes (01 a 10)")
            diag_cresc_sel = st.multiselect(
                "Quais diagonais crescentes (inclinadas /) estão liberadas?",
                options=list(range(1, 11)),
                default=list(range(1, 11)),
                format_func=lambda x: f"Diag Crescente {x:02d}"
            )
            max_dc = st.slider("Máximo por Diagonal Crescente:", 1, 6, 1)

        # QUADRO 5: DIAGONAIS DECRESCENTES (D01 a D10)
        with st.container(border=True):
            st.markdown("#### 5️⃣ Quadro: Diagonais Decrescentes (01 a 10)")
            diag_decresc_sel = st.multiselect(
                "Quais diagonais decrescentes (inclinadas \\) estão liberadas?",
                options=list(range(1, 11)),
                default=list(range(1, 11)),
                format_func=lambda x: f"Diag Decrescente {x:02d}"
            )
            max_dd = st.slider("Máximo por Diagonal Decrescente:", 1, 6, 1)

        # QUADRO 6 & 7: PRIMOS, MOLDURA E SOMA
        with st.container(border=True):
            st.markdown("#### 6️⃣ e 7️⃣ Quadros: Primos, Moldura & Soma")
            c_p, c_m = st.columns(2)
            with c_p:
                primos_sel = st.multiselect(
                    "Qtd de Primos Aceita:",
                    options=[0, 1, 2, 3, 4, 5, 6],
                    default=[1, 2]
                )
            with c_m:
                moldura_sel = st.multiselect(
                    "Qtd na Moldura Aceita:",
                    options=[0, 1, 2, 3, 4, 5, 6],
                    default=[2, 3, 4]
                )
            faixa_soma = st.slider("Faixa de Soma Total:", 50, 320, (110, 240))

    # Consolidação do dicionário de configuração
    config_varredura = {
        "linhas_ativas": set(linhas_sel),
        "max_por_linha": max_l,
        "exigir_linhas_marcadas": exigir_linhas,
        "colunas_ativas": set(colunas_sel),
        "max_por_coluna": max_c,
        "diag_cresc_ativas": set(diag_cresc_sel),
        "max_por_diag_cresc": max_dc,
        "diag_decresc_ativas": set(diag_decresc_sel),
        "max_por_diag_decresc": max_dd,
        "pares_escolhidos": pares_permitidos,
        "primos_escolhidos": set(primos_sel),
        "moldura_escolhidos": set(moldura_sel),
        "soma_min": faixa_soma[0],
        "soma_max": faixa_soma[1]
    }

    st.divider()

    # ==============================================================================
    # LINHA DE ACOMPANHAMENTO DE SERVIÇO (MONITOR DE PROGRESSO)
    # ==============================================================================
    st.markdown("### 📡 Linha de Acompanhamento de Serviço")
    placeholder_metricas = st.empty()
    barra_progresso = st.progress(0, text="Aguardando comando de execução...")

    btn_iniciar = st.button("🚀 Iniciar Varredura com Parâmetros Selecionados", use_container_width=True)

    if btn_iniciar:
        if not linhas_sel or not colunas_sel or not diag_cresc_sel or not diag_decresc_sel:
            st.error("Erro: Você precisa selecionar pelo menos 1 item em cada quadro (Linhas, Colunas e Diagonais).")
        elif not paridades_sel:
            st.error("Erro: Selecione pelo menos uma combinação de Pares / Ímpares.")
        elif not primos_sel:
            st.error("Erro: Selecione pelo menos uma quantidade de Primos.")
        elif not moldura_sel:
            st.error("Erro: Selecione pelo menos uma quantidade de Moldura.")
        else:
            with st.status("🛠️ Executando Serviço de Filtragem Combinatória...", expanded=True) as status_box:
                t_comeco = time.time()
                resultados = executar_servico_varredura(
                    config_varredura, 
                    barra_progresso, 
                    status_box, 
                    placeholder_metricas
                )
                t_total = time.time() - t_comeco
                
                st.session_state.jogos_aprovados = resultados
                qtd = len(resultados)
                
                if qtd > 0:
                    status_box.update(
                        label=f"✅ Serviço Concluído! {qtd:,} apostas aprovadas em {t_total:.2f} segundos.", 
                        state="complete", 
                        expanded=False
                    )
                else:
                    status_box.update(
                        label=f"⚠️ Concluído em {t_total:.2f}s, porém nenhuma aposta satisfez todos os filtros simultaneamente.", 
                        state="error", 
                        expanded=True
                    )

    # Exibição dos resultados e download
    if st.session_state.jogos_aprovados:
        qtd_total = len(st.session_state.jogos_aprovados)
        st.success(f"🎯 **Varredura Finalizada:** Exatamente **{qtd_total:,} jogos** prontos para exportação!")
        
        txt_conteudo = "\n".join([" ".join([f"{n:02d}" for n in j]) for j in st.session_state.jogos_aprovados])
        
        c_btn, c_cont = st.columns([3, 1])
        with c_btn:
            st.download_button(
                "📥 Baixar Arquivo Completo (.TXT)",
                data=txt_conteudo,
                file_name=f"mega60_selecao_personalizada_{qtd_total}.txt",
                mime="text/plain",
                use_container_width=True
            )
        with c_cont:
            st.metric("Total Aprovado", f"{qtd_total:,}")

        amostra = min(qtd_total, 50)
        with st.expander(f"Visualizar Primeiras Apostas ({amostra} de {qtd_total:,})", expanded=True):
            for i, j in enumerate(st.session_state.jogos_aprovados[:amostra]):
                p = sum(1 for n in j if PROPRIEDADES_DEZENAS[n]["is_primo"])
                par = sum(1 for n in j if PROPRIEDADES_DEZENAS[n]["is_par"])
                mold = sum(1 for n in j if PROPRIEDADES_DEZENAS[n]["is_moldura"])
                nums = " - ".join([f"{n:02d}" for n in j])
                st.markdown(f"**Jogo #{i+1:04d}:** `{nums}` | {par}P/{6-par}I | {p} Primos | {mold} Moldura | Soma: {sum(j)}")

# ==============================================================================
# ABA 2: VOLANTE VISUAL & RAIO-X DO JOGO
# ==============================================================================
with tab_volante:
    st.subheader("Dissecação da Cartela e Validação Estrutural")
    if st.session_state.jogos_aprovados:
        idx_sel = st.slider("Selecione a aposta para visualizar:", 1, len(st.session_state.jogos_aprovados), 1)
        jogo_ativo = st.session_state.jogos_aprovados[idx_sel - 1]
        marcadas = set(jogo_ativo)

        col_cartela, col_raiox = st.columns([1, 1])
        with col_cartela:
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
            <style>*{{box-sizing:border-box;}}body{{margin:0;padding:0;display:flex;justify-content:center;font-family:sans-serif;background:transparent;}}
            .box{{background:#fff;border:2px solid #16a34a;border-radius:12px;padding:12px;box-shadow:0 4px 12px rgba(22,163,74,0.12);width:fit-content;}}
            .grid{{display:grid;grid-template-columns:repeat(10,36px);gap:5px;}}</style></head><body>
            <div class="box"><div style="font-weight:800;font-size:14px;margin-bottom:10px;color:#15803d;text-align:center;">Jogo #{idx_sel:04d}: {' - '.join([f'{n:02d}' for n in jogo_ativo])}</div>
            <div class="grid">{celulas}</div></div></body></html>
            """
            components.html(html_cartela, height=330, scrolling=False)

        with col_raiox:
            with st.container(border=True):
                st.markdown("#### 🔬 Raio-X dos 7 Quadros para este Jogo")
                linhas_usadas = [PROPRIEDADES_DEZENAS[n]["linha"] for n in jogo_ativo]
                colunas_usadas = [PROPRIEDADES_DEZENAS[n]["coluna"] for n in jogo_ativo]
                dc_usadas = [PROPRIEDADES_DEZENAS[n]["diag_cresc"] for n in jogo_ativo]
                dd_usadas = [PROPRIEDADES_DEZENAS[n]["diag_decresc"] for n in jogo_ativo]
                
                cnt_l = Counter(linhas_usadas)
                cnt_c = Counter(colunas_usadas)
                cnt_dc = Counter(dc_usadas)
                cnt_dd = Counter(dd_usadas)
                
                st.write(f"**Linhas Utilizadas:** " + " • ".join([f"L{k}: `{v}x`" for k, v in sorted(cnt_l.items())]))
                st.write(f"**Colunas Utilizadas:** " + " • ".join([f"C{k}: `{v}x`" for k, v in sorted(cnt_c.items())]))
                st.write(f"**Diag. Crescentes:** " + " • ".join([f"DC{k}: `{v}x`" for k, v in sorted(cnt_dc.items())]))
                st.write(f"**Diag. Decrescentes:** " + " • ".join([f"DD{k}: `{v}x`" for k, v in sorted(cnt_dd.items())]))
                
                p_c = sum(1 for n in jogo_ativo if PROPRIEDADES_DEZENAS[n]["is_primo"])
                par_c = sum(1 for n in jogo_ativo if PROPRIEDADES_DEZENAS[n]["is_par"])
                mold_c = sum(1 for n in jogo_ativo if PROPRIEDADES_DEZENAS[n]["is_moldura"])
                
                st.divider()
                st.markdown(f"**Pares/Ímpares:** `{par_c}P / {6-par_c}I` | **Primos:** `{p_c}` | **Moldura:** `{mold_c}` | **Soma:** `{sum(jogo_ativo)}`")
    else:
        st.info("Execute a varredura na primeira aba para inspecionar no volante.")

# ==============================================================================
# ABA 3: HISTÓRICO E ATUALIZAÇÃO
# ==============================================================================
with tab_historico:
    st.subheader("Base de Sorteios Oficiais")
    st.write(f"Concursos ativos em memória: **{len(st.session_state.historico)}** ({st.session_state.origem})")
    
    if st.button("🌐 Sincronizar Histórico com a Caixa Agora"):
        with st.spinner("Conectando ao servidor da Caixa..."):
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
                st.error(f"Não foi possível conectar: {e}")
