import streamlit as st
import streamlit.components.v1 as components
import requests
from itertools import combinations, product
from collections import Counter
import math
import time

st.set_page_config(
    page_title="MEGA60 - Laboratório Estrutural Granular",
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
# MOTOR COMBINATÓRIO COM DESDOBRAMENTO AUTOMÁTICO PARA 6 NÚMEROS
# ==============================================================================
def validar_jogo_6(jogo, cfg):
    """Testa se uma aposta final de 6 dezenas atende todos os critérios."""
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

    for n in jogo:
        p = PROPS[n]
        c_idx, dc_idx, dd_idx = p["c"], p["dc"], p["dd"]

        cols_count[c_idx] += 1
        if cols_count[c_idx] > cfg["colunas"][c_idx][1]:
            return False

        dc_count[dc_idx] += 1
        if dc_count[dc_idx] > cfg["diag_cresc"][dc_idx][1]:
            return False

        dd_count[dd_idx] += 1
        if dd_count[dd_idx] > cfg["diag_decresc"][dd_idx][1]:
            return False

    for c in range(10):
        if cols_count[c] < cfg["colunas"][c][0]:
            return False

    for d in range(10):
        if dc_count[d] < cfg["diag_cresc"][d][0] or dd_count[d] < cfg["diag_decresc"][d][0]:
            return False

    return True

def gerar_particoes(limites_linhas, alvo):
    """Calcula todas as distribuições de dezenas por linha que somam o valor alvo."""
    val_ranges = [list(range(limites_linhas[i][0], limites_linhas[i][1] + 1)) for i in range(6)]
    particoes = []
    
    def backtrack(idx, soma_acum, tupla_atual):
        if idx == 6:
            if soma_acum == alvo:
                particoes.append(tupla_atual)
            return
        min_restante = sum(limites_linhas[j][0] for j in range(idx + 1, 6))
        max_restante = sum(limites_linhas[j][1] for j in range(idx + 1, 6))
        for qtd in val_ranges[idx]:
            nova_soma = soma_acum + qtd
            if nova_soma + min_restante <= alvo <= nova_soma + max_restante:
                backtrack(idx + 1, nova_soma, tupla_atual + (qtd,))

    backtrack(0, 0, ())
    return particoes

def motor_executar_servico(cfg, bar_progresso, container_status, ticker_metricas):
    t_inicio = time.time()
    
    # 1. Filtra dezenas disponíveis por linha
    dezenas_por_linha = []
    for r in range(6):
        dezenas_l = []
        for c in range(10):
            n = r * 10 + c + 1
            prop = PROPS[n]
            if cfg["colunas"][prop["c"]][1] == 0:
                continue
            if cfg["diag_cresc"][prop["dc"]][1] == 0:
                continue
            if cfg["diag_decresc"][prop["dd"]][1] == 0:
                continue
            dezenas_l.append(n)
        dezenas_por_linha.append(dezenas_l)

    # 2. Avalia a meta das linhas
    min_linhas = sum(l[0] for l in cfg["linhas"])
    max_linhas = sum(l[1] for l in cfg["linhas"])
    
    modo_desdobramento = False
    
    if min_linhas == max_linhas and min_linhas > 6:
        alvo_busca = min_linhas
        modo_desdobramento = True
        container_status.write(
            f"🔄 **Modo Desdobramento Ativado:** Sua seleção define grupos de **{alvo_busca} dezenas**. "
            f"O sistema irá gerar esses grupos estruturais e **desdobrá-los automaticamente em apostas oficiais de 6 dezenas**!"
        )
    else:
        alvo_busca = 6
        container_status.write("⚡ **Modo Direto Ativado:** Gerando combinações diretamente no formato oficial de 6 dezenas.")

    particoes = gerar_particoes(cfg["linhas"], alvo=alvo_busca)
    
    if not particoes:
        container_status.error(
            f"Não há como compor combinações com a configuração atual das linhas. "
            f"Ajuste os valores para permitir que as linhas somem pelo menos 6 dezenas."
        )
        return []

    particoes_viaveis = []
    total_estimado = 0
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
            total_estimado += comb_part

    if total_estimado == 0:
        container_status.error("Nenhuma dezena disponível atende às colunas e diagonais configuradas para essas linhas.")
        return []

    container_status.write(
        f"📊 **Plano de Varredura:** {len(particoes_viaveis)} partições de linhas identificadas. "
        f"Universo base a inspecionar: **{total_estimado:,} matrizes**."
    )

    jogos_6_finais = set()
    testadas = 0
    lote_update = max(1, min(1000, total_estimado // 50))

    for part in particoes_viaveis:
        geradores = [combinations(dezenas_por_linha[r], part[r]) for r in range(6)]
        
        for pedacos in product(*geradores):
            testadas += 1
            matriz_candidata = []
            for p in pedacos:
                matriz_candidata.extend(p)

            # Se for modo direto (6 dezenas)
            if not modo_desdobramento:
                if validar_jogo_6(matriz_candidata, cfg):
                    jogos_6_finais.add(tuple(sorted(matriz_candidata)))
            # Se for modo desdobramento (> 6 dezenas), desdobra a matriz em jogos de 6
            else:
                for sub_jogo in combinations(matriz_candidata, 6):
                    if validar_jogo_6(sub_jogo, cfg):
                        jogos_6_finais.add(tuple(sorted(sub_jogo)))

            if testadas % lote_update == 0:
                prog = testadas / total_estimado
                bar_progresso.progress(prog)
                delta_t = max(0.001, time.time() - t_inicio)
                velocidade = int(testadas / delta_t)
                ticker_metricas.markdown(
                    f"**Linha de Serviço:** `{testadas:,}` de `{total_estimado:,}` ({prog*100:.1f}%) | "
                    f"Apostas de 6 dezenas geradas: `{len(jogos_6_finais):,}` | "
                    f"Velocidade: `{velocidade:,} matrizes/s` | Tempo: `{delta_t:.2f}s`"
                )

    bar_progresso.progress(1.0)
    delta_final = max(0.001, time.time() - t_inicio)
    ticker_metricas.markdown(
        f"**Linha de Serviço:** `{testadas:,}` matrizes processadas | "
        f"Aprovados finais: `{len(jogos_6_finais):,}` jogos de 6 dezenas | "
        f"Tempo total: `{delta_final:.2f}s`"
    )
    
    return [list(j) for j in sorted(list(jogos_6_finais))]

# ==============================================================================
# INICIALIZAÇÃO
# ==============================================================================
if "historico" not in st.session_state:
    st.session_state.historico = [list(j) for j in FALLBACK_MEGASENA]
    st.session_state.origem = "Base Local Offline (Carregamento Imediato)"

if "jogos_aprovados" not in st.session_state:
    st.session_state.jogos_aprovados = []

# ==============================================================================
# INTERFACE PRINCIPAL
# ==============================================================================
st.title("🍀 MEGA60: Seleção Individual & Desdobrador Automático")
st.caption("Você define a estratégia das Linhas, Colunas e Diagonais • O sistema desdobra e entrega jogos de SEMPRE 6 Números")

tab_config, tab_volante, tab_historico = st.tabs([
    "🎛️ Configuração dos Quadros",
    "🗺️ Volante Visual & Raio-X",
    "📊 Histórico & Conexão Caixa"
])

with tab_config:
    st.markdown("### 🎛️ Defina as Quantidades Individuais para Cada Elemento")

    # QUADRO 1: LINHAS INDIVIDUAIS
    with st.container(border=True):
        st.markdown("#### 1️⃣ Configuração Individual das 6 Linhas")
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

        soma_min_linhas = sum(l[0] for l in limites_linhas)
        soma_max_linhas = sum(l[1] for l in limites_linhas)

        if soma_min_linhas == soma_max_linhas == 6:
            st.info("ℹ️ **Modo Direto:** Suas linhas somam exatamente 6. Cada combinação gerada formará 1 aposta direta.")
        elif soma_min_linhas == soma_max_linhas and soma_min_linhas > 6:
            st.success(
                f"🎯 **Desdobramento Automático Ativo:** Suas linhas definem uma matriz de **{soma_min_linhas} dezenas** "
                f"(ex.: 2-1-1-1-1-2). O sistema vai gerar essas matrizes e **desdobrá-las em apostas de 6 dezenas**."
            )
        elif soma_min_linhas <= 6 <= soma_max_linhas:
            st.info(f"ℹ️ **Modo Flexível:** As linhas permitem entre {soma_min_linhas} e {soma_max_linhas} dezenas. O sistema extrairá jogos de 6 dezenas respeitando esses limites.")
        else:
            st.warning(f"⚠️ A soma mínima configurada ({soma_min_linhas}) é menor que 6. O sistema buscará combinações válidas de 6 dezenas.")

    # QUADRO 2: COLUNAS INDIVIDUAIS
    with st.container(border=True):
        st.markdown("#### 2️⃣ Configuração Individual das 10 Colunas")
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

    # QUADRO 3: DIAGONAIS INDIVIDUAIS
    c_diag1, c_diag2 = st.columns(2)
    with c_diag1:
        with st.container(border=True):
            st.markdown("#### 3️⃣ Diagonais Crescentes (DC01 a DC10 /)")
            with st.expander("Abrir Controle das Diagonais Crescentes", expanded=False):
                limites_dc = []
                for d in range(10):
                    escolha_dc = st.selectbox(
                        f"Diag Crescente DC{d+1:02d}",
                        opcoes_nomes,
                        index=6,
                        key=f"sel_dc_{d}"
                    )
                    limites_dc.append(OPCOES_QUANTIDADE[escolha_dc])
    with c_diag2:
        with st.container(border=True):
            st.markdown("#### 4️⃣ Diagonais Decrescentes (DD01 a DD10 \\)")
            with st.expander("Abrir Controle das Diagonais Decrescentes", expanded=False):
                limites_dd = []
                for d in range(10):
                    escolha_dd = st.selectbox(
                        f"Diag Decrescente DD{d+1:02d}",
                        opcoes_nomes,
                        index=6,
                        key=f"sel_dd_{d}"
                    )
                    limites_dd.append(OPCOES_QUANTIDADE[escolha_dd])

    # QUADRO 4: PRIMOS, PARES, MOLDURA E SOMA
    with st.container(border=True):
        st.markdown("#### 5️⃣ Primos, Pares, Moldura e Faixa de Soma")
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
    barra_progresso = st.progress(0, text="Aguardando comando de execução...")

    if st.button("🚀 Processar Varredura e Desdobrar em Jogos de 6 Dezenas", use_container_width=True):
        if not primos_sel:
            st.error("Selecione pelo menos uma quantidade aceita de Primos.")
        elif not par_sel:
            st.error("Selecione pelo menos uma proporção de Pares/Ímpares.")
        elif not moldura_sel:
            st.error("Selecione pelo menos uma quantidade de Moldura.")
        else:
            with st.status("🛠️ Processando Motor Estrutural...", expanded=True) as status_box:
                t0 = time.time()
                resultados = motor_executar_servico(
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
                        label=f"✅ Serviço Finalizado! {total_gerado:,} apostas oficiais de 6 dezenas geradas em {t_fim:.2f}s.",
                        state="complete",
                        expanded=False
                    )
                else:
                    status_box.update(
                        label=f"⚠️ Finalizado em {t_fim:.2f}s, mas nenhuma aposta atendeu a todos os critérios simultaneamente.",
                        state="error",
                        expanded=True
                    )

    if st.session_state.jogos_aprovados:
        qtd_aprov = len(st.session_state.jogos_aprovados)
        st.success(f"🎯 **Total Aprovado:** {qtd_aprov:,} apostas oficiais de 6 dezenas prontas!")
        
        txt_saida = "\n".join([" ".join([f"{n:02d}" for n in j]) for j in st.session_state.jogos_aprovados])
        
        c_btn, c_qtd = st.columns([3, 1])
        with c_btn:
            st.download_button(
                "📥 Baixar Arquivo com Jogos de 6 Dezenas (.TXT)",
                data=txt_saida,
                file_name=f"mega60_jogos_6dezenas_{qtd_aprov}.txt",
                mime="text/plain",
                use_container_width=True
            )
        with c_qtd:
            st.metric("Apostas de 6 Números", f"{qtd_aprov:,}")

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
# ABA 2: VOLANTE VISUAL & RAIO-X
# ==============================================================================
with tab_volante:
    st.subheader("Dissecação da Cartela Oficial (Jogos de 6 Dezenas)")
    if st.session_state.jogos_aprovados:
        total_jogos = len(st.session_state.jogos_aprovados)
        
        if total_jogos > 1:
            sel_idx = st.slider("Escolha a aposta para inspecionar:", 1, total_jogos, 1)
        else:
            sel_idx = 1
            st.info("ℹ️ Exibindo a única aposta encontrada pelos filtros.")
            
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
            <div class="box"><div style="font-weight:800;font-size:14px;margin-bottom:10px;color:#15803d;text-align:center;">Jogo #{sel_idx:04d} (6 dezenas): {' - '.join([f'{n:02d}' for n in jogo_ativo])}</div>
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

                st.markdown("**Linhas Presentes:** " + " • ".join([f"L{k}: `{v}x`" for k, v in sorted(cnt_linhas.items())]))
                st.markdown("**Colunas Presentes:** " + " • ".join([f"C{k:02d}: `{v}x`" for k, v in sorted(cnt_colunas.items())]))
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
# ABA 3: HISTÓRICO
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
