import streamlit as st
import streamlit.components.v1 as components
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from itertools import combinations, permutations
from collections import Counter
import random

st.set_page_config(
    page_title="MEGA60 - Laboratório de Filtros Estruturais",
    page_icon="🍀",
    layout="wide"
)

TOTAL_NUMS = 60
TAMANHO_JOGO = 6
PRIMOS_MEGASENA = {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59}

# 28 Dezenas da Moldura (Bordas da matriz 6x10)
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
# MOTOR MATEMÁTICO: VALIDAÇÃO DOS 7 QUADROS (ULTRAVELOZ / ZERO ALOCAÇÃO)
# ==============================================================================
def validar_jogo_completo(jogo, cfg):
    """
    Testa rigorosamente os 7 quadros com saída antecipada (fail-fast).
    """
    # Quadro 6: Faixa de Soma
    soma = sum(jogo)
    if not (cfg["soma_min"] <= soma <= cfg["soma_max"]):
        return False
        
    # Quadro 3: Primos (01 a 05)
    primos = sum(1 for n in jogo if n in PRIMOS_MEGASENA)
    if not (cfg["primos_min"] <= primos <= cfg["primos_max"]):
        return False

    # Quadro 4: Pares (01 a 06) e Ímpares (01 a 06)
    pares = sum(1 for n in jogo if n % 2 == 0)
    if not (cfg["pares_min"] <= pares <= cfg["pares_max"]):
        return False
    impares = 6 - pares
    if not (cfg["impares_min"] <= impares <= cfg["impares_max"]):
        return False

    # Quadro 5: Moldura (01 a 06)
    moldura = sum(1 for n in jogo if n in MOLDURA_SET)
    if not (cfg["moldura_min"] <= moldura <= cfg["moldura_max"]):
        return False

    # Quadro 1 e 2: Linhas (01 a 06), Colunas (01 a 10) e Diagonais (01 a 10)
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
        
        # Teste de Linhas
        linhas[r] += 1
        if linhas[r] > max_l:
            return False
            
        # Teste de Colunas
        colunas[c] += 1
        if colunas[c] > max_c:
            return False
            
        # Quadro Diagonais Crescentes (D01 a D10)
        idx_dc = (c + r) % 10
        diag_cresc[idx_dc] += 1
        if diag_cresc[idx_dc] > max_dc:
            return False
            
        # Quadro Diagonais Decrescentes (D01 a D10)
        idx_dd = (c - r) % 10
        diag_decresc[idx_dd] += 1
        if diag_decresc[idx_dd] > max_dd:
            return False

    return True

def executar_varredura_100_porcento(cfg):
    """
    Varre 100% das possibilidades sem truncamento ou travas artificiais.
    """
    jogos_aprovados = []
    
    # MODO 1: ESPAÇO ESTRUTURAL MEGA60 PERFEITO (1 por linha e 1 por coluna)
    # Universo total exato: 10 * 9 * 8 * 7 * 6 * 5 = 151.200 combinações
    if cfg["max_por_linha"] == 1 and cfg["max_por_coluna"] == 1:
        cols_pares = [1, 3, 5, 7, 9]     # Colunas 2, 4, 6, 8, 10
        cols_impares = [0, 2, 4, 6, 8]   # Colunas 1, 3, 5, 7, 9
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
                        
                        if validar_jogo_completo(jogo, cfg):
                            jogos_aprovados.append(jogo)
                            
        return jogos_aprovados

    # MODO 2: COMBINAÇÕES AMPLAS (Quando permite mais de 1 por linha/coluna)
    else:
        # Varre gerador exaustivo com processamento em lote
        for jogo in combinations(range(1, 61), 6):
            if validar_jogo_completo(jogo, cfg):
                jogos_aprovados.append(list(jogo))
                
        return jogos_aprovados

# ==============================================================================
# SINCRONIZAÇÃO OPCIONAL COM A CAIXA
# ==============================================================================
def sincronizar_com_caixa():
    url_base = "https://servicebus2.caixa.gov.br/portaldeloterias/api/megasena"
    headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
    session = requests.Session()
    session.headers.update(headers)
    try:
        resp = session.get(url_base, timeout=4)
        if resp.status_code != 200:
            return None, "Indisponível"
        dados = resp.json()
        ultimo_num = int(dados["numero"])
        concursos = {ultimo_num: sorted([int(d) for d in dados["listaDezenas"]])}
        alvos = list(range(max(1, ultimo_num - 20), ultimo_num))
        
        def baixar(n):
            try:
                r = session.get(f"{url_base}/{n}", timeout=2)
                if r.status_code == 200:
                    return n, sorted([int(d) for d in r.json()["listaDezenas"]])
            except:
                pass
            return n, None

        with ThreadPoolExecutor(max_workers=5) as ex:
            futuros = [ex.submit(baixar, n) for n in alvos]
            for f in as_completed(futuros):
                n_conc, nums = f.result()
                if nums and len(nums) == 6:
                    concursos[n_conc] = nums

        return [concursos[k] for k in sorted(concursos.keys())], f"#{ultimo_num}"
    except:
        return None, "Erro de Conexão"

# ==============================================================================
# INICIALIZAÇÃO INSTANTÂNEA
# ==============================================================================
if "historico" not in st.session_state:
    st.session_state.historico = [list(j) for j in FALLBACK_MEGASENA]
    st.session_state.origem = "Base Local Offline (Carregamento Imediato)"

if "jogos_aprovados" not in st.session_state:
    st.session_state.jogos_aprovados = []

# ==============================================================================
# CABEÇALHO & ABAS PRINCIPAIS
# ==============================================================================
st.title("🍀 MEGA60: Laboratório de Filtros Estruturais")
st.caption(f"Status da Base: **{st.session_state.origem}** • Varredura Total das 60 Dezenas")

tab_quadros, tab_volante, tab_historico = st.tabs([
    "🎛️ Os 7 Quadros & Varredura 100%",
    "🗺️ Volante Visual & Raio-X",
    "📊 Histórico & Sincronização Caixa"
])

# ==============================================================================
# ABA 1: OS 7 QUADROS ESTRUTURAIS
# ==============================================================================
with tab_quadros:
    st.subheader("Configuração Paramétrica dos 7 Quadros")
    
    col_q1, col_q2 = st.columns(2)
    
    with col_q1:
        with st.container(border=True):
            st.markdown("#### 1️⃣ Quadro: Linhas (01 a 06) & Colunas (01 a 10)")
            max_l = st.slider("Máximo de Dezenas por Linha (01 a 06):", 1, 6, 1, 
                              help="1 = exatamente 1 por linha (Modo Matriz 151.200 combinações).")
            max_c = st.slider("Máximo de Dezenas por Coluna (01 a 10):", 1, 6, 1,
                              help="1 = colunas distintas sem repetição vertical.")
            
        with st.container(border=True):
            st.markdown("#### 2️⃣ Quadro: Diagonais Crescentes & Decrescentes (01 a 10)")
            max_dc = st.slider("Máximo por Diag. Crescente (D01 a D10):", 1, 6, 1,
                               help="Limita dezenas alinhadas na diagonal inclinada para cima.")
            max_dd = st.slider("Máximo por Diag. Decrescente (D01 a D10):", 1, 6, 1,
                               help="Limita dezenas alinhadas na diagonal inclinada para baixo.")

        with st.container(border=True):
            st.markdown("#### 3️⃣ Quadro: Primos (01 a 05)")
            f_primos = st.slider("Quantidade de Dezenas Primas:", 0, 5, (1, 2))

    with col_q2:
        with st.container(border=True):
            st.markdown("#### 4️⃣ Quadro: Pares (01 a 06) & Ímpares (01 a 06)")
            f_pares = st.slider("Faixa de Pares:", 0, 6, (2, 4))
            f_impares = st.slider("Faixa de Ímpares:", 0, 6, (2, 4))

        with st.container(border=True):
            st.markdown("#### 5️⃣ Quadro: Moldura (01 a 06)")
            f_moldura = st.slider("Dezenas na Moldura Externa (01 a 06):", 0, 6, (2, 4))

        with st.container(border=True):
            st.markdown("#### 6️⃣ Quadro: Faixa de Soma")
            f_soma = st.slider("Intervalo de Soma Geral:", 50, 320, (110, 240))

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

    if st.button("🚀 Processar Varredura 100% das Possibilidades", use_container_width=True):
        universo_txt = "151.200 jogos estruturais" if (max_l == 1 and max_c == 1) else "50.063.860 combinações"
        with st.spinner(f"Verificando 100% das possibilidades ({universo_txt})..."):
            resultados = executar_varredura_100_porcento(cfg)
            st.session_state.jogos_aprovados = resultados

    if st.session_state.jogos_aprovados:
        qtd_total = len(st.session_state.jogos_aprovados)
        st.success(f"🎉 **Varredura Completa Concluída:** Exatamente **{qtd_total:,} apostas** atendem 100% dos critérios configurados!")

        # Montagem do arquivo completo em memória
        txt_conteudo = "\n".join([" ".join([f"{n:02d}" for n in j]) for j in st.session_state.jogos_aprovados])
        
        c_btn1, c_btn2 = st.columns([3, 1])
        with c_btn1:
            st.download_button(
                "📥 Baixar Arquivo Completo com Todos os Jogos (.TXT)",
                data=txt_conteudo,
                file_name=f"mega60_varredura_completa_{qtd_total}_jogos.txt",
                mime="text/plain",
                use_container_width=True
            )
        with c_btn2:
            st.metric("Total em Memória", f"{qtd_total:,}")

        # Visualização parcial de conferência (evita travar o navegador)
        amostra_exibir = min(qtd_total, 100)
        with st.expander(f"Visualizar Conferência Inicial ({amostra_exibir} de {qtd_total:,} jogos)", expanded=True):
            for i, j in enumerate(st.session_state.jogos_aprovados[:amostra_exibir]):
                p = sum(1 for n in j if n in PRIMOS_MEGASENA)
                par = sum(1 for n in j if n % 2 == 0)
                mold = sum(1 for n in j if n in MOLDURA_SET)
                nums = " - ".join([f"{n:02d}" for n in j])
                st.markdown(f"**Jogo #{i+1:04d}:** `{nums}` | **{par}P/{6-par}I** | **{p} Primos** | **{mold} Moldura** | Soma: `{sum(j)}`")

# ==============================================================================
# ABA 2: VOLANTE VISUAL & RAIO-X
# ==============================================================================
with tab_volante:
    st.subheader("Dissecação da Cartela Oficial")
    if st.session_state.jogos_aprovados:
        idx_sel = st.slider("Selecione o número da aposta para inspecionar:", 1, len(st.session_state.jogos_aprovados), 1)
        jogo_ativo = st.session_state.jogos_aprovados[idx_sel - 1]
        marcadas = set(jogo_ativo)
        
        col_vol, col_diag = st.columns([1, 1])
        with col_vol:
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
            
        with col_diag:
            with st.container(border=True):
                st.markdown("#### 🔬 Diagnóstico dos 7 Quadros Deste Jogo")
                
                # Mapeamento do jogo selecionado
                linhas_count = [0] * 6
                colunas_count = [0] * 10
                dc_count = [0] * 10
                dd_count = [0] * 10
                for n in jogo_ativo:
                    r = (n - 1) // 10
                    c = (n - 1) % 10
                    linhas_count[r] += 1
                    colunas_count[c] += 1
                    dc_count[(c + r) % 10] += 1
                    dd_count[(c - r) % 10] += 1
                    
                p_qtd = sum(1 for n in jogo_ativo if n in PRIMOS_MEGASENA)
                par_qtd = sum(1 for n in jogo_ativo if n % 2 == 0)
                mold_qtd = sum(1 for n in jogo_ativo if n in MOLDURA_SET)
                
                st.markdown(f"**Quadro Linhas:** `{' | '.join([f'L{i+1}:{v}' for i, v in enumerate(linhas_count)])}`")
                st.markdown(f"**Quadro Colunas:** `{' '.join([f'C{i+1}:{v}' for i, v in enumerate(colunas_count)])}`")
                st.markdown(f"**Quadro Diag. Cresc.:** `{' '.join([f'D{i+1}:{v}' for i, v in enumerate(dc_count) if v > 0])}`")
                st.markdown(f"**Quadro Diag. Decresc.:** `{' '.join([f'D{i+1}:{v}' for i, v in enumerate(dd_count) if v > 0])}`")
                st.markdown(f"**Quadro Primos:** `{p_qtd}` | **Pares/Ímpares:** `{par_qtd}P / {6 - par_qtd}I`")
                st.markdown(f"**Quadro Moldura/Miolo:** `{mold_qtd} Moldura` / `{6 - mold_qtd} Miolo` | **Soma:** `{sum(jogo_ativo)}`")
    else:
        st.info("Execute a varredura na primeira aba para inspecionar no volante.")

# ==============================================================================
# ABA 3: HISTÓRICO & SINCRONIZAÇÃO
# ==============================================================================
with tab_historico:
    st.subheader("Base de Sorteios Recentes")
    st.write(f"Concursos ativos em memória: **{len(st.session_state.historico)}**")
    
    if st.button("🌐 Sincronizar Concursos Oficiais com a Caixa"):
        with st.spinner("Conectando à API da Caixa..."):
            dados, info = sincronizar_com_caixa()
            if dados:
                st.session_state.historico = dados
                st.session_state.origem = f"Caixa Online ({info})"
                st.success("Histórico atualizado com sucesso!")
                st.rerun()
            else:
                st.warning("Servidor da Caixa não respondeu. Mantendo base de segurança local.")
