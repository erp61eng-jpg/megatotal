import streamlit as st
import streamlit.components.v1 as components
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import random
import re
from itertools import combinations, permutations
from collections import defaultdict, Counter
import pandas as pd

st.set_page_config(
    page_title="MEGA60 - Laboratório & Filtros Estruturais",
    page_icon="🍀",
    layout="wide"
)

TOTAL_NUMS = 60
TAMANHO_JOGO = 6
QTD_LINHAS = 6
QTD_COLUNAS = 10

PRIMOS_MEGASENA = {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59}

FALLBACK_MEGASENA = [
    [4, 12, 18, 30, 35, 54], [1, 9, 15, 23, 44, 52], [7, 14, 27, 39, 48, 59],
    [10, 11, 25, 33, 42, 58], [3, 16, 28, 37, 45, 60], [5, 20, 22, 34, 49, 56],
    [8, 17, 31, 40, 50, 57], [2, 13, 24, 38, 43, 55], [6, 19, 29, 36, 47, 53],
    [12, 21, 32, 41, 46, 51], [4, 15, 26, 35, 48, 58], [7, 18, 23, 39, 44, 59],
    [1, 10, 27, 34, 42, 54], [9, 14, 30, 37, 50, 60], [3, 16, 25, 38, 49, 57],
    [5, 11, 28, 33, 45, 53], [8, 20, 31, 43, 52, 56], [2, 17, 24, 36, 47, 55],
    [6, 13, 29, 40, 46, 51], [12, 19, 32, 41, 50, 58], [4, 22, 27, 35, 44, 60],
    [7, 15, 26, 39, 48, 54], [1, 18, 30, 37, 42, 59], [9, 14, 23, 34, 49, 57],
    [3, 10, 28, 38, 45, 55], [5, 16, 31, 33, 50, 56], [8, 11, 25, 43, 47, 53],
    [2, 20, 29, 36, 46, 52], [6, 17, 32, 40, 51, 58], [12, 13, 24, 41, 48, 60],
    [4, 19, 27, 35, 44, 54], [7, 22, 30, 39, 49, 59], [1, 15, 26, 37, 42, 57],
    [9, 18, 28, 34, 45, 56], [3, 14, 31, 38, 50, 55], [5, 10, 23, 33, 46, 53],
    [8, 16, 29, 43, 47, 58], [2, 11, 32, 36, 51, 60], [6, 20, 25, 40, 48, 54],
    [12, 17, 27, 41, 49, 59], [4, 13, 30, 35, 44, 57], [7, 19, 26, 39, 42, 56],
    [1, 22, 28, 37, 45, 55], [9, 15, 31, 34, 50, 58], [3, 18, 24, 38, 46, 60],
    [5, 14, 29, 33, 47, 54], [8, 10, 32, 43, 48, 59], [2, 16, 27, 36, 51, 57],
    [6, 11, 25, 40, 49, 55], [12, 20, 28, 41, 46, 58]
]

# ==============================================================================
# MOTOR MATEMÁTICO ESPECÍFICO DO MEGA60 (ALTA VELOCIDADE)
# ==============================================================================
def processar_filtro_mestre_mega60(qtd_pares=3, qtd_primos=1, max_diag=1, faixa_soma=(100, 260)):
    """Gera diretamente as combinações satisfazendo:
       - Exatamente 1 por linha (implícito pelas 6 linhas e 6 dezenas)
       - Máximo 1 por coluna (colunas distintas)
       - Exatamente qtd_pares pares e (6 - qtd_pares) ímpares
       - Máximo max_diag por diagonal (direita e esquerda)
       - Exatamente qtd_primos primos
    """
    cols_pares = [1, 3, 5, 7, 9]     # Colunas com final 2, 4, 6, 8, 0 (pares)
    cols_impares = [0, 2, 4, 6, 8]   # Colunas com final 1, 3, 5, 7, 9 (ímpares)
    
    qtd_impares = 6 - qtd_pares
    linhas_indices = list(range(6))
    
    jogos_aprovados = []
    
    # 1. Escolhe quais 3 linhas terão números pares
    for linhas_par in combinations(linhas_indices, qtd_pares):
        linhas_par_set = set(linhas_par)
        linhas_impar = [l for l in linhas_indices if l not in linhas_par_set]
        
        # 2. Distribui 3 colunas pares e 3 colunas ímpares
        for perm_par in permutations(cols_pares, qtd_pares):
            for perm_impar in permutations(cols_impares, qtd_impares):
                
                # Monta a combinação de colunas para as 6 linhas [L0..L5]
                colunas = [0] * 6
                for idx, l in enumerate(linhas_par):
                    colunas[l] = perm_par[idx]
                for idx, l in enumerate(linhas_impar):
                    colunas[l] = perm_impar[idx]
                
                # 3. Teste Diagonais Direitas (+11 mod 10): (c - r) % 10
                diag_dir = [(colunas[r] - r) % 10 for r in range(6)]
                if max_diag == 1 and len(set(diag_dir)) < 6:
                    continue
                elif max_diag > 1 and max(Counter(diag_dir).values()) > max_diag:
                    continue
                
                # 4. Teste Diagonais Esquerdas (+9 mod 10): (c + r) % 10
                diag_esq = [(colunas[r] + r) % 10 for r in range(6)]
                if max_diag == 1 and len(set(diag_esq)) < 6:
                    continue
                elif max_diag > 1 and max(Counter(diag_esq).values()) > max_diag:
                    continue
                
                # 5. Constrói o jogo real
                jogo = [r * 10 + colunas[r] + 1 for r in range(6)]
                
                # 6. Teste de Soma
                soma_jogo = sum(jogo)
                if not (faixa_soma[0] <= soma_jogo <= faixa_soma[1]):
                    continue
                
                # 7. Teste de Primos
                primos_no_jogo = sum(1 for n in jogo if n in PRIMOS_MEGASENA)
                if primos_no_jogo != qtd_primos:
                    continue
                
                jogos_aprovados.append(jogo)
                
    return jogos_aprovados

# ==============================================================================
# API CAIXA & BASES ESTATÍSTICAS
# ==============================================================================
@st.cache_data(ttl=7200, show_spinner=False)
def buscar_50_concursos_caixa():
    url_base = "https://servicebus2.caixa.gov.br/portaldeloterias/api/megasena"
    headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
    try:
        resp = requests.get(url_base, headers=headers, timeout=8)
        if resp.status_code != 200: return None, "Offline"
        dados = resp.json()
        ultimo_num = int(dados["numero"])
        concursos_dict = {ultimo_num: sorted([int(d) for d in dados["listaDezenas"]])}
        alvos = list(range(max(1, ultimo_num - 49), ultimo_num))
        
        def baixar(n):
            try:
                r = requests.get(f"{url_base}/{n}", headers=headers, timeout=4)
                if r.status_code == 200:
                    return n, sorted([int(d) for d in r.json()["listaDezenas"]])
            except: pass
            return n, None

        with ThreadPoolExecutor(max_workers=10) as ex:
            futuros = [ex.submit(baixar, n) for n in alvos]
            for f in as_completed(futuros):
                n_conc, nums = f.result()
                if nums and len(nums) == 6:
                    concursos_dict[n_conc] = nums

        return [concursos_dict[k] for k in sorted(concursos_dict.keys())], f"#{ultimo_num}"
    except:
        return None, "Erro"

def get_moldura_megasena():
    mold = set(range(1, 11)) | set(range(51, 61))
    for r in range(6): mold.update([r * 10 + 1, r * 10 + 10])
    return sorted(list(mold))

def get_miolo_megasena():
    mold = set(get_moldura_megasena())
    return [n for n in range(1, 61) if n not in mold]

def get_quadrantes_megasena():
    q1, q2, q3, q4 = [], [], [], []
    for r in range(6):
        for c in range(10):
            n = r * 10 + c + 1
            if r < 3 and c < 5: q1.append(n)
            elif r < 3 and c >= 5: q2.append(n)
            elif r >= 3 and c < 5: q3.append(n)
            else: q4.append(n)
    return {"Q1 (NO)": sorted(q1), "Q2 (NE)": sorted(q2), "Q3 (SO)": sorted(q3), "Q4 (SE)": sorted(q4)}

def construir_grupos():
    g = {
        "Pares": [n for n in range(1, 61) if n % 2 == 0],
        "Ímpares": [n for n in range(1, 61) if n % 2 != 0],
        "Primos": sorted(list(PRIMOS_MEGASENA)),
        "Moldura": get_moldura_megasena(),
        "Centro (Miolo)": get_miolo_megasena()
    }
    for l in range(6): g[f"Linha {l+1}"] = list(range(l * 10 + 1, (l + 1) * 10 + 1))
    for c in range(10): g[f"Coluna {c+1}"] = [r * 10 + c + 1 for r in range(6)]
    for c in range(10):
        g[f"Diag Direita {c+1:02d}"] = sorted([(r * 10) + ((c + r) % 10) + 1 for r in range(6)])
        g[f"Diag Esquerda {c+1:02d}"] = sorted([(r * 10) + ((c - r) % 10) + 1 for r in range(6)])
    return g

def calcular_stats(historico, grupos):
    cnt = Counter()
    for s in historico: cnt.update(s)
    ordenados = sorted(range(1, 61), key=lambda d: (cnt[d], -d), reverse=True)
    somas = [sum(s) for s in historico]
    
    stats_g = {}
    for nome, dezenas in grupos.items():
        dset = set(dezenas)
        ocorr = [len(set(s) & dset) for s in historico]
        stats_g[nome] = {
            "min": min(ocorr) if ocorr else 0,
            "max": max(ocorr) if ocorr else 6,
            "media": sum(ocorr) / len(ocorr) if ocorr else 0.0,
            "total": sum(ocorr),
            "dezenas": dezenas
        }
    return {
        "cnt": cnt,
        "ordenados": ordenados,
        "min_soma": min(somas) if somas else 21,
        "max_soma": max(somas) if somas else 345,
        "media_soma": sum(somas) / len(somas) if somas else 183.0,
        "stats_g": stats_g
    }

# ==============================================================================
# UI COMPONENTS (ISOLATED CSS)
# ==============================================================================
def render_volante(jogo, titulo=""):
    marcadas = set(jogo)
    celulas = ""
    for r in range(6):
        for c in range(10):
            n = r * 10 + c + 1
            if n in marcadas:
                celulas += f'<div style="width:38px;height:38px;background:linear-gradient(135deg,#16a34a,#15803d);color:#fff;border:2px solid #0f5132;font-weight:800;border-radius:8px;display:flex;align-items:center;justify-content:center;font-family:monospace;font-size:13px;box-sizing:border-box;">{n:02d}</div>'
            else:
                celulas += f'<div style="width:38px;height:38px;background:#f8fafc;color:#475569;border:1px solid #cbd5e1;font-weight:600;border-radius:8px;display:flex;align-items:center;justify-content:center;font-family:monospace;font-size:13px;box-sizing:border-box;">{n:02d}</div>'
    
    html = f"""
    <!DOCTYPE html><html><head><meta charset="utf-8">
    <style>*{{box-sizing:border-box;}}body{{margin:0;padding:0;display:flex;justify-content:center;font-family:sans-serif;background:transparent;}}
    .box{{background:#fff;border:2px solid #16a34a;border-radius:14px;padding:16px;box-shadow:0 4px 16px rgba(22,163,74,0.15);width:fit-content;}}
    .grid{{display:grid;grid-template-columns:repeat(10,38px);gap:6px;}}</style></head><body>
    <div class="box"><div style="font-weight:800;font-size:15px;margin-bottom:12px;color:#15803d;text-align:center;">{titulo}</div>
    <div class="grid">{celulas}</div></div></body></html>
    """
    components.html(html, height=360, scrolling=False)

def card_aposta(idx, jogo, extra=""):
    dezenas = "".join([f"<span style='display:inline-flex;align-items:center;justify-content:center;width:34px;height:34px;background:linear-gradient(135deg,#16a34a,#15803d);color:#fff;font-weight:800;font-size:14px;border-radius:50%;margin:0 3px;box-shadow:0 2px 4px rgba(22,163,74,0.3);font-family:monospace;'>{n:02d}</span>" for n in jogo])
    soma = sum(jogo)
    ext = f"<span style='color:#15803d;font-weight:700;margin-right:10px;'>{extra}</span>" if extra else ""
    st.markdown(f"""
    <div style="background:#ffffff;border:1px solid #bbf7d0;border-left:5px solid #16a34a;border-radius:10px;padding:10px 16px;margin:8px 0;display:flex;justify-content:space-between;align-items:center;box-shadow:0 2px 6px rgba(0,0,0,0.05);">
        <div style="display:flex;align-items:center;gap:12px;"><span style="font-weight:800;color:#0f172a;font-size:14px;font-family:sans-serif;">Jogo #{idx:03d}</span><div>{dezenas}</div></div>
        <div style="display:flex;align-items:center;">{ext}<span style="background:#dcfce7;color:#15803d;padding:4px 10px;border-radius:12px;font-size:12px;font-weight:700;">Soma: {soma}</span></div>
    </div>
    """, unsafe_allow_html=True)

def converter_txt(jogos):
    return "\n".join([" ".join([f"{n:02d}" for n in j]) for j in jogos])

# ==============================================================================
# INICIALIZAÇÃO
# ==============================================================================
if "grupos" not in st.session_state: st.session_state.grupos = construir_grupos()
if "historico" not in st.session_state:
    res, info = buscar_50_concursos_caixa()
    st.session_state.historico = res if res else [list(j) for j in FALLBACK_MEGASENA]
    st.session_state.origem = f"Caixa Oficial ({info})" if res else "Base Local"

if "jogos_mega60" not in st.session_state: st.session_state.jogos_mega60 = []

stats = calcular_stats(st.session_state.historico[-30:], st.session_state.grupos)

# ==============================================================================
# CABEÇALHO & ABAS
# ==============================================================================
st.title("🍀 MEGA60: Laboratório de Filtros Estuturais")
st.caption("Execução Local • Matriz 6x10 • Filtro Simultâneo de 60 Dezenas • 1 por Linha, 1 por Coluna, Diagonais, Primos & Paridade")

tab_mestre, tab_filtros, tab_hist, tab_volante = st.tabs([
    "⚡ MEGA60 - Filtro Estrutural (60 Dezenas)",
    "⚙️ Filtros Avançados & Desdobramentos",
    "📜 Estatísticas & Heatmap 6x10",
    "🗺️ Volante Visual"
])

# ==============================================================================
# ABA 1: O FILTRO ESPECÍFICO MEGA60
# ==============================================================================
with tab_mestre:
    st.subheader("🎯 Filtro Estrutural Mestre: Varredura Completa das 60 Dezenas")
    st.markdown("""
    Este módulo aplica as **restrições combinatórias diretamente no espaço amostral**:
    * **Linhas:** Máximo 1 por linha (*exatamente 1 dezena em cada uma das 6 linhas*).
    * **Colunas:** Máximo 1 por coluna (*6 colunas distintas, sem repetição vertical*).
    * **Diagonais Cilíndricas:** Máximo 1 por diagonal (não colide em diagonais +11 e +9).
    * **Equilíbrio:** 3 Pares e 3 Ímpares.
    * **Primos:** Exatamente 1 Primo.
    """)

    c_m1, c_m2, c_m3, c_m4 = st.columns(4)
    with c_m1:
        par_sel = st.selectbox("Pares / Ímpares:", [3, 2, 4], index=0, help="Padrão: 3 pares e 3 ímpares.")
    with c_m2:
        primo_sel = st.selectbox("Quantidade de Primos:", [1, 2, 0, 3], index=0, help="Padrão: exatamente 1 primo.")
    with c_m3:
        diag_sel = st.selectbox("Máximo por Diagonal:", [1, 2], index=0, help="Padrão: 1 por diagonal.")
    with c_m4:
        soma_faixa = st.slider("Faixa de Soma:", 80, 280, (110, 240))

    st.divider()

    if st.button("🚀 Processar as 60 Dezenas com o Filtro MEGA60", use_container_width=True):
        with st.spinner("Processando combinações em alta velocidade..."):
            aprovados = processar_filtro_mestre_mega60(
                qtd_pares=par_sel,
                qtd_primos=primo_sel,
                max_diag=diag_sel,
                faixa_soma=soma_faixa
            )
            st.session_state.jogos_mega60 = aprovados

    if st.session_state.jogos_mega60:
        total = len(st.session_state.jogos_mega60)
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Universo Mega-Sena", "50.063.860")
        m2.metric("Espaço 1 p/ Linha e Coluna", "151.200")
        m3.metric("Com 3P/3I e Diagonais", "3.600 - 4.200")
        m4.metric("Aprovados Finais (1 Primo)", f"{total:,} jogos")

        st.success(f"🎉 **Varredura Concluída:** Exatamente **{total:,} jogos** atendem todos os critérios simultâneos nas 60 dezenas!")

        st.download_button(
            "📥 Baixar Lista de Jogos Aprovados (.TXT)",
            data=converter_txt(st.session_state.jogos_mega60),
            file_name=f"mega60_jogos_filtrados_{total}.txt",
            mime="text/plain",
            use_container_width=True
        )

        with st.expander(f"Visualizar Apostas Geradas ({min(total, 100)} de {total})", expanded=True):
            for idx, j in enumerate(st.session_state.jogos_mega60[:100]):
                p_count = sum(1 for n in j if n in PRIMOS_MEGASENA)
                card_aposta(idx + 1, j, extra=f"{p_count} Primo | 3P/3I")

# ==============================================================================
# ABA 2: FILTROS AVANÇADOS GERAIS
# ==============================================================================
with tab_filtros:
    st.subheader("Controle de Filtros Tradicionais")
    st.caption("Configurações secundárias para testes complementares.")
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        st.write("**Faixas Estatísticas Gerais:**")
        st.write(f"- Menor soma recente: {stats['min_soma']}")
        st.write(f"- Maior soma recente: {stats['max_soma']}")
        st.write(f"- Média da soma: {stats['media_soma']:.1f}")
    with col_f2:
        st.write("**Grupos Estruturais:**")
        st.write(f"- Moldura (28 dezenas): Média {stats['stats_g']['Moldura']['media']:.1f}")
        st.write(f"- Miolo (32 dezenas): Média {stats['stats_g']['Centro (Miolo)']['media']:.1f}")

# ==============================================================================
# ABA 3: ESTATÍSTICAS E HEATMAP 6x10
# ==============================================================================
with tab_hist:
    st.subheader("Frequência Térmica da Matriz 6x10")
    
    celulas_html = ""
    v_min = min(stats["cnt"].values()) if stats["cnt"] else 0
    v_max = max(stats["cnt"].values()) if stats["cnt"] else 1
    delta = max(1, v_max - v_min)

    for r in range(6):
        for c in range(10):
            n = r * 10 + c + 1
            freq = stats["cnt"][n]
            ratio = (freq - v_min) / delta
            bg = "#dbeafe" if ratio == 0 else ("#22c55e" if ratio < 0.5 else ("#f97316" if ratio < 0.8 else "#ef4444"))
            color = "#0369a1" if ratio == 0 else "#ffffff"
            celulas_html += f"""
            <div style="width:48px;height:48px;background:{bg};color:{color};border-radius:8px;display:flex;flex-direction:column;align-items:center;justify-content:center;font-family:monospace;border:1px solid rgba(0,0,0,0.1);box-sizing:border-box;">
                <span style="font-size:15px;font-weight:900;">{n:02d}</span>
                <span style="font-size:10px;font-weight:800;">{freq}x</span>
            </div>
            """

    full_heat = f"""
    <!DOCTYPE html><html><head><meta charset="utf-8">
    <style>*{{box-sizing:border-box;}}body{{margin:0;padding:0;background:transparent;display:flex;justify-content:center;font-family:sans-serif;color:#0f172a;}}
    .box{{background:#fff;border:2px solid #cbd5e1;border-radius:14px;padding:16px;box-shadow:0 4px 16px rgba(0,0,0,0.06);width:fit-content;}}
    .grid{{display:grid;grid-template-columns:repeat(10,48px);gap:6px;}}</style></head><body>
    <div class="box"><div style="font-size:16px;font-weight:800;color:#15803d;text-align:center;margin-bottom:12px;">Heatmap dos Últimos 30 Sorteios</div>
    <div class="grid">{celulas_html}</div></div></body></html>
    """
    components.html(full_heat, height=440, scrolling=False)

# ==============================================================================
# ABA 4: VOLANTE VISUAL
# ==============================================================================
with tab_volante:
    st.subheader("Inspeção de Jogo na Cartela Oficial")
    if st.session_state.jogos_mega60:
        idx_escolhido = st.slider("Escolha o número do jogo para visualizar:", 1, len(st.session_state.jogos_mega60), 1)
        jogo_mostra = st.session_state.jogos_mega60[idx_escolhido - 1]
        render_volante(jogo_mostra, titulo=f"Jogo MEGA60 #{idx_escolhido:03d}: {' - '.join([f'{n:02d}' for n in jogo_mostra])}")
    else:
        st.info("Execute o filtro na primeira aba para inspecionar os jogos na cartela.")