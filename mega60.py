import streamlit as st
import streamlit.components.v1 as components
import requests
from itertools import combinations
from collections import Counter
import math
import time
import re
import json
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(
    page_title="MEGA60 - Cartela Virtual, Filtros & Sistema de Elliott",
    page_icon="🍀",
    layout="wide"
)

# ==============================================================================
# CONSTANTES E ESTRUTURA DA MATRIZ 6x10
# ==============================================================================
TOTAL_NUMS = 60
TAMANHO_JOGO_FINAL = 6
FIBONACCI_MEGASENA = {1, 2, 3, 5, 8, 13, 21, 34, 55}
PRIMOS_MEGASENA = {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59}

MOLDURA_SET = (
    set(range(1, 11)) |
    set(range(51, 61)) |
    {r * 10 + 1 for r in range(6)} |
    {r * 10 + 10 for r in range(6)}
)

DEZENAS_BASE_3010 = {5, 9, 16, 40, 41, 59}

FALLBACK_MEGASENA = [
    [4, 12, 18, 30, 35, 54], [1, 9, 15, 23, 44, 52], [7, 14, 27, 39, 48, 59],
    [10, 11, 25, 33, 42, 58], [3, 16, 28, 37, 45, 60], [5, 20, 22, 34, 49, 56],
    [8, 17, 31, 40, 50, 57], [2, 13, 24, 38, 43, 55], [6, 19, 29, 36, 47, 53],
    [12, 21, 32, 41, 46, 51], [4, 15, 26, 35, 48, 58], [7, 18, 23, 39, 44, 59],
    [1, 10, 27, 34, 42, 54], [9, 14, 30, 37, 50, 60], [3, 16, 25, 38, 49, 57],
    [5, 11, 28, 33, 45, 53], [8, 20, 31, 43, 52, 56], [2, 17, 24, 36, 47, 55],
    [6, 13, 29, 40, 46, 51], [12, 19, 32, 41, 50, 58]
]

PAR_LOOKUP = [False] + [(n % 2 == 0) for n in range(1, 61)]
PRIMO_LOOKUP = [False] + [(n in PRIMOS_MEGASENA) for n in range(1, 61)]
MOLDURA_LOOKUP = [False] + [(n in MOLDURA_SET) for n in range(1, 61)]
ROW_LOOKUP = [0] + [(n - 1) // 10 for n in range(1, 61)]
COL_LOOKUP = [0] + [(n - 1) % 10 for n in range(1, 61)]
DC_LOOKUP = [0] + [(((n - 1) % 10) + ((n - 1) // 10)) % 10 for n in range(1, 61)]
DD_LOOKUP = [0] + [(((n - 1) % 10) - ((n - 1) // 10)) % 10 for n in range(1, 61)]

PROPS = {}
for n in range(1, 61):
    PROPS[n] = {
        "r": ROW_LOOKUP[n],
        "c": COL_LOOKUP[n],
        "dc": DC_LOOKUP[n],
        "dd": DD_LOOKUP[n],
        "is_primo": PRIMO_LOOKUP[n],
        "is_par": PAR_LOOKUP[n],
        "is_moldura": MOLDURA_LOOKUP[n],
        "is_fib": n in FIBONACCI_MEGASENA
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

PRESETS_PADRAO = {
    "FILTRO3010": {
        "linhas": ["Exatamente 2", "Exatamente 1", "0 (Nenhuma)", "Exatamente 1", "Exatamente 1", "Exatamente 1"],
        "colunas": ["Exatamente 1", "0 (Nenhuma)", "0 (Nenhuma)", "0 (Nenhuma)", "Exatamente 1", "Exatamente 1", "0 (Nenhuma)", "0 (Nenhuma)", "Exatamente 2", "Exatamente 1"],
        "diag_cresc": ["0 (Nenhuma)", "0 (Nenhuma)", "Exatamente 1", "Exatamente 1", "Exatamente 2", "0 (Nenhuma)", "Exatamente 1", "0 (Nenhuma)", "Exatamente 1", "0 (Nenhuma)"],
        "diag_decresc": ["0 (Nenhuma)", "0 (Nenhuma)", "0 (Nenhuma)", "Exatamente 1", "Exatamente 2", "0 (Nenhuma)", "Exatamente 2", "0 (Nenhuma)", "Exatamente 1", "0 (Nenhuma)"],
        "primos": [3],
        "pares": ["2P / 4I"],
        "moldura": [5],
        "soma": (150, 190)
    },
    "FILTRO3010_DUPLAS (Gerador Aberto)": {
        "linhas": ["1 ou 2", "0 a 2", "0 a 2", "0 a 2", "0 a 2", "0 a 2"],
        "colunas": ["0 a 2"] * 10,
        "diag_cresc": ["0 a 2"] * 10,
        "diag_decresc": ["0 a 2"] * 10,
        "primos": [1, 2, 3],
        "pares": ["3P / 3I", "4P / 2I", "2P / 4I"],
        "moldura": [2, 3, 4, 5],
        "soma": (120, 245)
    },
    "MEGA60: 1 por Linha Padrão (6 Dezenas)": {
        "linhas": ["Exatamente 1"] * 6,
        "colunas": ["0 ou 1"] * 10,
        "diag_cresc": ["0 ou 1"] * 10,
        "diag_decresc": ["0 ou 1"] * 10,
        "primos": [1, 2],
        "pares": ["3P / 3I", "2P / 4I", "4P / 2I"],
        "moldura": [2, 3, 4],
        "soma": (110, 240)
    }
}

# ==============================================================================
# ENGENHARIA REVERSA: EXTRAÇÃO INDIVIDUAL E MULTICONCURSOS
# ==============================================================================
def mapear_quantidade_para_rotulo(qtd, modo="exato"):
    if modo == "exato":
        mapa = {0: "0 (Nenhuma)", 1: "Exatamente 1", 2: "Exatamente 2", 3: "Exatamente 3", 4: "Exatamente 4"}
        return mapa.get(qtd, "Livre (0 a 6)")
    return "0 a 2" if qtd <= 2 else "Livre (0 a 6)"

def mapear_intervalo_para_opcao(min_v, max_v, flexivel=False):
    if flexivel:
        min_v = max(0, min_v - 1)
        max_v = min(6, max_v + 1)
    for label, (low, high) in OPCOES_QUANTIDADE.items():
        if low == min_v and high == max_v:
            return label
    candidatos = []
    for label, (low, high) in OPCOES_QUANTIDADE.items():
        if low <= min_v and high >= max_v:
            candidatos.append((high - low, label))
    if candidatos:
        candidatos.sort(key=lambda x: x[0])
        return candidatos[0][1]
    return "Livre (0 a 6)"

def extrair_filtros_de_jogo(dezenas, modo="exato", margem_soma=25):
    dezenas = sorted(list(set(dezenas)))
    total_dezenas = len(dezenas)
    if not (6 <= total_dezenas <= 60):
        return None

    l_cnt, c_cnt = [0] * 6, [0] * 10
    dc_cnt, dd_cnt = [0] * 10, [0] * 10

    for n in dezenas:
        l_cnt[ROW_LOOKUP[n]] += 1
        c_cnt[COL_LOOKUP[n]] += 1
        dc_cnt[DC_LOOKUP[n]] += 1
        dd_cnt[DD_LOOKUP[n]] += 1

    pares_total = sum(1 for n in dezenas if PAR_LOOKUP[n])
    primos_total = sum(1 for n in dezenas if PRIMO_LOOKUP[n])
    moldura_total = sum(1 for n in dezenas if MOLDURA_LOOKUP[n])
    soma_total = sum(dezenas)

    if total_dezenas == 6:
        if modo == "exato":
            return {
                "linhas": [mapear_quantidade_para_rotulo(q, "exato") for q in l_cnt],
                "colunas": [mapear_quantidade_para_rotulo(q, "exato") for q in c_cnt],
                "diag_cresc": [mapear_quantidade_para_rotulo(q, "exato") for q in dc_cnt],
                "diag_decresc": [mapear_quantidade_para_rotulo(q, "exato") for q in dd_cnt],
                "primos": [primos_total],
                "pares": [f"{pares_total}P / {6 - pares_total}I"],
                "moldura": [moldura_total],
                "soma": (max(50, soma_total - margem_soma), min(320, soma_total + margem_soma))
            }
        else:
            primos_range = sorted(list({max(0, primos_total - 1), primos_total, min(6, primos_total + 1)}))
            moldura_range = sorted(list({max(0, moldura_total - 1), moldura_total, min(6, moldura_total + 1)}))
            pares_opcoes = list({f"{pares_total}P / {6 - pares_total}I", "3P / 3I", "4P / 2I", "2P / 4I"})
            return {
                "linhas": ["1 ou 2" if l_cnt[0] in (1, 2) else "0 a 2"] + ["0 a 2"] * 5,
                "colunas": ["0 a 2"] * 10,
                "diag_cresc": ["0 a 2"] * 10,
                "diag_decresc": ["0 a 2"] * 10,
                "primos": primos_range,
                "pares": pares_opcoes,
                "moldura": moldura_range,
                "soma": (max(50, soma_total - 30), min(320, soma_total + 30))
            }

    def converter_contagem_grupo(qtd):
        if qtd == 0: return "0 (Nenhuma)"
        elif qtd == 1: return "0 ou 1"
        elif qtd <= 3: return "0 a 2"
        elif qtd <= 5: return "1 a 3"
        return "Livre (0 a 6)"

    linhas_filt = [converter_contagem_grupo(q) for q in l_cnt]
    colunas_filt = [converter_contagem_grupo(q) for q in c_cnt]
    dc_filt = [converter_contagem_grupo(q) for q in dc_cnt]
    dd_filt = [converter_contagem_grupo(q) for q in dd_cnt]

    prop_primo = primos_total / total_dezenas
    esperado_primo = int(round(prop_primo * 6))
    primos_range = sorted(list({max(0, esperado_primo - 1), esperado_primo, min(6, esperado_primo + 1)})) or [1, 2, 3]

    prop_par = pares_total / total_dezenas
    esperado_par = max(1, min(5, int(round(prop_par * 6))))
    pares_opcoes = list({f"{esperado_par}P / {6 - esperado_par}I", "3P / 3I", "4P / 2I", "2P / 4I"})

    prop_moldura = moldura_total / total_dezenas
    esperado_moldura = int(round(prop_moldura * 6))
    moldura_range = sorted(list({max(1, esperado_moldura - 1), esperado_moldura, min(5, esperado_moldura + 1)}))

    media_dezena = soma_total / total_dezenas
    soma_esperada = int(media_dezena * 6)
    delta_soma = 40 if modo == "flexivel" else 28
    faixa_soma = (max(50, soma_esperada - delta_soma), min(320, soma_esperada + delta_soma))

    return {
        "linhas": linhas_filt,
        "colunas": colunas_filt,
        "diag_cresc": dc_filt,
        "diag_decresc": dd_filt,
        "primos": primos_range,
        "pares": pares_opcoes,
        "moldura": moldura_range,
        "soma": faixa_soma
    }

def extrair_filtros_multiconcursos(lista_sorteios, modo="preciso"):
    if not lista_sorteios:
        return None

    is_flex = modo == "flexivel"
    k_sorteios = len(lista_sorteios)

    min_l, max_l = [99] * 6, [-1] * 6
    min_c, max_c = [99] * 10, [-1] * 10
    min_dc, max_dc = [99] * 10, [-1] * 10
    min_dd, max_dd = [99] * 10, [-1] * 10

    conjunto_primos = set()
    conjunto_pares = set()
    conjunto_moldura = set()
    somas_observadas = []

    for sorteio in lista_sorteios:
        dezenas = sorted(sorteio)
        l_cnt, c_cnt = [0] * 6, [0] * 10
        dc_cnt, dd_cnt = [0] * 10, [0] * 10

        for n in dezenas:
            l_cnt[ROW_LOOKUP[n]] += 1
            c_cnt[COL_LOOKUP[n]] += 1
            dc_cnt[DC_LOOKUP[n]] += 1
            dd_cnt[DD_LOOKUP[n]] += 1

        for r in range(6):
            min_l[r] = min(min_l[r], l_cnt[r])
            max_l[r] = max(max_l[r], l_cnt[r])

        for c in range(10):
            min_c[c] = min(min_c[c], c_cnt[c])
            max_c[c] = max(max_c[c], c_cnt[c])

        for d in range(10):
            min_dc[d] = min(min_dc[d], dc_cnt[d])
            max_dc[d] = max(max_dc[d], dc_cnt[d])
            min_dd[d] = min(min_dd[d], dd_cnt[d])
            max_dd[d] = max(max_dd[d], dd_cnt[d])

        pr = sum(1 for n in dezenas if PRIMO_LOOKUP[n])
        pa = sum(1 for n in dezenas if PAR_LOOKUP[n])
        mo = sum(1 for n in dezenas if MOLDURA_LOOKUP[n])
        so = sum(dezenas)

        conjunto_primos.add(pr)
        conjunto_pares.add(f"{pa}P / {6 - pa}I")
        conjunto_moldura.add(mo)
        somas_observadas.append(so)

    linhas_filt = [mapear_intervalo_para_opcao(min_l[r], max_l[r], flexivel=is_flex) for r in range(6)]
    colunas_filt = [mapear_intervalo_para_opcao(min_c[c], max_c[c], flexivel=is_flex) for c in range(10)]
    dc_filt = [mapear_intervalo_para_opcao(min_dc[d], max_dc[d], flexivel=is_flex) for d in range(10)]
    dd_filt = [mapear_intervalo_para_opcao(min_dd[d], max_dd[d], flexivel=is_flex) for d in range(10)]

    primos_res = sorted(list(conjunto_primos))
    moldura_res = sorted(list(conjunto_moldura))
    pares_res = sorted(list(conjunto_pares))

    if is_flex:
        ext_pr = set(primos_res)
        for p in primos_res:
            ext_pr.add(max(0, p - 1))
            ext_pr.add(min(6, p + 1))
        primos_res = sorted(list(ext_pr))

        ext_mo = set(moldura_res)
        for m in moldura_res:
            ext_mo.add(max(0, m - 1))
            ext_mo.add(min(6, m + 1))
        moldura_res = sorted(list(ext_mo))

    margem_soma = 20 if not is_flex else 35
    soma_min = max(50, min(somas_observadas) - margem_soma)
    soma_max = min(320, max(somas_observadas) + margem_soma)

    return {
        "linhas": linhas_filt,
        "colunas": colunas_filt,
        "diag_cresc": dc_filt,
        "diag_decresc": dd_filt,
        "primos": primos_res,
        "pares": pares_res,
        "moldura": moldura_res,
        "soma": (soma_min, soma_max),
        "audit": {
            "total_concursos": k_sorteios,
            "soma_min_real": min(somas_observadas),
            "soma_max_real": max(somas_observadas),
            "primos_reais": sorted(list(conjunto_primos)),
            "pares_reais": sorted(list(conjunto_pares)),
            "moldura_reais": sorted(list(conjunto_moldura))
        }
    }

# ==============================================================================
# MOTOR TÉRMICO DE ELLIOTT
# ==============================================================================
def calcular_metricas_elliott(historico):
    total = len(historico)
    atrasos = {n: total for n in range(1, 61)}
    freq_5 = {n: 0 for n in range(1, 61)}
    freq_15 = {n: 0 for n in range(1, 61)}

    for idx_rev, sorteio in enumerate(reversed(historico)):
        for n in sorteio:
            if atrasos[n] == total:
                atrasos[n] = idx_rev
            if idx_rev < 5:
                freq_5[n] += 1
            if idx_rev < 15:
                freq_15[n] += 1

    dados = {}
    for n in range(1, 61):
        atr = atrasos[n]
        dist_fib = min(abs(atr - f) for f in [1, 2, 3, 5, 8, 13, 21])
        score_retracao = max(0.0, 10.0 - (dist_fib * 2.2))
        score_impulso = (freq_5[n] * 6.5) + (freq_15[n] * 2.5)
        score_fib = 3.5 if PROPS[n]["is_fib"] else 0.0
        penalidade = -4.0 if atr > 21 else 0.0

        score_total = max(0.0, score_retracao + score_impulso + score_fib + penalidade)
        fase_nome = "Impulso (Onda 3)" if freq_5[n] >= 2 else ("Retração Ótima" if dist_fib <= 1 else "Acumulação")

        dados[n] = {
            "numero": n,
            "score": round(score_total, 1),
            "atraso": atr,
            "fase": fase_nome,
            "is_fib": PROPS[n]["is_fib"]
        }

    return dados

# ==============================================================================
# MOTOR COMBINATÓRIO
# ==============================================================================
def validar_aposta_final_6(jogo, cfg):
    soma_j = jogo[0] + jogo[1] + jogo[2] + jogo[3] + jogo[4] + jogo[5]
    if not (cfg["faixa_soma"][0] <= soma_j <= cfg["faixa_soma"][1]):
        return False

    pares_cnt = (
        PAR_LOOKUP[jogo[0]] + PAR_LOOKUP[jogo[1]] + PAR_LOOKUP[jogo[2]] +
        PAR_LOOKUP[jogo[3]] + PAR_LOOKUP[jogo[4]] + PAR_LOOKUP[jogo[5]]
    )
    if pares_cnt not in cfg["pares_aceitos"]:
        return False

    primos_cnt = (
        PRIMO_LOOKUP[jogo[0]] + PRIMO_LOOKUP[jogo[1]] + PRIMO_LOOKUP[jogo[2]] +
        PRIMO_LOOKUP[jogo[3]] + PRIMO_LOOKUP[jogo[4]] + PRIMO_LOOKUP[jogo[5]]
    )
    if primos_cnt not in cfg["primos_aceitos"]:
        return False

    moldura_cnt = (
        MOLDURA_LOOKUP[jogo[0]] + MOLDURA_LOOKUP[jogo[1]] + MOLDURA_LOOKUP[jogo[2]] +
        MOLDURA_LOOKUP[jogo[3]] + MOLDURA_LOOKUP[jogo[4]] + MOLDURA_LOOKUP[jogo[5]]
    )
    if moldura_cnt not in cfg["moldura_aceita"]:
        return False

    l_cnt = [0] * 6
    c_cnt = [0] * 10
    dc_cnt = [0] * 10
    dd_cnt = [0] * 10

    for n in jogo:
        r = ROW_LOOKUP[n]
        l_cnt[r] += 1
        if l_cnt[r] > cfg["linhas"][r][1]:
            return False

        c = COL_LOOKUP[n]
        c_cnt[c] += 1
        if c_cnt[c] > cfg["colunas"][c][1]:
            return False

        dc = DC_LOOKUP[n]
        dc_cnt[dc] += 1
        if dc_cnt[dc] > cfg["diag_cresc"][dc][1]:
            return False

        dd = DD_LOOKUP[n]
        dd_cnt[dd] += 1
        if dd_cnt[dd] > cfg["diag_decresc"][dd][1]:
            return False

    for r in range(6):
        if l_cnt[r] < cfg["linhas"][r][0]:
            return False

    for c in range(10):
        if c_cnt[c] < cfg["colunas"][c][0]:
            return False

    for d in range(10):
        if dc_cnt[d] < cfg["diag_cresc"][d][0] or dd_cnt[d] < cfg["diag_decresc"][d][0]:
            return False

    return True

def executar_varredura_pool(pool_dezenas, cfg, bar_progresso, container_status, ticker_metricas, teto_max=1000):
    t_inicio = time.time()
    dezenas_candidatas = sorted(list(pool_dezenas))
    k_escolhidas = len(dezenas_candidatas)

    if k_escolhidas < 6:
        container_status.error("Selecione pelo menos 6 dezenas no pool para gerar apostas.")
        return []

    total_combinacoes = math.comb(k_escolhidas, 6)
    container_status.write(
        f"🎯 **Varredura Ativa:** {k_escolhidas} dezenas selecionadas. "
        f"Espaço amostral: **{total_combinacoes:,} jogos de 6 números**."
    )

    jogos_aprovados = []
    testadas = 0
    lote_update = max(1000, min(100000, total_combinacoes // 25))

    for comb in combinations(dezenas_candidatas, 6):
        testadas += 1
        if validar_aposta_final_6(comb, cfg):
            jogos_aprovados.append(list(comb))
            if len(jogos_aprovados) >= teto_max:
                break

        if testadas % lote_update == 0:
            prog = min(1.0, testadas / total_combinacoes)
            bar_progresso.progress(prog)
            delta_t = max(0.001, time.time() - t_inicio)
            velocidade = int(testadas / delta_t)
            ticker_metricas.markdown(
                f"**Processando:** `{testadas:,}` de `{total_combinacoes:,}` ({prog*100:.1f}%) | "
                f"Aprovadas: `{len(jogos_aprovados):,}` | "
                f"Velocidade: `{velocidade:,} comb/s`"
            )

    bar_progresso.progress(1.0)
    delta_final = max(0.001, time.time() - t_inicio)
    ticker_metricas.markdown(
        f"**Concluído:** `{testadas:,}` combinações testadas | "
        f"Aprovados: `{len(jogos_aprovados):,}` apostas | "
        f"Tempo total: `{delta_final:.2f}s`"
    )
    return jogos_aprovados

# ==============================================================================
# COMPONENTES VISUAIS & CONFERÊNCIA
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

def render_cartao_sorteio_html(dezenas, titulo="CARTÃO OFICIAL DO SORTEIO"):
    bolas_html = "".join([
        f"<span style='display:inline-flex;align-items:center;justify-content:center;width:40px;height:40px;"
        f"background:linear-gradient(135deg,#eab308,#ca8a04);color:#ffffff;font-weight:900;font-size:15px;"
        f"border-radius:50%;margin:0 4px;box-shadow:0 3px 6px rgba(202,138,4,0.35);border:2px solid #a16207;"
        f"font-family:monospace;'>{n:02d}</span>"
        for n in dezenas
    ])
    st.markdown(
        f"""
        <div style="background:linear-gradient(135deg,#fefce8,#fef08a);border:2px solid #eab308;border-radius:12px;padding:12px;margin:8px 0;text-align:center;">
            <div style="font-weight:900;color:#854d0e;font-size:12px;margin-bottom:6px;text-transform:uppercase;">🏆 {titulo}</div>
            <div style="display:flex;justify-content:center;align-items:center;flex-wrap:wrap;gap:4px;">{bolas_html}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

def render_volante_conferencia(jogo, dezenas_sorteio, titulo=""):
    jogo_set = set(jogo)
    sorteio_set = set(dezenas_sorteio)
    celulas = ""
    for r in range(6):
        for c in range(10):
            n = r * 10 + c + 1
            if n in jogo_set and n in sorteio_set:
                celulas += f'<div style="width:34px;height:34px;background:#16a34a;color:#ffffff;font-weight:900;border:2px solid #0f5132;border-radius:6px;display:flex;flex-direction:column;align-items:center;justify-content:center;font-family:monospace;font-size:11px;">{n:02d}<span style="font-size:8px;line-height:6px;">★</span></div>'
            elif n in jogo_set:
                celulas += f'<div style="width:34px;height:34px;background:#0284c7;color:#ffffff;font-weight:800;border:1px solid #0369a1;border-radius:6px;display:flex;align-items:center;justify-content:center;font-family:monospace;font-size:11px;">{n:02d}</div>'
            elif n in sorteio_set:
                celulas += f'<div style="width:34px;height:34px;background:#fef08a;color:#854d0e;font-weight:800;border:2px dashed #ca8a04;border-radius:6px;display:flex;align-items:center;justify-content:center;font-family:monospace;font-size:11px;">{n:02d}</div>'
            else:
                bg = "#f1f5f9" if n in MOLDURA_SET else "#ffffff"
                celulas += f'<div style="width:34px;height:34px;background:{bg};color:#94a3b8;border:1px solid #e2e8f0;font-weight:600;border-radius:6px;display:flex;align-items:center;justify-content:center;font-family:monospace;font-size:11px;">{n:02d}</div>'

    html = f"""
    <!DOCTYPE html><html><head><meta charset="utf-8">
    <style>*{{box-sizing:border-box;}}body{{margin:0;padding:0;display:flex;justify-content:center;background:transparent;font-family:sans-serif;}}
    .box{{background:#fff;border:2px solid #cbd5e1;border-radius:10px;padding:10px;width:fit-content;}}
    .grid{{display:grid;grid-template-columns:repeat(10,34px);gap:4px;}}</style></head><body>
    <div class="box"><div style="font-weight:800;font-size:12px;margin-bottom:8px;color:#0f172a;text-align:center;">{titulo}</div>
    <div class="grid">{celulas}</div>
    <div style="margin-top:8px;display:flex;justify-content:center;gap:10px;font-size:10px;font-weight:700;">
        <span style="color:#16a34a;">★ Acerto</span>
        <span style="color:#0284c7;">■ Jogado</span>
        <span style="color:#ca8a04;">□ Sorteado</span>
    </div></div></body></html>
    """
    components.html(html, height=330, scrolling=False)

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

if "presets_filtros" not in st.session_state:
    st.session_state.presets_filtros = PRESETS_PADRAO.copy()

if "input_resultado_reverso_val" not in st.session_state:
    ult_res = st.session_state.historico[-1] if st.session_state.historico else [5, 9, 16, 40, 41, 59]
    st.session_state.input_resultado_reverso_val = " ".join([f"{n:02d}" for n in ult_res])

if "linha_trabalho_reverso" not in st.session_state:
    st.session_state.linha_trabalho_reverso = None

dados_calor = calcular_metricas_elliott(st.session_state.historico)
ranking_elliott = sorted(dados_calor.values(), key=lambda x: x["score"], reverse=True)
top_40_dezenas = {item["numero"] for item in ranking_elliott[:40]}
pool_inicial = top_40_dezenas | DEZENAS_BASE_3010

if "pool_trabalho" not in st.session_state or not isinstance(st.session_state.pool_trabalho, set):
    st.session_state.pool_trabalho = pool_inicial.copy()

def aplicar_preset(nome_preset):
    cfg_p = st.session_state.presets_filtros.get(nome_preset)
    if not cfg_p: return
    for r in range(6):
        st.session_state[f"sel_l_{r}"] = cfg_p["linhas"][r]
    for c in range(10):
        st.session_state[f"sel_c_{c}"] = cfg_p["colunas"][c]
    for d in range(10):
        st.session_state[f"sel_dc_{d}"] = cfg_p["diag_cresc"][d]
        st.session_state[f"sel_dd_{d}"] = cfg_p["diag_decresc"][d]
    st.session_state["sel_primos"] = cfg_p["primos"]
    st.session_state["sel_pares"] = cfg_p["pares"]
    st.session_state["sel_moldura"] = cfg_p["moldura"]
    st.session_state["sel_soma"] = tuple(cfg_p["soma"])

if "filtro_inicial_carregado" not in st.session_state:
    aplicar_preset("FILTRO3010")
    st.session_state.filtro_inicial_carregado = True

def toggle_dezena(n):
    if not isinstance(st.session_state.pool_trabalho, set):
        st.session_state.pool_trabalho = set(st.session_state.pool_trabalho)
    if n in st.session_state.pool_trabalho:
        st.session_state.pool_trabalho.remove(n)
    else:
        st.session_state.pool_trabalho.add(n)

def cb_puxar_ultimo():
    if st.session_state.historico:
        st.session_state.input_resultado_reverso_val = " ".join(
            [f"{n:02d}" for n in st.session_state.historico[-1]]
        )

max_sc = max(d["score"] for d in dados_calor.values())
min_sc = min(d["score"] for d in dados_calor.values())
delta_sc = max(0.1, max_sc - min_sc)

def obter_estilo_calor(score):
    norm = (score - min_sc) / delta_sc
    if norm >= 0.70:
        return {"cor_bg": "#fee2e2", "cor_texto": "#991b1b", "borda": "#ef4444", "icone": "🔥"}
    elif norm >= 0.45:
        return {"cor_bg": "#ffedd5", "cor_texto": "#9a3412", "borda": "#f97316", "icone": "☀️"}
    elif norm >= 0.25:
        return {"cor_bg": "#fef9c3", "cor_texto": "#854d0e", "borda": "#eab308", "icone": "🌤️"}
    return {"cor_bg": "#f1f5f9", "cor_texto": "#475569", "borda": "#94a3b8", "icone": "❄️"}

# ==============================================================================
# INTERFACE PRINCIPAL
# ==============================================================================
st.title("🍀 MEGA60: Cartela de Calor Elliott & Filtros Matriciais")
st.caption("Matriz 6x10 • Engenharia Reversa Multiconcursos • Monitor da Linha de Trabalho")

tab_cartela, tab_config, tab_volante, tab_upload, tab_historico = st.tabs([
    "🎟️ Cartela Térmica (Pool Ativo)",
    "🎛️ Filtros & Engenharia Reversa",
    "🗺️ Volante & Raio-X",
    "📥 Upload & Conferência",
    "📊 Histórico & API Caixa"
])

# ==============================================================================
# ABA 1: CARTELA TÉRMICA DE ELLIOTT
# ==============================================================================
with tab_cartela:
    st.subheader("🎟️ Cartela de Calor Interativa (Matriz 6x10)")
    st.markdown("Selecione os números que formarão a base do pool de combinações:")

    c_b1, c_b2, c_b3, c_b4, c_b5 = st.columns(5)
    with c_b1:
        if st.button("⭐ Base 3010 + Top 40", use_container_width=True):
            st.session_state.pool_trabalho = (top_40_dezenas | DEZENAS_BASE_3010).copy()
            st.rerun()
    with c_b2:
        if st.button("🔥 Apenas Quentes (Top 20)", use_container_width=True):
            st.session_state.pool_trabalho = {item["numero"] for item in ranking_elliott[:20]}
            st.rerun()
    with c_b3:
        if st.button("⚡ +9 Dezenas Fibonacci", use_container_width=True):
            st.session_state.pool_trabalho = set(st.session_state.pool_trabalho) | FIBONACCI_MEGASENA
            st.rerun()
    with c_b4:
        if st.button("✅ Marcar Todas (60)", use_container_width=True):
            st.session_state.pool_trabalho = set(range(1, 61))
            st.rerun()
    with c_b5:
        if st.button("🧹 Limpar Cartela", use_container_width=True):
            st.session_state.pool_trabalho = set()
            st.rerun()

    st.write("")

    for r in range(6):
        cols = st.columns(10)
        for c in range(10):
            n = r * 10 + c + 1
            meta = dados_calor[n]
            estilo = obter_estilo_calor(meta["score"])
            esta_ativa = n in st.session_state.pool_trabalho
            tipo_btn = "primary" if esta_ativa else "secondary"
            check_ico = "🟢" if esta_ativa else "⚪"
            rotulo = f"{check_ico} {n:02d}\n{estilo['icone']}{meta['score']:.0f}p"

            with cols[c]:
                if st.button(rotulo, key=f"btn_num_{n}", type=tipo_btn, use_container_width=True):
                    toggle_dezena(n)
                    st.rerun()

    st.divider()
    col_inf1, col_inf2 = st.columns([3, 1])
    qtd_sel = len(st.session_state.pool_trabalho)
    with col_inf1:
        st.markdown(
            "**Classificação Térmica:** &nbsp; "
            "<span style='color:#dc2626;font-weight:700;'>🔥 Ultra Quente (Onda 3)</span> &nbsp;|&nbsp; "
            "<span style='color:#ea580c;font-weight:700;'>☀️ Quente (Retração Fib)</span> &nbsp;|&nbsp; "
            "<span style='color:#ca8a04;font-weight:700;'>🌤️ Morno (Acumulação)</span> &nbsp;|&nbsp; "
            "<span style='color:#64748b;font-weight:700;'>❄️ Frio (Repouso)</span>",
            unsafe_allow_html=True
        )
        dezenas_txt = " - ".join([f"{n:02d}" for n in sorted(list(st.session_state.pool_trabalho))])
        st.success(f"✅ **Dezenas Ativas ({qtd_sel}):** `{dezenas_txt if dezenas_txt else 'Nenhuma'}`")
    with col_inf2:
        total_comb = math.comb(qtd_sel, 6) if qtd_sel >= 6 else 0
        st.metric("Dezenas Selecionadas", f"{qtd_sel} / 60")
        st.caption(f"Espaço Bruto: **{total_comb:,}** jogos")

# ==============================================================================
# ABA 2: CONFIGURAÇÃO DOS FILTROS & ENGENHARIA REVERSA
# ==============================================================================
with tab_config:
    st.markdown("### 🎛️ Filtros Estruturais & Engenharia Reversa")

    # SUB-ABA / SEÇÃO: DUAS ROTINAS REVERSAS (CONCURSOS HISTÓRICOS VS DEZENAS DIGITADAS)
    tipo_reverso = st.radio(
        "Selecione a Rotina de Engenharia Reversa Desejada:",
        [
            "🏛️ Rotina 1: Histórica Multiconcursos (Concursos Anteriores em Lote)",
            "⚡ Rotina 2: Amostra Personalizada (Digitar 6 a 60 Dezenas)"
        ],
        horizontal=True
    )

    # --------------------------------------------------------------------------
    # ROTINA 1: HISTÓRICA MULTICONCURSOS
    # --------------------------------------------------------------------------
    if tipo_reverso.startswith("🏛️ Rotina 1"):
        with st.container(border=True):
            st.markdown("#### 🏛️ Engenharia Reversa Multiconcursos: Otimização Histórica")
            st.caption(
                "Escolha a quantidade de concursos anteriores recentes para sintetizar o **Melhor Filtro Combinado**. "
                "O motor analisa linha por linha, coluna por coluna, diagonais, somas e paridades de todos esses resultados, "
                "criando a moldura matemática precisa que cobriu 100% desses concursos."
            )

            total_disp = len(st.session_state.historico)
            col_m1, col_m2, col_m3 = st.columns([1.5, 1.8, 1.7])
            with col_m1:
                qtd_concursos_sel = st.slider(
                    "Concursos Anteriores para Analisar:",
                    min_value=1,
                    max_value=max(1, total_disp),
                    value=min(10, total_disp),
                    help=f"Total disponível em memória: {total_disp} sorteios."
                )
            with col_m2:
                nome_filtro_multi = st.text_input(
                    "Nome da Predefinição:",
                    value=f"FILTRO_ULT_{qtd_concursos_sel}_CONCURSOS",
                    key="input_nome_multi"
                )
                carregar_pool_multi = st.checkbox(
                    "Carregar Dezenas Desses Sorteios no Pool",
                    value=True,
                    help="Adiciona na cartela todas as dezenas que foram sorteadas nesse período."
                )
            with col_m3:
                tolerancia_multi = st.selectbox(
                    "Margem Estrutural:",
                    ["Envelope Preciso (100% dos Sorteios)", "Envelope Flexível (Margem +1 / -1)"],
                    index=0,
                    key="sel_tolerancia_multi"
                )

            if st.button("🚀 Processar Concursos, Criar e Ativar Melhor Filtro", type="primary", use_container_width=True):
                with st.spinner("Varrendo e modelando concursos selecionados..."):
                    sorteios_alvo = st.session_state.historico[-qtd_concursos_sel:]
                    modo_extrair = "preciso" if tolerancia_multi.startswith("Envelope Preciso") else "flexivel"
                    preset_multi = extrair_filtros_multiconcursos(sorteios_alvo, modo=modo_extrair)
                    
                    nome_salvar = nome_filtro_multi.strip() or f"FILTRO_ULT_{qtd_concursos_sel}_CONCURSOS"
                    audit_dados = preset_multi.pop("audit")
                    
                    st.session_state.presets_filtros[nome_salvar] = preset_multi
                    aplicar_preset(nome_salvar)

                    dezenas_unicas_periodo = sorted(list({n for j in sorteios_alvo for n in j}))

                    if carregar_pool_multi:
                        st.session_state.pool_trabalho = set(dezenas_unicas_periodo)
                    else:
                        st.session_state.pool_trabalho = set(st.session_state.pool_trabalho) | set(dezenas_unicas_periodo)

                    hora_agora = time.strftime("%H:%M:%S - %d/%m/%Y")
                    st.session_state.linha_trabalho_reverso = {
                        "tipo": "MULTICONCURSOS",
                        "nome": nome_salvar,
                        "qtd_concursos": qtd_concursos_sel,
                        "total_dezenas_unicas": len(dezenas_unicas_periodo),
                        "dezenas": dezenas_unicas_periodo,
                        "timestamp": hora_agora,
                        "status": "CONCLUÍDO & ATIVO NO MOTOR",
                        "modo": tolerancia_multi,
                        "audit": audit_dados,
                        "pool_atualizado": carregar_pool_multi
                    }

                    st.success(f"🎉 Sucesso! O melhor filtro para os últimos {qtd_concursos_sel} concursos foi sintetizado e ativado!")
                    st.rerun()

    # --------------------------------------------------------------------------
    # ROTINA 2: AMOSTRA PERSONALIZADA (6 A 60 DEZENAS)
    # --------------------------------------------------------------------------
    else:
        with st.container(border=True):
            st.markdown("#### ⚡ Engenharia Reversa por Dezenas Digitadas (6 a 60 Números)")
            st.caption("Cole de 6 a 60 dezenas avulsas. O motor sintetiza a distribuição ideal e envia direto ao painel.")

            col_input_res, col_input_nome, col_input_tipo = st.columns([2.5, 1.8, 1.7])
            with col_input_res:
                entrada_dezenas_filtro = st.text_area(
                    "Dezenas de Referência (6 a 60 números):",
                    value=st.session_state.input_resultado_reverso_val,
                    height=75,
                    key="input_resultado_reverso"
                )
            with col_input_nome:
                nome_filtro_novo = st.text_input(
                    "Nome para Salvar o Filtro:",
                    value="MEU_NOVO_FILTRO",
                    key="input_nome_filtro_auto"
                )
                substituir_pool_opcao = st.checkbox(
                    "Definir estas dezenas como Pool Ativo",
                    value=True
                )
            with col_input_tipo:
                tipo_tolerancia = st.selectbox(
                    "Nível de Tolerância:",
                    ["Perfil Exato (Fiel à Amostra)", "Perfil Flexível (Margem Aberta)"],
                    index=0,
                    key="select_modo_reverso"
                )

            c_btn_rev1, c_btn_rev2 = st.columns([2, 1])
            with c_btn_rev1:
                if st.button("⚡ Gerar, Gravar e Ativar Filtro Deste Conjunto", type="primary", use_container_width=True):
                    nums_parse = [int(x) for x in re.findall(r"\b\d+\b", entrada_dezenas_filtro)]
                    dezenas_limpas = sorted(list(set([n for n in nums_parse if 1 <= n <= 60])))
                    total_identificado = len(dezenas_limpas)

                    if total_identificado < 6:
                        st.error(f"Informe pelo menos 6 dezenas válidas (entre 01 e 60). Foram identificadas {total_identificado}.")
                    elif total_identificado > 60:
                        st.error(f"O limite máximo é de 60 dezenas. Foram informadas {total_identificado}.")
                    elif not nome_filtro_novo.strip():
                        st.error("Informe um nome para o novo filtro.")
                    else:
                        modo_sel = "exato" if tipo_tolerancia.startswith("Perfil Exato") else "flexivel"
                        preset_extraido = extrair_filtros_de_jogo(dezenas_limpas, modo=modo_sel)
                        nome_salvar = nome_filtro_novo.strip()

                        st.session_state.presets_filtros[nome_salvar] = preset_extraido
                        aplicar_preset(nome_salvar)

                        if substituir_pool_opcao:
                            st.session_state.pool_trabalho = set(dezenas_limpas)
                        else:
                            st.session_state.pool_trabalho = set(st.session_state.pool_trabalho) | set(dezenas_limpas)

                        hora_agora = time.strftime("%H:%M:%S - %d/%m/%Y")
                        st.session_state.linha_trabalho_reverso = {
                            "tipo": "AMOSTRA_DEZENAS",
                            "nome": nome_salvar,
                            "qtd_dezenas": total_identificado,
                            "dezenas": dezenas_limpas,
                            "timestamp": hora_agora,
                            "status": "PROCESSADO & GRAVADO COM SUCESSO",
                            "modo": tipo_tolerancia,
                            "pool_atualizado": substituir_pool_opcao
                        }

                        st.success(f"🎉 Filtro '{nome_salvar}' gerado, gravado na memória e ativado com sucesso!")
                        st.rerun()

            with c_btn_rev2:
                st.button("🔄 Puxar Último Concurso", on_click=cb_puxar_ultimo, use_container_width=True)

    # --------------------------------------------------------------------------
    # LINHA DE TRABALHO & SINAL DE OPERAÇÃO (EXIBE STATUS DE AMBAS AS ROTINAS)
    # --------------------------------------------------------------------------
    st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
    if st.session_state.linha_trabalho_reverso:
        lt = st.session_state.linha_trabalho_reverso
        is_multi = lt.get("tipo") == "MULTICONCURSOS"
        dezenas_formatadas = " - ".join([f"{n:02d}" for n in lt["dezenas"]])
        pool_info = "Cartela sincronizada com este pool" if lt["pool_atualizado"] else "Cartela prévia preservada"

        if is_multi:
            detalhes_audit = (
                f"• <strong>Base de Auditoria:</strong> <strong>{lt['qtd_concursos']} concursos recentes</strong> analisados.<br>"
                f"• <strong>Dezenas Abrangidas no Histórico ({lt['total_dezenas_unicas']}):</strong> <span style='font-family:monospace;color:#166534;font-weight:700;'>{dezenas_formatadas}</span><br>"
                f"• <strong>Faixa de Soma Observada:</strong> <code>{lt['audit']['soma_min_real']}</code> até <code>{lt['audit']['soma_max_real']}</code> | "
                f"<strong>Primos Reais:</strong> <code>{lt['audit']['primos_reais']}</code> | "
                f"<strong>Moldura Real:</strong> <code>{lt['audit']['moldura_reais']}</code>"
            )
        else:
            detalhes_audit = (
                f"• <strong>Volume Analisado:</strong> <strong>{lt['qtd_dezenas']} dezenas</strong> computadas em linhas, colunas e diagonais.<br>"
                f"• <strong>Dezenas Auditadas:</strong> <span style='font-family:monospace;color:#166534;font-weight:700;'>{dezenas_formatadas}</span>"
            )

        st.markdown(
            f"""
            <div style="background:#f0fdf4;border:1px solid #86efac;border-left:6px solid #16a34a;border-radius:8px;padding:12px 16px;box-shadow:0 1px 3px rgba(0,0,0,0.05);margin-bottom:15px;">
                <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
                    <span style="font-weight:900;color:#15803d;font-size:13px;letter-spacing:0.5px;">
                        🟢 LINHA DE TRABALHO: {lt['status']} ({lt.get('tipo', 'OPERACIONAL')})
                    </span>
                    <span style="font-size:11px;color:#166534;font-family:monospace;background:#dcfce7;border:1px solid #bbf7d0;padding:2px 8px;border-radius:4px;font-weight:700;">
                        🕒 {lt['timestamp']}
                    </span>
                </div>
                <div style="margin-top:8px;font-size:12px;color:#14532d;line-height:1.6;">
                    • <strong>Filtro Ativo:</strong> <code style="color:#0f5132;background:#dcfce7;padding:1px 6px;border-radius:3px;font-weight:bold;">{lt['nome']}</code> ({lt['modo']})<br>
                    {detalhes_audit}<br>
                    • <strong>Sincronização:</strong> Gravado no catálogo de predefinições e aplicado aos seletores abaixo ({pool_info}).
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            """
            <div style="background:#f8fafc;border:1px dashed #cbd5e1;border-left:6px solid #94a3b8;border-radius:8px;padding:10px 14px;color:#64748b;font-size:12px;margin-bottom:15px;">
                ⚪ <strong>LINHA DE TRABALHO (AGUARDANDO):</strong> Nenhuma rotina executada. Escolha uma das opções acima e clique em processar para gerar e visualizar os dados em tempo real.
            </div>
            """,
            unsafe_allow_html=True
        )

    # --------------------------------------------------------------------------
    # GERENCIADOR DE PREDEFINIÇÕES (CARREGAR / SALVAR / BAIXAR)
    # --------------------------------------------------------------------------
    with st.container(border=True):
        st.markdown("#### 💾 Gerenciador de Predefinições Salvas")
        col_puxar, col_gravar = st.columns(2)

        with col_puxar:
            st.markdown("**📥 Carregar Filtro Salvo:**")
            lista_nomes = list(st.session_state.presets_filtros.keys())
            filtro_escolhido = st.selectbox("Selecione o filtro:", lista_nomes, index=0, key="select_preset_load")

            c_pux1, c_pux2 = st.columns(2)
            with c_pux1:
                if st.button("🚀 Aplicar Predefinição", use_container_width=True):
                    aplicar_preset(filtro_escolhido)
                    st.success(f"Filtro '{filtro_escolhido}' carregado!")
                    st.rerun()
            with c_pux2:
                json_presets = json.dumps(st.session_state.presets_filtros, indent=2, ensure_ascii=False)
                st.download_button(
                    "💾 Baixar Filtros (.JSON)",
                    data=json_presets,
                    file_name="meus_filtros_mega60.json",
                    mime="application/json",
                    use_container_width=True
                )

        with col_gravar:
            st.markdown("**💾 Gravar Configuração Manual Atual:**")
            nome_novo_filtro = st.text_input("Nome da predefinição manual:", placeholder="Ex: Filtro Personalizado", key="input_nome_filtro_manual")

            c_grv1, c_grv2 = st.columns(2)
            with c_grv1:
                if st.button("💾 Gravar Manual", use_container_width=True):
                    if not nome_novo_filtro.strip():
                        st.error("Informe um nome para a predefinição.")
                    else:
                        novo_preset = {
                            "linhas": [st.session_state.get(f"sel_l_{r}", "0 a 2") for r in range(6)],
                            "colunas": [st.session_state.get(f"sel_c_{c}", "0 a 2") for c in range(10)],
                            "diag_cresc": [st.session_state.get(f"sel_dc_{d}", "0 a 2") for d in range(10)],
                            "diag_decresc": [st.session_state.get(f"sel_dd_{d}", "0 a 2") for d in range(10)],
                            "primos": st.session_state.get("sel_primos", [3]),
                            "pares": st.session_state.get("sel_pares", ["2P / 4I"]),
                            "moldura": st.session_state.get("sel_moldura", [5]),
                            "soma": st.session_state.get("sel_soma", (150, 190))
                        }
                        st.session_state.presets_filtros[nome_novo_filtro.strip()] = novo_preset
                        st.success(f"Predefinição '{nome_novo_filtro.strip()}' gravada!")
                        st.rerun()
            with c_grv2:
                arq_json_upload = st.file_uploader("Importar Filtros (.JSON):", type=["json"], label_visibility="collapsed")
                if arq_json_upload is not None:
                    try:
                        st.session_state.presets_filtros.update(json.load(arq_json_upload))
                        st.success("Filtros importados com sucesso!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao ler JSON: {e}")

    st.divider()
    opcoes_nomes = list(OPCOES_QUANTIDADE.keys())

    with st.container(border=True):
        st.markdown("#### 1️⃣ Linhas Individuais (L01 a L06)")
        cols_l = st.columns(6)
        limites_linhas = []
        for r in range(6):
            with cols_l[r]:
                val_padrao = st.session_state.get(f"sel_l_{r}", "0 a 2")
                idx_sel = opcoes_nomes.index(val_padrao) if val_padrao in opcoes_nomes else 0
                esc = st.selectbox(f"Linha {r+1:02d}", opcoes_nomes, index=idx_sel, key=f"sel_l_{r}")
                limites_linhas.append(OPCOES_QUANTIDADE[esc])

    with st.container(border=True):
        st.markdown("#### 2️⃣ Colunas Individuais (C01 a C10)")
        cols_c_up, cols_c_dw = st.columns(5), st.columns(5)
        limites_colunas = []
        for c in range(10):
            alvo = cols_c_up[c] if c < 5 else cols_c_dw[c - 5]
            with alvo:
                val_padrao = st.session_state.get(f"sel_c_{c}", "0 a 2")
                idx_sel = opcoes_nomes.index(val_padrao) if val_padrao in opcoes_nomes else 0
                esc = st.selectbox(f"Coluna {c+1:02d}", opcoes_nomes, index=idx_sel, key=f"sel_c_{c}")
                limites_colunas.append(OPCOES_QUANTIDADE[esc])

    c_diag1, c_diag2 = st.columns(2)
    with c_diag1:
        with st.container(border=True):
            st.markdown("#### 3️⃣ Diag. Crescentes (DC01 a DC10 /)")
            with st.expander("Expandir Diagonais Crescentes", expanded=False):
                limites_dc = []
                for d in range(10):
                    val_padrao = st.session_state.get(f"sel_dc_{d}", "0 a 2")
                    idx_sel = opcoes_nomes.index(val_padrao) if val_padrao in opcoes_nomes else 0
                    esc = st.selectbox(f"DC{d+1:02d}", opcoes_nomes, index=idx_sel, key=f"sel_dc_{d}")
                    limites_dc.append(OPCOES_QUANTIDADE[esc])
    with c_diag2:
        with st.container(border=True):
            st.markdown("#### 4️⃣ Diag. Decrescentes (DD01 a DD10 \\)")
            with st.expander("Expandir Diagonais Decrescentes", expanded=False):
                limites_dd = []
                for d in range(10):
                    val_padrao = st.session_state.get(f"sel_dd_{d}", "0 a 2")
                    idx_sel = opcoes_nomes.index(val_padrao) if val_padrao in opcoes_nomes else 0
                    esc = st.selectbox(f"DD{d+1:02d}", opcoes_nomes, index=idx_sel, key=f"sel_dd_{d}")
                    limites_dd.append(OPCOES_QUANTIDADE[esc])

    with st.container(border=True):
        st.markdown("#### 5️⃣ Primos, Pares, Moldura e Faixa de Soma")
        c_p1, c_p2, c_p3, c_p4 = st.columns(4)
        with c_p1:
            primos_sel = st.multiselect("Quantidade de Primos:", list(range(7)), default=st.session_state.get("sel_primos", [3]), key="sel_primos")
        with c_p2:
            opcoes_par = {"3P / 3I": 3, "2P / 4I": 2, "4P / 2I": 4, "1P / 5I": 1, "5P / 1I": 5, "0P / 6I": 0, "6P / 0I": 6}
            par_sel = st.multiselect("Pares / Ímpares:", list(opcoes_par.keys()), default=st.session_state.get("sel_pares", ["2P / 4I"]), key="sel_pares")
            pares_valores = {opcoes_par[k] for k in par_sel}
        with c_p3:
            moldura_sel = st.multiselect("Dezenas na Moldura:", list(range(7)), default=st.session_state.get("sel_moldura", [5]), key="sel_moldura")
        with c_p4:
            faixa_soma = st.slider("Faixa de Soma:", 50, 320, st.session_state.get("sel_soma", (150, 190)), key="sel_soma")

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
    c_exec1, c_exec2 = st.columns([3, 1])
    with c_exec2:
        teto_apostas = st.number_input("Teto Máximo de Jogos:", min_value=1, max_value=50000, value=500, step=50)

    with c_exec1:
        placeholder_metricas = st.empty()
        barra_progresso = st.progress(0, text="Aguardando comando...")

    pode_processar = len(st.session_state.pool_trabalho) >= 6

    if st.button("🚀 Gerar e Filtrar Apostas com a Configuração Ativa", use_container_width=True, disabled=not pode_processar, type="primary"):
        if not primos_sel or not par_sel or not moldura_sel:
            st.error("Selecione os parâmetros de Primos, Pares e Moldura.")
        else:
            with st.status("🛠️ Processando Motor Combinatório...", expanded=True) as status_box:
                t0 = time.time()
                resultados = executar_varredura_pool(
                    st.session_state.pool_trabalho,
                    config_total,
                    barra_progresso,
                    status_box,
                    placeholder_metricas,
                    teto_max=teto_apostas
                )
                t_fim = time.time() - t0
                st.session_state.jogos_aprovados = resultados
                total_gerado = len(resultados)

                if total_gerado > 0:
                    status_box.update(
                        label=f"✅ Sucesso! {total_gerado:,} aposta(s) aprovada(s) em {t_fim:.2f}s.",
                        state="complete",
                        expanded=False
                    )
                else:
                    status_box.update(
                        label=f"⚠️ Concluído em {t_fim:.2f}s: Nenhuma combinação atendeu aos filtros selecionados.",
                        state="error",
                        expanded=True
                    )

    if st.session_state.jogos_aprovados:
        qtd_aprov = len(st.session_state.jogos_aprovados)
        st.success(f"🎯 **Total Aprovado:** {qtd_aprov:,} apostas oficiais prontas.")
        txt_saida = "\n".join([" ".join([f"{n:02d}" for n in j]) for j in st.session_state.jogos_aprovados])

        c_d1, c_d2 = st.columns([3, 1])
        with c_d1:
            st.download_button(
                "📥 Baixar Arquivo com Jogos Aprovados (.TXT)",
                data=txt_saida,
                file_name=f"mega60_apostas_filtradas_{qtd_aprov}.txt",
                mime="text/plain",
                use_container_width=True
            )
        with c_d2:
            st.metric("Apostas Prontas", f"{qtd_aprov:,}")

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
                        celulas += f'<div style="width:34px;height:34px;background:linear-gradient(135deg,#16a34a,#15803d);color:#fff;border:2px solid #0f5132;font-weight:800;border-radius:6px;display:flex;align-items:center;justify-content:center;font-family:monospace;font-size:12px;">{n:02d}</div>'
                    else:
                        bg = "#f1f5f9" if n in MOLDURA_SET else "#ffffff"
                        celulas += f'<div style="width:34px;height:34px;background:{bg};color:#64748b;border:1px solid #cbd5e1;font-weight:600;border-radius:6px;display:flex;align-items:center;justify-content:center;font-family:monospace;font-size:12px;">{n:02d}</div>'

            html_cartela = f"""
            <!DOCTYPE html><html><head><meta charset="utf-8">
            <style>*{{box-sizing:border-box;}}body{{margin:0;padding:0;display:flex;justify-content:center;background:transparent;font-family:sans-serif;}}
            .box{{background:#fff;border:2px solid #16a34a;border-radius:10px;padding:10px;width:fit-content;}}
            .grid{{display:grid;grid-template-columns:repeat(10,34px);gap:4px;}}</style></head><body>
            <div class="box"><div style="font-weight:800;font-size:13px;margin-bottom:8px;color:#15803d;text-align:center;">Jogo #{sel_idx:04d}: {' - '.join([f'{n:02d}' for n in jogo_ativo])}</div>
            <div class="grid">{celulas}</div></div></body></html>
            """
            components.html(html_cartela, height=310, scrolling=False)

        with c_v2:
            with st.container(border=True):
                st.markdown("#### 🔬 Raio-X Detalhado do Jogo")
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
        st.info("Gere apostas na aba de Filtros para visualizá-las no volante oficial.")

# ==============================================================================
# ABA 4: UPLOAD & CONFERÊNCIA
# ==============================================================================
with tab_upload:
    st.subheader("📥 Upload, Auditoria & Conferência de Resultados")
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
        st.success(f"✅ **Arquivo Ativo:** **{total_up:,} apostas oficiais** carregadas.")

        col_diag_left, col_conf_right = st.columns([1, 1], gap="large")

        with col_diag_left:
            st.markdown("### 📊 Diagnóstico das Apostas")
            cnt_nums = Counter()
            somas = []
            for j in jogos_up:
                cnt_nums.update(j)
                somas.append(sum(j))

            m1, m2, m3 = st.columns(3)
            m1.metric("Total de Jogos", f"{total_up:,}")
            m2.metric("Soma Média", f"{sum(somas)/len(somas):.1f}")
            m3.metric("Mais Frequente", f"{cnt_nums.most_common(1)[0][0]:02d}")

            st.markdown("#### 🔥 Frequência na Matriz 6x10")
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
                    celulas_up_heat += f'<div style="width:34px;height:34px;background:{bg};color:{color};border-radius:6px;display:flex;flex-direction:column;align-items:center;justify-content:center;font-family:monospace;border:1px solid rgba(0,0,0,0.08);box-sizing:border-box;"><span style="font-size:11px;font-weight:900;">{n:02d}</span><span style="font-size:8px;font-weight:700;">{freq}x</span></div>'

            html_up = f'<!DOCTYPE html><html><head><meta charset="utf-8"><style>*{{box-sizing:border-box;}}body{{margin:0;padding:0;background:transparent;display:flex;justify-content:center;font-family:sans-serif;}}.box{{background:#fff;border:2px solid #cbd5e1;border-radius:10px;padding:8px;width:fit-content;}}.grid{{display:grid;grid-template-columns:repeat(10,34px);gap:3px;}}</style></head><body><div class="box"><div class="grid">{celulas_up_heat}</div></div></body></html>'
            components.html(html_up, height=270, scrolling=False)

        with col_conf_right:
            st.markdown("### 🎯 Conferência de Resultados")
            ult_sorteio = st.session_state.historico[-1] if st.session_state.historico else [4, 12, 18, 30, 35, 54]
            txt_padrao = " ".join([f"{n:02d}" for n in ult_sorteio])

            modo_origem = st.radio("Origem do Sorteio:", ["Último Sorteio Oficial", "Digitar Manualmente"], horizontal=True)
            if modo_origem == "Último Sorteio Oficial":
                dezenas_conf = sorted(ult_sorteio)
            else:
                entrada_manual = st.text_input("6 Dezenas Sorteadas (separadas por espaço):", value=txt_padrao)
                nums_man = [int(x) for x in re.findall(r"\b\d+\b", entrada_manual)]
                dezenas_conf = sorted(list(set([n for n in nums_man if 1 <= n <= 60])))

            if len(dezenas_conf) != 6:
                st.error("Informe exatamente 6 dezenas distintas entre 01 e 60 para conferir.")
            else:
                render_cartao_sorteio_html(dezenas_conf, titulo="CARTÃO DO SORTEIO CONFERIDO")
                relatorio_conf, placar_conf = conferir_apostas_contra_sorteio(jogos_up, dezenas_conf)

                c_s, c_q, c_qd, c_t = st.columns(4)
                c_s.metric("Sena (6)", f"{len(placar_conf[6])}")
                c_q.metric("Quina (5)", f"{len(placar_conf[5])}")
                c_qd.metric("Quadra (4)", f"{len(placar_conf[4])}")
                c_t.metric("Terno (3)", f"{len(placar_conf[3])}")

                tot_prem = len(placar_conf[6]) + len(placar_conf[5]) + len(placar_conf[4])
                if tot_prem > 0:
                    st.success(f"🎉 **{tot_prem} aposta(s) premiada(s)** encontradas no arquivo!")
                    jogos_premiados_txt = "\n".join([
                        f"{' '.join([f'{n:02d}' for n in it['jogo']])} | {it['qtd_acertos']} ACERTOS"
                        for it in relatorio_conf if it["qtd_acertos"] >= 4
                    ])
                    st.download_button(
                        "📥 Baixar Apostas Premiadas (.TXT)",
                        data=jogos_premiados_txt,
                        file_name=f"mega60_apostas_premiadas_{tot_prem}.txt",
                        mime="text/plain",
                        use_container_width=True
                    )
                else:
                    st.warning("Nenhuma aposta alcançou 4, 5 ou 6 acertos neste sorteio.")

                jogos_com_acerto = [it for it in relatorio_conf if it["qtd_acertos"] >= 4] or relatorio_conf
                opcoes_map = {
                    it["num_aposta"]: f"Aposta #{it['num_aposta']:04d} — {it['qtd_acertos']} acertos"
                    for it in jogos_com_acerto[:50]
                }
                idx_escolhido = st.selectbox(
                    "Inspecionar Aposta no Volante:",
                    list(opcoes_map.keys()),
                    format_func=lambda x: opcoes_map[x]
                )
                if idx_escolhido is not None:
                    item_ativo = next(it for it in relatorio_conf if it["num_aposta"] == idx_escolhido)
                    render_volante_conferencia(
                        item_ativo["jogo"],
                        dezenas_conf,
                        titulo=f"Volante: Aposta #{item_ativo['num_aposta']:04d} ({item_ativo['qtd_acertos']} Acertos)"
                    )
    else:
        st.info("Envie um arquivo de apostas no topo da página para conferir seus acertos.")

# ==============================================================================
# ABA 5: HISTÓRICO & API CAIXA
# ==============================================================================
with tab_historico:
    st.subheader("Base de Sorteios Oficiais")
    st.write(f"Concursos ativos em memória: **{len(st.session_state.historico)}** ({st.session_state.origem})")

    if st.button("🌐 Sincronizar Histórico com a Caixa Agora", type="primary"):
        with st.spinner("Conectando aos servidores da Caixa..."):
            try:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "application/json, text/plain, */*",
                    "Referer": "https://loterias.caixa.gov.br/"
                }
                r = requests.get(
                    "https://servicebus2.caixa.gov.br/portaldeloterias/api/megasena",
                    headers=headers,
                    timeout=10,
                    verify=False
                )
                if r.status_code == 200:
                    ult = r.json()
                    dezenas_sorteadas = sorted([int(x) for x in ult.get("listaDezenas", [])])

                    if len(dezenas_sorteadas) == 6:
                        if dezenas_sorteadas not in st.session_state.historico:
                            st.session_state.historico.append(dezenas_sorteadas)
                        st.session_state.origem = f"API Caixa (Concurso #{ult.get('numero', '?')})"
                        st.session_state.input_resultado_reverso_val = " ".join([f"{n:02d}" for n in dezenas_sorteadas])
                        st.success(f"Concurso #{ult.get('numero')} sincronizado: {' - '.join([f'{n:02d}' for n in dezenas_sorteadas])}")
                        st.rerun()
                    else:
                        st.warning("Formato inesperado no retorno da API da Caixa.")
                else:
                    st.warning(f"Servidor da Caixa retornou código HTTP {r.status_code}.")
            except Exception as e:
                st.error(f"Erro ao conectar com a API: {e}")

    with st.expander("Ver Concursos Armazenados na Sessão"):
        for i, sorteio in enumerate(reversed(st.session_state.historico), start=1):
            st.write(f"**Concurso recente #{i:02d}:** `{' - '.join([f'{n:02d}' for n in sorteio])}`")
