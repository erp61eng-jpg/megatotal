import streamlit as st
import streamlit.components.v1 as components
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from itertools import combinations, permutations
import random

st.set_page_config(
    page_title="MEGA60 - Laboratório de Filtros Estruturais",
    page_icon="🍀",
    layout="wide"
)

TOTAL_NUMS = 60
TAMANHO_JOGO = 6
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
# MOTOR TURBO: VALIDAÇÃO FAIL-FAST (SEM ALOCAÇÃO DESNECESSÁRIA)
# ==============================================================================
def valida_jogo_rapido(jogo, cfg):
    """
    Testa os 7 quadros com saída imediata no primeiro erro detectado.
    Evita alocação de memória e objetos intermediários.
    """
    # 1. Soma
    soma = sum(jogo)
    if not (cfg["soma_min"] <= soma <= cfg["soma_max"]):
        return False
        
    # 2. Primos
    primos = sum(1 for n in jogo if n in PRIMOS_MEGASENA)
    if not (cfg["primos_min"] <= primos <= cfg["primos_max"]):
        return False

    # 3. Pares e Ímpares
    pares = sum(1 for n in jogo if n % 2 == 0)
    if not (cfg["pares_min"] <= pares <= cfg["pares_max"]):
        return False
    if not (cfg["impares_min"] <= (6 - pares) <= cfg["impares_max"]):
        return False

    # 4. Moldura
    moldura = sum(1 for n in jogo if n in MOLDURA_SET)
    if not (cfg["moldura_min"] <= moldura <= cfg["moldura_max"]):
        return False

    # 5. Linhas, Colunas e Diagonais
    linhas = [0] * 6
    colunas = [0] * 10
    diag_cresc = [0] * 10
    diag_decresc = [0] * 10

    max_l = cfg["max_por_linha"]
    max_c = cfg["max_por_coluna"]
    max_dc = cfg["max_diag_cresc"]
    max_dd = cfg["max_diag_decresc"]

    for n in jogo:
        r = (n - 1) // 10
        c = (n - 1) % 10
        
        linhas[r] += 1
        if linhas[r] > max_l:
            return False
            
        colunas[c] += 1
        if colunas[c] > max_c:
            return False
            
        idx_dc = (c + r) % 10
        diag_cresc[idx_dc] += 1
        if diag_cresc[idx_dc] > max_dc:
            return False
            
        idx_dd = (c - r) % 10
        diag_decresc[idx_dd] += 1
        if diag_decresc[idx_dd] > max_dd:
            return False

    return True

def motor_executar_varredura(cfg, meta_jogos=1000):
    """
    Executa a filtragem sem travar a interface, com parada antecipada na meta.
    """
    aprovados = []
    
    # Modo Determinístico Perfeito: 1 por linha e 1 por coluna
    if cfg["max_por_linha"] == 1 and cfg["max_por_coluna"] == 1:
        cols_pares = [1, 3, 5, 7, 9]
        cols_impares = [0, 2, 4, 6, 8]
        linhas_indices = list(range(6))
        
        for q_par in range(cfg["pares_min"], cfg["pares_max"] + 1):
            q_impar = 6 - q_par
            if not (cfg["impares_min"] <= q_impar <= cfg["impares_max"]):
                continue
                
            for linhas_par in combinations(linhas_indices, q_par):
                linhas_par_set = set(linhas_par)
                linhas_impar = [l for l in linhas_indices if l not in linhas_par_set]
                
                for perm_par in permutations(cols_pares, q_par):
                    for perm_impar in permutations(cols_impares, q_impar):
                        colunas = [0] * 6
                        for idx, l in enumerate(linhas_par):
                            colunas[l] = perm_par[idx]
                        for idx, l in enumerate(linhas_impar):
                            colunas[l] = perm_impar[idx]
                            
                        jogo = [r * 10 + colunas[r] + 1 for r in range(6)]
                        
                        if valida_jogo_rapido(jogo, cfg):
                            aprovados.append(jogo)
                            if len(aprovados) >= meta_jogos:
                                return aprovados
        return aprovados

    # Modo Flexível: Distribuição livre por geração estruturada
    populacao = list(range(1, 61))
    vistos = set()
    tentativas = 0
    max_tentativas = 40000

    while len(aprovados) < meta_jogos and tentativas < max_tentativas:
        tentativas += 1
        jogo = tuple(sorted(random.sample(populacao, 6)))
        if jogo in vistos:
            continue
        vistos.add(jogo)
        
        if valida_jogo_rapido(jogo, cfg):
            aprovados.append(list(jogo))
            
    return aprovados

# ==============================================================================
# SINCRONIZAÇÃO OPCIONAL COM A CAIXA
# ==============================================================================
def sincronizar_com_caixa():
    url_base = "https://servicebus2.caixa.gov.br/portaldeloterias/api/megasena"
    headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
    try:
        resp = requests.get(url_base, headers=headers, timeout=4)
        if resp.status_code != 200:
            return None, "Indisponível"
        dados = resp.json()
        ultimo_num = int(dados["numero"])
        concursos = {ultimo_num: sorted([int(d) for d in dados["listaDezenas"]])}
        alvos = list(range(max(1, ultimo_num - 15), ultimo_num))
        
        def baixar(n):
            try:
                r = requests.get(f"{url_base}/{n}", headers=headers, timeout=2)
                if r.status_code == 200:
                    return n, sorted([int(d) for d in r.json()["listaDezenas"]])
            except:
                pass
            return n, None

        with ThreadPoolExecutor(max_workers=4) as ex:
            futuros = [ex.submit(baixar, n) for n in alvos]
            for f in as_completed(futuros):
                n_conc, nums = f.result()
                if nums and len(nums) == 6:
                    concursos[n_conc] = nums

        return [concursos[k] for k in sorted(concursos.keys())], f"#{ultimo_num}"
    except:
        return None, "Erro de Conexão"

# ==============================================================================
# INICIALIZAÇÃO INSTANTÂNEA (ZERO ESPERA)
# ==============================================================================
if "historico" not in st.session_state:
    st.session_state.historico = [list(j) for j in FALLBACK_MEGASENA]
    st.session_state.origem = "Base Local Offline (Carregamento Imediato)"

if "jogos_aprovados" not in st.session_state:
    st.session_state.jogos_aprovados = []

# ==============================================================================
# INTERFACE PRINCIPAL
# ==============================================================================
st.title("🍀 MEGA60: Painel de Filtros Estruturais")
st.caption(f"Status dos Dados: **{st.session_state.origem}**")

tab_quadros, tab_volante, tab_historico = st.tabs([
    "🎛️ Filtros dos 7 Quadros",
    "🗺️ Volante Visual & Detalhamento",
    "📊 Histórico & Sincronização"
])

with tab_quadros:
    st.markdown("#### Configure as Faixas dos 7 Quadros")
    
    c1, c2 = st.columns(2)
    with c1:
        with st.container(border=True):
            st.markdown("**1️⃣ Linhas e Colunas**")
            max_l = st.slider("Máximo por Linha (1 a 6):", 1, 6, 1)
            max_c = st.slider("Máximo por Coluna (1 a 10):", 1, 6, 1)
            
        with st.container(border=True):
            st.markdown("**2️⃣ Diagonais (01 a 10)**")
            max_dc = st.slider("Máximo por Diag. Crescente:", 1, 6, 1)
            max_dd = st.slider("Máximo por Diag. Decrescente:", 1, 6, 1)

        with st.container(border=True):
            st.markdown("**3️⃣ Primos (0 a 5)**")
            f_primos = st.slider("Quantidade de Primos:", 0, 5, (1, 2))

    with c2:
        with st.container(border=True):
            st.markdown("**4️⃣ Pares e Ímpares (0 a 6)**")
            f_pares = st.slider("Faixa de Pares:", 0, 6, (2, 4))
            f_impares = st.slider("Faixa de Ímpares:", 0, 6, (2, 4))

        with st.container(border=True):
            st.markdown("**5️⃣ Moldura (0 a 6)**")
            f_moldura = st.slider("Dezenas na Moldura:", 0, 6, (2, 4))

        with st.container(border=True):
            st.markdown("**6️⃣ Soma & Quantidade Alvo**")
            f_soma = st.slider("Intervalo de Soma:", 60, 300, (110, 230))
            limite_solicitado = st.select_slider("Quantidade Máxima de Jogos a Gerar:", [100, 500, 1000, 3000, 5000], value=1000)

    cfg = {
        "max_por_linha": max_l,
        "max_por_coluna": max_c,
        "max_diag_cresc": max_dc,
        "max_diag_decresc": max_dd,
        "primos_min": f_primos[0],
        "primos_max": f_primos[1],
        "pares_min": f_pares[0],
        "pares_max": f_pares[1],
        "impares_min": f_impares[0],
        "impares_max": f_impares[1],
        "moldura_min": f_moldura[0],
        "moldura_max": f_moldura[1],
        "soma_min": f_soma[0],
        "soma_max": f_soma[1]
    }

    st.divider()

    if st.button("🚀 Processar Varredura (Alta Velocidade)", use_container_width=True):
        barra = st.progress(0, text="Processando combinações estruturais...")
        resultados = motor_executar_varredura(cfg, meta_jogos=limite_solicitado)
        barra.progress(100, text="Concluído!")
        st.session_state.jogos_aprovados = resultados

    if st.session_state.jogos_aprovados:
        qtd = len(st.session_state.jogos_aprovados)
        st.success(f"✅ **Varredura Finalizada:** {qtd:,} apostas aprovadas!")
        
        txt_conteudo = "\n".join([" ".join([f"{n:02d}" for n in j]) for j in st.session_state.jogos_aprovados])
        st.download_button(
            "📥 Baixar Lista em .TXT",
            data=txt_conteudo,
            file_name=f"mega60_jogos_{qtd}.txt",
            mime="text/plain",
            use_container_width=True
        )

        with st.expander(f"Ver Primeiras Apostas ({min(qtd, 30)} de {qtd})", expanded=True):
            for i, j in enumerate(st.session_state.jogos_aprovados[:30]):
                p = sum(1 for n in j if n in PRIMOS_MEGASENA)
                par = sum(1 for n in j if n % 2 == 0)
                mold = sum(1 for n in j if n in MOLDURA_SET)
                nums = " - ".join([f"{n:02d}" for n in j])
                st.markdown(f"**Jogo #{i+1:03d}:** `{nums}` | {par}P/{6-par}I | {p} Primos | {mold} Moldura | Soma: {sum(j)}")

with tab_volante:
    st.subheader("Visualização da Cartela")
    if st.session_state.jogos_aprovados:
        idx = st.slider("Escolha o número do jogo:", 1, len(st.session_state.jogos_aprovados), 1)
        jogo_ativo = set(st.session_state.jogos_aprovados[idx - 1])
        
        celulas = ""
        for r in range(6):
            for c in range(10):
                n = r * 10 + c + 1
                if n in jogo_ativo:
                    celulas += f'<div style="width:36px;height:36px;background:#15803d;color:#fff;font-weight:800;border-radius:6px;display:flex;align-items:center;justify-content:center;font-family:monospace;font-size:13px;">{n:02d}</div>'
                else:
                    bg = "#f1f5f9" if n in MOLDURA_SET else "#ffffff"
                    celulas += f'<div style="width:36px;height:36px;background:{bg};color:#64748b;border:1px solid #cbd5e1;font-weight:600;border-radius:6px;display:flex;align-items:center;justify-content:center;font-family:monospace;font-size:13px;">{n:02d}</div>'
        
        html = f"""
        <!DOCTYPE html><html><head><meta charset="utf-8">
        <style>*{{box-sizing:border-box;}}body{{margin:0;padding:0;display:flex;justify-content:center;background:transparent;}}
        .box{{background:#fff;border:2px solid #16a34a;border-radius:10px;padding:12px;width:fit-content;}}
        .grid{{display:grid;grid-template-columns:repeat(10,36px);gap:5px;}}</style></head><body>
        <div class="box"><div class="grid">{celulas}</div></div></body></html>
        """
        components.html(html, height=310, scrolling=False)
    else:
        st.info("Processe os filtros na primeira aba para inspecionar no volante.")

with tab_historico:
    st.subheader("Base de Sorteios")
    st.write(f"Concursos ativos em memória: **{len(st.session_state.historico)}**")
    
    if st.button("🌐 Sincronizar com Servidor da Caixa Agora"):
        with st.spinner("Conectando à API da Caixa..."):
            dados, info = sincronizar_com_caixa()
            if dados:
                st.session_state.historico = dados
                st.session_state.origem = f"Caixa Online ({info})"
                st.success("Base atualizada com sucesso!")
                st.rerun()
            else:
                st.warning("Servidor da Caixa não respondeu. Mantendo base de segurança local.")
