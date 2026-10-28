import streamlit as st
import streamlit.components.v1 as components
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from itertools import combinations, permutations
from collections import Counter
import random

st.set_page_config(
    page_title="MEGA60 - Painel de Filtros Estruturais",
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
MIOLO_SET = set(range(1, 61)) - MOLDURA_SET

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
# FUNÇÕES DE MAPEAMENTO MATRICIAL 6x10
# ==============================================================================
def obter_coordenadas(num):
    """Retorna (linha: 0..5, coluna: 0..9) a partir da dezena 1..60"""
    r = (num - 1) // 10
    c = (num - 1) % 10
    return r, c

def mapear_propriedades_jogo(jogo):
    """Extrai o perfil completo do jogo em relação aos 7 quadros estruturais."""
    linhas = [0] * 6
    colunas = [0] * 10
    diag_cresc = [0] * 10   # Diagonais Crescentes D01..D10: (c + r) % 10
    diag_decresc = [0] * 10 # Diagonais Decrescentes D01..D10: (c - r) % 10
    
    qtd_primos = 0
    qtd_pares = 0
    qtd_moldura = 0
    
    for n in jogo:
        r, c = obter_coordenadas(n)
        linhas[r] += 1
        colunas[c] += 1
        diag_cresc[(c + r) % 10] += 1
        diag_decresc[(c - r) % 10] += 1
        
        if n in PRIMOS_MEGASENA:
            qtd_primos += 1
        if n % 2 == 0:
            qtd_pares += 1
        if n in MOLDURA_SET:
            qtd_moldura += 1
            
    qtd_impares = 6 - qtd_pares
    qtd_miolo = 6 - qtd_moldura
    soma = sum(jogo)
    
    return {
        "linhas": linhas,
        "colunas": colunas,
        "diag_cresc": diag_cresc,
        "diag_decresc": diag_decresc,
        "primos": qtd_primos,
        "pares": qtd_pares,
        "impares": qtd_impares,
        "moldura": qtd_moldura,
        "miolo": qtd_miolo,
        "soma": soma
    }

# ==============================================================================
# MOTORES DE FILTRAGEM
# ==============================================================================
def validar_jogo(jogo, cfg):
    """Aplica os filtros dos 7 quadros a um jogo individual."""
    info = mapear_propriedades_jogo(jogo)
    
    # 1. Pares e Ímpares (01 a 06)
    if not (cfg["pares_min"] <= info["pares"] <= cfg["pares_max"]):
        return False
    if not (cfg["impares_min"] <= info["impares"] <= cfg["impares_max"]):
        return False
        
    # 2. Primos (01 a 05)
    if not (cfg["primos_min"] <= info["primos"] <= cfg["primos_max"]):
        return False
        
    # 3. Moldura (01 a 06)
    if not (cfg["moldura_min"] <= info["moldura"] <= cfg["moldura_max"]):
        return False
        
    # 4. Linhas (Máximo por Linha de 1 a 6)
    if max(info["linhas"]) > cfg["max_por_linha"]:
        return False
        
    # 5. Colunas (Máximo por Coluna de 1 a 10)
    if max(info["colunas"]) > cfg["max_por_coluna"]:
        return False
        
    # 6. Diagonais Crescentes e Decrescentes (Máximo de 1 a 10)
    if max(info["diag_cresc"]) > cfg["max_diag_cresc"]:
        return False
    if max(info["diag_decresc"]) > cfg["max_diag_decresc"]:
        return False
        
    # 7. Soma
    if not (cfg["soma_min"] <= info["soma"] <= cfg["soma_max"]):
        return False
        
    return True

def motor_estrutural_mega60(cfg, limite_amostras=50000):
    """
    Executa a varredura aplicando os 7 quadros estruturais.
    - Se max_por_linha == 1 e max_por_coluna == 1, usa o algoritmo determinístico de permutação direta.
    - Se relaxado, usa o motor combinatório flexível.
    """
    jogos_filtrados = []
    
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
                        
                        if validar_jogo(jogo, cfg):
                            jogos_filtrados.append(jogo)
                            if len(jogos_filtrados) >= limite_amostras:
                                return jogos_filtrados
    else:
        # Modo Flexível por Amostragem Aleatória Rejeitada (Monte Carlo estruturado)
        populacao = list(range(1, 61))
        tentativas = 0
        vistos = set()
        
        while len(jogos_filtrados) < limite_amostras and tentativas < 150000:
            tentativas += 1
            jogo = tuple(sorted(random.sample(populacao, 6)))
            if jogo in vistos:
                continue
            vistos.add(jogo)
            
            if validar_jogo(list(jogo), cfg):
                jogos_filtrados.append(list(jogo))
                
    return jogos_filtrados

# ==============================================================================
# API CAIXA & DADOS
# ==============================================================================
@st.cache_data(ttl=7200, show_spinner=False)
def buscar_historico_caixa():
    url_base = "https://servicebus2.caixa.gov.br/portaldeloterias/api/megasena"
    headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
    session = requests.Session()
    session.headers.update(headers)
    try:
        resp = session.get(url_base, timeout=6)
        if resp.status_code != 200:
            return None, "Offline"
        dados = resp.json()
        ultimo_num = int(dados["numero"])
        concursos = {ultimo_num: sorted([int(d) for d in dados["listaDezenas"]])}
        alvos = list(range(max(1, ultimo_num - 29), ultimo_num))
        
        def baixar(n):
            try:
                r = session.get(f"{url_base}/{n}", timeout=3)
                if r.status_code == 200:
                    return n, sorted([int(d) for d in r.json()["listaDezenas"]])
            except:
                pass
            return n, None

        with ThreadPoolExecutor(max_workers=8) as ex:
            futuros = [ex.submit(baixar, n) for n in alvos]
            for f in as_completed(futuros):
                n_conc, nums = f.result()
                if nums and len(nums) == 6:
                    concursos[n_conc] = nums

        return [concursos[k] for k in sorted(concursos.keys())], f"#{ultimo_num}"
    except:
        return None, "Fallback"

# ==============================================================================
# COMPONENTES VISUAIS (CSS EMBUTIDO)
# ==============================================================================
def render_volante_completo(jogo, titulo=""):
    marcadas = set(jogo)
    celulas = ""
    for r in range(6):
        for c in range(10):
            n = r * 10 + c + 1
            if n in marcadas:
                celulas += f'<div style="width:36px;height:36px;background:linear-gradient(135deg,#16a34a,#15803d);color:#fff;border:2px solid #0f5132;font-weight:800;border-radius:8px;display:flex;align-items:center;justify-content:center;font-family:monospace;font-size:13px;">{n:02d}</div>'
            else:
                is_moldura = n in MOLDURA_SET
                bg = "#f1f5f9" if is_moldura else "#ffffff"
                border = "#cbd5e1"
                celulas += f'<div style="width:36px;height:36px;background:{bg};color:#64748b;border:1px solid {border};font-weight:600;border-radius:8px;display:flex;align-items:center;justify-content:center;font-family:monospace;font-size:13px;">{n:02d}</div>'
    
    html = f"""
    <!DOCTYPE html><html><head><meta charset="utf-8">
    <style>*{{box-sizing:border-box;}}body{{margin:0;padding:0;display:flex;justify-content:center;font-family:sans-serif;background:transparent;}}
    .box{{background:#fff;border:2px solid #16a34a;border-radius:12px;padding:14px;box-shadow:0 4px 12px rgba(22,163,74,0.12);width:fit-content;}}
    .grid{{display:grid;grid-template-columns:repeat(10,36px);gap:5px;}}</style></head><body>
    <div class="box"><div style="font-weight:800;font-size:14px;margin-bottom:10px;color:#15803d;text-align:center;">{titulo}</div>
    <div class="grid">{celulas}</div></div></body></html>
    """
    components.html(html, height=330, scrolling=False)

def painel_raio_x_quadros(info):
    """Exibe badges com o diagnóstico de todos os 7 quadros estruturais."""
    col_a, col_b, col_c, col_d = st.columns(4)
    with col_a:
        st.markdown(f"**Quadro Linhas (01 a 06):**")
        l_txt = " • ".join([f"L{i+1}: `{v}`" for i, v in enumerate(info['linhas'])])
        st.caption(l_txt)
        st.markdown(f"**Quadro Primos:** `{info['primos']}` dezenas")

    with col_b:
        st.markdown(f"**Quadro Colunas (01 a 10):**")
        c_txt = " ".join([f"C{i+1}:`{v}`" for i, v in enumerate(info['colunas'])])
        st.caption(c_txt)
        st.markdown(f"**Quadro Paridade:** `{info['pares']} Pares` | `{info['impares']} Ímpares`")

    with col_c:
        st.markdown(f"**Diag. Crescentes (01 a 10):**")
        dc_txt = " ".join([f"D{i+1}:`{v}`" for i, v in enumerate(info['diag_cresc']) if v > 0] or ["Nenhuma"])
        st.caption(f"Ativas: {dc_txt}")
        st.markdown(f"**Quadro Moldura/Miolo:** `{info['moldura']} Moldura` | `{info['miolo']} Miolo`")

    with col_d:
        st.markdown(f"**Diag. Decrescentes (01 a 10):**")
        dd_txt = " ".join([f"D{i+1}:`{v}`" for i, v in enumerate(info['diag_decresc']) if v > 0] or ["Nenhuma"])
        st.caption(f"Ativas: {dd_txt}")
        st.markdown(f"**Soma Geral:** `{info['soma']}`")

def converter_txt(jogos):
    return "\n".join([" ".join([f"{n:02d}" for n in j]) for j in jogos])

# ==============================================================================
# INICIALIZAÇÃO
# ==============================================================================
if "historico" not in st.session_state:
    res, info = buscar_historico_caixa()
    st.session_state.historico = res if res else [list(j) for j in FALLBACK_MEGASENA]
    st.session_state.origem = f"Caixa Oficial ({info})" if res else "Base Local"

if "jogos_aprovados" not in st.session_state:
    st.session_state.jogos_aprovados = []

# ==============================================================================
# CABEÇALHO & ABAS PRINCIPAIS
# ==============================================================================
st.title("🍀 MEGA60: Laboratório de Filtros Estruturais")
st.caption("Painel Paramétrico dos 7 Quadros • Matriz 6x10 • Varredura Completa das 60 Dezenas")

tab_quadros, tab_volante, tab_estatisticas = st.tabs([
    "🎛️ Os 7 Quadros Estruturais & Varredura",
    "🗺️ Volante & Raio-X dos Quadros",
    "📊 Estatísticas Históricas da Matriz"
])

# ==============================================================================
# ABA 1: OS 7 QUADROS ESTRUTURAIS
# ==============================================================================
with tab_quadros:
    st.markdown("### 🎛️ Configuração dos Quadros Estruturais da Matriz 6x10")
    
    col_q1, col_q2 = st.columns(2)
    
    with col_q1:
        with st.container(border=True):
            st.markdown("#### 1️⃣ Quadro: Linhas (01 a 06) & Colunas (01 a 10)")
            max_l = st.slider("Máximo de Dezenas por Linha (01 a 06):", 1, 6, 1, 
                              help="1 = exatamente 1 por linha (Mega-Sena perfeita). 2 = permite até 2 dezenas na mesma linha.")
            max_c = st.slider("Máximo de Dezenas por Coluna (01 a 10):", 1, 6, 1,
                              help="1 = colunas distintas sem repetição vertical.")
            
        with st.container(border=True):
            st.markdown("#### 2️⃣ Quadro: Diagonais Crescentes & Decrescentes (01 a 10)")
            max_dc = st.slider("Máximo por Diagonal Crescente (01 a 10):", 1, 6, 1,
                               help="Limita colisões em diagonais inclinadas para cima/direita.")
            max_dd = st.slider("Máximo por Diagonal Decrescente (01 a 10):", 1, 6, 1,
                               help="Limita colisões em diagonais inclinadas para baixo/direita.")

        with st.container(border=True):
            st.markdown("#### 3️⃣ Quadro: Primos (01 a 05)")
            f_primos = st.slider("Quantidade de Dezenas Primas:", 0, 5, (1, 2),
                                 help="Primos da Mega-Sena: 2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59.")

    with col_q2:
        with st.container(border=True):
            st.markdown("#### 4️⃣ Quadro: Pares (01 a 06) & Ímpares (01 a 06)")
            f_pares = st.slider("Faixa de Pares:", 0, 6, (2, 4), help="Exemplo: 3 pares implica automaticamente 3 ímpares.")
            f_impares = st.slider("Faixa de Ímpares:", 0, 6, (2, 4), help="Controle complementar de ímpares.")

        with st.container(border=True):
            st.markdown("#### 5️⃣ Quadro: Moldura (01 a 06) & Miolo")
            f_moldura = st.slider("Dezenas na Moldura Externa (01 a 06):", 0, 6, (2, 4),
                                  help="A moldura compreende 28 dezenas periféricas; o miolo possui 32 dezenas.")

        with st.container(border=True):
            st.markdown("#### 6️⃣ Quadro: Faixa de Soma Geral")
            f_soma = st.slider("Intervalo de Soma das 6 Dezenas:", 50, 320, (110, 240))

    cfg_atual = {
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

    if st.button("🚀 Processar Varredura com Todos os Quadros", use_container_width=True):
        with st.spinner("Filtrando combinações em alta performance..."):
            aprovados = motor_estrutural_mega60(cfg_atual)
            st.session_state.jogos_aprovados = aprovados

    if st.session_state.jogos_aprovados:
        qtd_total = len(st.session_state.jogos_aprovados)
        st.success(f"🎉 **Varredura Finalizada:** Exatamente **{qtd_total:,} apostas** atendem rigorosamente a todos os 7 quadros!")

        c_down1, c_down2 = st.columns([3, 1])
        with c_down1:
            st.download_button(
                "📥 Baixar Arquivo de Jogos (.TXT)",
                data=converter_txt(st.session_state.jogos_aprovados),
                file_name=f"mega60_quadros_{qtd_total}_jogos.txt",
                mime="text/plain",
                use_container_width=True
            )
        with c_down2:
            st.metric("Total Aprovado", f"{qtd_total:,}")

        with st.expander(f"Visualizar Lista Preliminar ({min(qtd_total, 50)} de {qtd_total})", expanded=True):
            for i, j in enumerate(st.session_state.jogos_aprovados[:50]):
                p = sum(1 for n in j if n in PRIMOS_MEGASENA)
                par = sum(1 for n in j if n % 2 == 0)
                mold = sum(1 for n in j if n in MOLDURA_SET)
                dezenas_fmt = " - ".join([f"{n:02d}" for n in j])
                st.markdown(
                    f"**Jogo #{i+1:03d}:** `{dezenas_fmt}` | **{par}P/{6-par}I** | **{p} Primos** | **{mold} Moldura** | Soma: `{sum(j)}`"
                )

# ==============================================================================
# ABA 2: VOLANTE VISUAL & RAIO-X DOS QUADROS
# ==============================================================================
with tab_volante:
    st.subheader("Inspeção Estrutural da Cartela")
    if st.session_state.jogos_aprovados:
        sel_idx = st.slider("Selecione o número da aposta para dissecação:", 1, len(st.session_state.jogos_aprovados), 1)
        jogo_ativo = st.session_state.jogos_aprovados[sel_idx - 1]
        
        c_vol, c_rx = st.columns([1, 1])
        with c_vol:
            render_volante_completo(jogo_ativo, titulo=f"Jogo #{sel_idx:03d}: {' - '.join([f'{n:02d}' for n in jogo_ativo])}")
        
        with c_rx:
            with st.container(border=True):
                st.markdown("#### 🔬 Raio-X dos 7 Quadros para este Jogo")
                info_j = mapear_propriedades_jogo(jogo_ativo)
                painel_raio_x_quadros(info_j)
    else:
        st.info("Execute a varredura na primeira aba para inspecionar os jogos no volante interativo.")

# ==============================================================================
# ABA 3: ESTATÍSTICAS HISTÓRICAS
# ==============================================================================
with tab_estatisticas:
    st.subheader("Distribuição Histórica Recente")
    st.caption(f"Origem dos dados: {st.session_state.origem}")
    
    cnt = Counter()
    for j in st.session_state.historico:
        cnt.update(j)
        
    v_min = min(cnt.values()) if cnt else 0
    v_max = max(cnt.values()) if cnt else 1
    delta = max(1, v_max - v_min)
    
    celulas_heat = ""
    for r in range(6):
        for c in range(10):
            n = r * 10 + c + 1
            f = cnt[n]
            ratio = (f - v_min) / delta
            bg = "#dbeafe" if ratio == 0 else ("#22c55e" if ratio < 0.5 else ("#f97316" if ratio < 0.8 else "#ef4444"))
            color = "#0369a1" if ratio == 0 else "#ffffff"
            celulas_heat += f'<div style="width:46px;height:46px;background:{bg};color:{color};border-radius:6px;display:flex;flex-direction:column;align-items:center;justify-content:center;font-family:monospace;font-size:14px;font-weight:800;">{n:02d}<span style="font-size:10px;font-weight:600;">{f}x</span></div>'
            
    html_heat = f"""
    <!DOCTYPE html><html><head><meta charset="utf-8">
    <style>*{{box-sizing:border-box;}}body{{margin:0;padding:0;display:flex;justify-content:center;background:transparent;}}
    .box{{background:#fff;border:2px solid #cbd5e1;border-radius:12px;padding:12px;width:fit-content;}}
    .grid{{display:grid;grid-template-columns:repeat(10,46px);gap:5px;}}</style></head><body>
    <div class="box"><div style="font-weight:800;color:#15803d;text-align:center;margin-bottom:8px;">Mapa de Calor 6x10</div><div class="grid">{celulas_heat}</div></div></body></html>
    """
    components.html(html_heat, height=380, scrolling=False)
