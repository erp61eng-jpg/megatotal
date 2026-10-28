import streamlit as st
import streamlit.components.v1 as components
import requests
from itertools import combinations, product
from collections import Counter
import math
import time
import re
import pandas as pd

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
# MOTOR MATEMÁTICO: VALIDAÇÃO RIGOROSA DA APOSTA FINAL DE 6 DEZENAS
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

def gerar_particoes_linhas(limites_linhas, alvo):
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

    min_linhas = sum(l[0] for l in cfg["linhas"])
    max_linhas = sum(l[1] for l in cfg["linhas"])
    
    if min_linhas > 6:
        alvo_busca = min_linhas
        modo_desdobramento = True
        container_status.write(
            f"🔄 **Modo Desdobramento Automático:** Suas linhas exigem um grupo de **{alvo_busca} dezenas** "
            f"(ex.: 2-1-1-1-1-2). O sistema vai gerar essas matrizes e **desdobrá-las em jogos de 6 dezenas**!"
        )
    elif max_linhas < 6:
        container_status.error(
            f"A soma máxima configurada nas linhas ({max_linhas}) é menor que 6. "
            f"É impossível formar uma aposta de 6 números. Aumente os valores das linhas."
        )
        return []
    else:
        alvo_busca = 6
        modo_desdobramento = False
        container_status.write("⚡ **Modo Direto:** Gerando diretamente combinações de 6 dezenas.")

    particoes = gerar_particoes_linhas(cfg["linhas"], alvo=alvo_busca)
    
    if not particoes:
        container_status.error(
            f"Não foi possível encontrar partições válidas para atingir {alvo_busca} dezenas com os limites definidos."
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
        container_status.error("Nenhuma dezena disponível nas linhas atende aos filtros de coluna e diagonal selecionados.")
        return []

    container_status.write(
        f"📊 **Plano de Execução:** {len(particoes_viaveis)} partições de linhas identificadas. "
        f"Universo base a inspecionar: **{total_estimado:,} matrizes**."
    )

    jogos_finais_set = set()
    testadas = 0
    lote_update = max(1, min(1000, total_estimado // 50))

    for part in particoes_viaveis:
        geradores = [combinations(dezenas_por_linha[r], part[r]) for r in range(6)]
        
        for pedacos in product(*geradores):
            testadas += 1
            matriz_candidata = []
            for p in pedacos:
                matriz_candidata.extend(p)

            if not modo_desdobramento:
                if validar_aposta_final_6(matriz_candidata, cfg):
                    jogos_finais_set.add(tuple(sorted(matriz_candidata)))
            else:
                for sub_jogo in combinations(matriz_candidata, 6):
                    if validar_aposta_final_6(sub_jogo, cfg):
                        jogos_finais_set.add(tuple(sorted(sub_jogo)))

            if testadas % lote_update == 0:
                prog = testadas / total_estimado
                bar_progresso.progress(prog)
                delta_t = max(0.001, time.time() - t_inicio)
                velocidade = int(testadas / delta_t)
                ticker_metricas.markdown(
                    f"**Linha de Serviço:** `{testadas:,}` de `{total_estimado:,}` ({prog*100:.1f}%) | "
                    f"Apostas de 6 dezenas geradas: `{len(jogos_finais_set):,}` | "
                    f"Velocidade: `{velocidade:,} matrizes/s` | Tempo: `{delta_t:.2f}s`"
                )

    bar_progresso.progress(1.0)
    delta_final = max(0.001, time.time() - t_inicio)
    ticker_metricas.markdown(
        f"**Linha de Serviço:** `{testadas:,}` matrizes processadas | "
        f"Aprovados finais: `{len(jogos_finais_set):,}` apostas oficiais de 6 dezenas | "
        f"Tempo total: `{delta_final:.2f}s`"
    )
    
    return [list(j) for j in sorted(list(jogos_finais_set))]

# ==============================================================================
# FUNÇÕES DE PROCESSAMENTO E PARSER DE UPLOAD
# ==============================================================================
def processar_arquivo_upload(conteudo_bytes):
    """Extrai jogos de 6 dezenas a partir de texto com qualquer separador."""
    texto = conteudo_bytes.decode("utf-8", errors="ignore")
    linhas = texto.strip().splitlines()
    jogos = []
    invalidos = 0
    
    for linha in linhas:
        l = linha.strip()
        if not l:
            continue
        # Encontra todos os números na linha
        nums = [int(x) for x in re.findall(r"\b\d+\b", l)]
        nums_validos = sorted(list(set([n for n in nums if 1 <= n <= 60])))
        if len(nums_validos) == 6:
            jogos.append(nums_validos)
        else:
            invalidos += 1
            
    return jogos, invalidos

def calcular_estatisticas_completas(lista_jogos):
    """Gera diagnóstico estatístico detalhado sobre uma lista de jogos."""
    if not lista_jogos:
        return None
        
    cnt_nums = Counter()
    cnt_pares = Counter()
    cnt_primos = Counter()
    cnt_moldura = Counter()
    cnt_linhas = Counter()
    cnt_colunas = Counter()
    cnt_dc = Counter()
    cnt_dd = Counter()
    somas = []
    
    for j in lista_jogos:
        soma = sum(j)
        somas.append(soma)
        pares = sum(1 for n in j if PROPS[n]["is_par"])
        primos = sum(1 for n in j if PROPS[n]["is_primo"])
        moldura = sum(1 for n in j if PROPS[n]["is_moldura"])
        
        cnt_pares[pares] += 1
        cnt_primos[primos] += 1
        cnt_moldura[moldura] += 1
        
        for n in j:
            cnt_nums[n] += 1
            cnt_linhas[PROPS[n]["r"] + 1] += 1
            cnt_colunas[PROPS[n]["c"] + 1] += 1
            cnt_dc[PROPS[n]["dc"] + 1] += 1
            cnt_dd[PROPS[n]["dd"] + 1] += 1

    return {
        "total_jogos": len(lista_jogos),
        "cnt_nums": cnt_nums,
        "cnt_pares": cnt_pares,
        "cnt_primos": cnt_primos,
        "cnt_moldura": cnt_moldura,
        "cnt_linhas": cnt_linhas,
        "cnt_colunas": cnt_colunas,
        "cnt_dc": cnt_dc,
        "cnt_dd": cnt_dd,
        "soma_min": min(somas),
        "soma_max": max(somas),
        "soma_media": sum(somas) / len(somas),
        "somas": somas
    }

# ==============================================================================
# INICIALIZAÇÃO
# ==============================================================================
if "historico" not in st.session_state:
    st.session_state.historico = [list(j) for j in FALLBACK_MEGASENA]
    st.session_state.origem = "Base Local Offline"

if "jogos_aprovados" not in st.session_state:
    st.session_state.jogos_aprovados = []

if "jogos_upload" not in st.session_state:
    st.session_state.jogos_upload = []

# ==============================================================================
# INTERFACE PRINCIPAL (4 ABAS)
# ==============================================================================
st.title("🍀 MEGA60: Painel de Filtros & Auditoria Estatística")
st.caption("Configuração Granular • Desdobramento Automático • Auditoria Completa por Upload")

tab_config, tab_volante, tab_upload, tab_historico = st.tabs([
    "🎛️ Configuração dos Quadros",
    "🗺️ Volante Visual & Raio-X",
    "📥 Upload & Estatísticas de Apostas",
    "📊 Histórico & Conexão Caixa"
])

# ==============================================================================
# ABA 1: CONFIGURAÇÃO INDIVIDUAL
# ==============================================================================
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
                    index=2,
                    key=f"sel_l_{r}"
                )
                limites_linhas.append(OPCOES_QUANTIDADE[escolha_l])

        soma_min_linhas = sum(l[0] for l in limites_linhas)
        soma_max_linhas = sum(l[1] for l in limites_linhas)

        if soma_min_linhas == soma_max_linhas == 6:
            st.info("ℹ️ **Modo Direto:** Suas linhas somam exatamente 6. Cada matriz gera diretamente 1 aposta de 6 números.")
        elif soma_min_linhas > 6:
            st.success(
                f"🎯 **Desdobramento Automático Ativo:** Suas linhas somam **{soma_min_linhas} dezenas** "
                f"(ex.: 2-1-1-1-1-2). O sistema vai gerar essas matrizes de {soma_min_linhas} dezenas e **desdobrá-las em jogos de 6 números**!"
            )
        elif soma_max_linhas < 6:
            st.error(f"❌ A soma máxima configurada ({soma_max_linhas}) é menor que 6. Aumente os valores das linhas para alcançar 6 dezenas.")
        else:
            st.info(f"ℹ️ **Modo Flexível:** As linhas permitem entre {soma_min_linhas} e {soma_max_linhas} dezenas. O sistema formará jogos de 6 números respeitando essa distribuição.")

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
                    index=6,
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

    st.markdown("### 📡 Linha de Acompanhamento de Serviço")
    placeholder_metricas = st.empty()
    barra_progresso = st.progress(0, text="Aguardando comando de execução...")

    pode_iniciar = soma_max_linhas >= 6

    if st.button("🚀 Processar Varredura e Desdobrar em Jogos de 6 Dezenas", use_container_width=True, disabled=not pode_iniciar):
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
            st.metric("Apostas Geradas", f"{qtd_aprov:,}")

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
    st.subheader("Dissecação da Cartela Oficial (Jogos do Motor MEGA60)")
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
# ABA 3: NOVA SEÇÃO - UPLOAD & ESTATÍSTICAS COMPLETAS
# ==============================================================================
with tab_upload:
    st.subheader("📥 Upload & Diagnóstico Estatístico das Suas Apostas")
    st.markdown("""
    Envie um arquivo com suas apostas (`.txt` ou `.csv`). O sistema aceita qualquer separador 
    (espaço, vírgula, traço, ponto e vírgula) e gera a **radiografia estatística completa do lote**.
    """)

    arquivo_enviado = st.file_uploader(
        "Carregue seu arquivo de jogos (.txt ou .csv):", 
        type=["txt", "csv"], 
        help="Cada linha deve conter uma aposta de 6 dezenas (ex: 04 12 18 30 35 54)."
    )

    if arquivo_enviado is not None:
        conteudo = arquivo_enviado.read()
        jogos_carregados, invalidos = processar_arquivo_upload(conteudo)
        st.session_state.jogos_upload = jogos_carregados
        
        if invalidos > 0:
            st.warning(f"⚠️ Atenção: {invalidos} linha(s) foram ignoradas por não conterem exatamente 6 dezenas válidas (1 a 60).")

    if st.session_state.jogos_upload:
        jogos_up = st.session_state.jogos_upload
        stats_up = calcular_estatisticas_completas(jogos_up)
        total_up = stats_up["total_jogos"]

        st.success(f"✅ **Arquivo Processado com Sucesso:** **{total_up:,} apostas oficiais** identificadas e auditadas!")

        # 1. CARDS DE RESUMO GERAL
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Total de Jogos", f"{total_up:,}")
        m2.metric("Soma Média", f"{stats_up['soma_media']:.1f}")
        m3.metric("Menor Soma", f"{stats_up['soma_min']}")
        m4.metric("Maior Soma", f"{stats_up['soma_max']}")
        
        # Dezenas mais e menos frequentes
        mais_freq = stats_up["cnt_nums"].most_common(1)[0]
        m5.metric("Dezena Mais Frequente", f"{mais_freq[0]:02d} ({mais_freq[1]}x)")

        st.divider()

        # 2. MAPA TÉRMICO 6x10 DO ARQUIVO ENVIADO
        st.markdown("#### 🔥 Mapa de Calor 6x10 (Distribuição das Apostas Enviadas)")
        v_min = min(stats_up["cnt_nums"].values()) if stats_up["cnt_nums"] else 0
        v_max = max(stats_up["cnt_nums"].values()) if stats_up["cnt_nums"] else 1
        delta_v = max(1, v_max - v_min)

        celulas_up_heat = ""
        for r in range(6):
            for c in range(10):
                n = r * 10 + c + 1
                freq = stats_up["cnt_nums"][n]
                ratio = (freq - v_min) / delta_v
                
                if freq == 0:
                    bg = "#f8fafc"
                    color = "#94a3b8"
                elif ratio < 0.35:
                    bg = "#bbf7d0"
                    color = "#166534"
                elif ratio < 0.70:
                    bg = "#fed7aa"
                    color = "#9a3412"
                else:
                    bg = "#fca5a5"
                    color = "#991b1b"

                celulas_up_heat += f"""
                <div style="width:46px;height:46px;background:{bg};color:{color};border-radius:6px;display:flex;flex-direction:column;align-items:center;justify-content:center;font-family:monospace;border:1px solid rgba(0,0,0,0.08);box-sizing:border-box;">
                    <span style="font-size:14px;font-weight:900;">{n:02d}</span>
                    <span style="font-size:10px;font-weight:700;">{freq}x</span>
                </div>
                """

        html_upload_heatmap = f"""
        <!DOCTYPE html><html><head><meta charset="utf-8">
        <style>*{{box-sizing:border-box;}}body{{margin:0;padding:0;background:transparent;display:flex;justify-content:center;font-family:sans-serif;}}
        .box{{background:#fff;border:2px solid #cbd5e1;border-radius:12px;padding:14px;width:fit-content;box-shadow:0 4px 12px rgba(0,0,0,0.05);}}
        .grid{{display:grid;grid-template-columns:repeat(10,46px);gap:5px;}}</style></head><body>
        <div class="box"><div style="font-weight:800;color:#15803d;text-align:center;margin-bottom:10px;font-size:14px;">Frequência de Ocorrência na Matriz 6x10</div><div class="grid">{celulas_up_heat}</div></div></body></html>
        """
        components.html(html_upload_heatmap, height=360, scrolling=False)

        st.divider()

        # 3. DIAGNÓSTICO DOS 7 QUADROS
        st.markdown("#### 🔬 Distribuição Estrutural nos 7 Quadros")
        c_quad1, c_quad2, c_quad3 = st.columns(3)

        with c_quad1:
            with st.container(border=True):
                st.markdown("**Quadro: Paridade (Pares x Ímpares)**")
                df_par = pd.DataFrame([
                    {"Divisão": f"{p} Pares / {6-p} Ímpares", "Jogos": qtd, "Proporção": f"{(qtd/total_up)*100:.1f}%"}
                    for p, qtd in sorted(stats_up["cnt_pares"].items(), key=lambda x: -x[1])
                ])
                st.dataframe(df_par, hide_index=True, use_container_width=True)

        with c_quad2:
            with st.container(border=True):
                st.markdown("**Quadro: Primos da Mega-Sena**")
                df_primos = pd.DataFrame([
                    {"Qtd Primos": f"{p} Primos", "Jogos": qtd, "Proporção": f"{(qtd/total_up)*100:.1f}%"}
                    for p, qtd in sorted(stats_up["cnt_primos"].items(), key=lambda x: -x[1])
                ])
                st.dataframe(df_primos, hide_index=True, use_container_width=True)

        with c_quad3:
            with st.container(border=True):
                st.markdown("**Quadro: Moldura x Miolo**")
                df_mold = pd.DataFrame([
                    {"Moldura": f"{m} Moldura / {6-m} Miolo", "Jogos": qtd, "Proporção": f"{(qtd/total_up)*100:.1f}%"}
                    for m, qtd in sorted(stats_up["cnt_moldura"].items(), key=lambda x: -x[1])
                ])
                st.dataframe(df_mold, hide_index=True, use_container_width=True)

        # 4. FREQUÊNCIA EM LINHAS, COLUNAS E DIAGONAIS
        st.markdown("#### 📐 Distribuição em Linhas, Colunas e Diagonais")
        c_l, c_c, c_d = st.columns(3)
        with c_l:
            with st.container(border=True):
                st.markdown("**Presença por Linha (01 a 06):**")
                for r in range(1, 7):
                    tot_l = stats_up["cnt_linhas"][r]
                    st.write(f"- **Linha {r:02d}:** {tot_l} dezenas ({tot_l/(total_up*6)*100:.1f}%)")

        with c_c:
            with st.container(border=True):
                st.markdown("**Presença por Coluna (01 a 10):**")
                for c in range(1, 11):
                    tot_c = stats_up["cnt_colunas"][c]
                    st.write(f"- **Coluna {c:02d}:** {tot_c} dezenas ({tot_c/(total_up*6)*100:.1f}%)")

        with c_d:
            with st.container(border=True):
                st.markdown("**Top Diagonais Crescentes (DC):**")
                for dc, tot_dc in stats_up["cnt_dc"].most_common(5):
                    st.write(f"- **DC{dc:02d}:** {tot_dc} dezenas")

        st.divider()

        # 5. INSPEÇÃO NO VOLANTE DOS JOGOS DO UPLOAD
        st.markdown("#### 🔍 Inspecionar Qualquer Aposta do Arquivo no Volante")
        idx_up_sel = st.slider("Escolha a aposta para visualizar no volante:", 1, total_up, 1, key="slider_upload")
        jogo_up_ativo = jogos_up[idx_up_sel - 1]
        marcadas_up = set(jogo_up_ativo)

        c_vup1, c_vup2 = st.columns([1, 1])
        with c_vup1:
            celulas_up = ""
            for r in range(6):
                for c in range(10):
                    n = r * 10 + c + 1
                    if n in marcadas_up:
                        celulas_up += f'<div style="width:36px;height:36px;background:linear-gradient(135deg,#16a34a,#15803d);color:#fff;border:2px solid #0f5132;font-weight:800;border-radius:8px;display:flex;align-items:center;justify-content:center;font-family:monospace;font-size:13px;box-sizing:border-box;">{n:02d}</div>'
                    else:
                        bg = "#f1f5f9" if n in MOLDURA_SET else "#ffffff"
                        celulas_up += f'<div style="width:36px;height:36px;background:{bg};color:#64748b;border:1px solid #cbd5e1;font-weight:600;border-radius:8px;display:flex;align-items:center;justify-content:center;font-family:monospace;font-size:13px;box-sizing:border-box;">{n:02d}</div>'

            html_vup = f"""
            <!DOCTYPE html><html><head><meta charset="utf-8">
            <style>*{{box-sizing:border-box;}}body{{margin:0;padding:0;display:flex;justify-content:center;background:transparent;font-family:sans-serif;}}
            .box{{background:#fff;border:2px solid #16a34a;border-radius:12px;padding:12px;box-shadow:0 4px 12px rgba(22,163,74,0.12);width:fit-content;}}
            .grid{{display:grid;grid-template-columns:repeat(10,36px);gap:5px;}}</style></head><body>
            <div class="box"><div style="font-weight:800;font-size:14px;margin-bottom:10px;color:#15803d;text-align:center;">Aposta #{idx_up_sel:04d}: {' - '.join([f'{n:02d}' for n in jogo_up_ativo])}</div>
            <div class="grid">{celulas_up}</div></div></body></html>
            """
            components.html(html_vup, height=330, scrolling=False)

        with c_vup2:
            with st.container(border=True):
                st.markdown(f"**Raio-X da Aposta #{idx_up_sel:04d}**")
                p_u = sum(1 for n in jogo_up_ativo if PROPS[n]["is_primo"])
                pa_u = sum(1 for n in jogo_up_ativo if PROPS[n]["is_par"])
                mo_u = sum(1 for n in jogo_up_ativo if PROPS[n]["is_moldura"])
                st.write(f"- **Dezenas:** `{' - '.join([f'{n:02d}' for n in jogo_up_ativo])}`")
                st.write(f"- **Paridade:** `{pa_u} Pares / {6-pa_u} Ímpares`")
                st.write(f"- **Primos:** `{p_u}`")
                st.write(f"- **Moldura:** `{mo_u} dezenas` (Miolo: `{6-mo_u}`)")
                st.write(f"- **Soma Total:** `{sum(jogo_up_ativo)}`")
    else:
        st.info("Faça o upload de um arquivo com apostas acima para gerar o diagnóstico estatístico completo.")

# ==============================================================================
# ABA 4: HISTÓRICO
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
                    st.success(f"Conexão bem-sucedida! Concurso oficial #{ult['numero']}")
                else:
                    st.warning("Servidor da Caixa indisponível no momento.")
            except Exception as e:
                st.error(f"Erro ao conectar: {e}")
