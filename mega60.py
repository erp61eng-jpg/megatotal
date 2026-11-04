import streamlit as st
import streamlit.components.v1 as components
import requests
from itertools import combinations
from collections import Counter
import math
import time
import re
import json
import io
import traceback
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==============================================================================
# CONFIGURAÇÃO DE PÁGINA (PRIMEIRO COMANDO STREAMLIT OBRIGATÓRIO)
# ==============================================================================
st.set_page_config(
    page_title="MEGA60 - Alto Contraste & Blindado",
    page_icon="🍀",
    layout="wide"
)

# ==============================================================================
# ENCAPSULAMENTO GLOBAL DE SEGURANÇA
# ==============================================================================
try:
    # ESTILIZAÇÃO CSS: FONTE MAIOR, TUDO PRETO E ALTO CONTRASTE (ZERO VERDE)
    st.markdown("""
    <style>
        html, body, [class*="css"], .stMarkdown, p, span, label, div, input, textarea, select {
            color: #000000 !important;
            font-weight: 800 !important;
            font-family: Arial, Helvetica, sans-serif !important;
        }
        
        h1 {
            font-size: 2.3rem !important;
            color: #000000 !important;
            font-weight: 900 !important;
        }
        h2 {
            font-size: 1.9rem !important;
            color: #000000 !important;
            font-weight: 900 !important;
        }
        h3 {
            font-size: 1.5rem !important;
            color: #000000 !important;
            font-weight: 900 !important;
        }
        h4 {
            font-size: 1.25rem !important;
            color: #000000 !important;
            font-weight: 900 !important;
        }

        .stCaption, [data-testid="stCaptionContainer"] {
            color: #000000 !important;
            font-size: 1.1rem !important;
            font-weight: 900 !important;
        }

        .stButton > button {
            color: #000000 !important;
            font-size: 1.2rem !important;
            font-weight: 900 !important;
            border: 3px solid #000000 !important;
            background-color: #ffffff !important;
            border-radius: 8px !important;
            padding: 6px 4px !important;
        }
        
        .stButton > button[kind="primary"] {
            background-color: #facc15 !important;
            color: #000000 !important;
            border: 3px solid #000000 !important;
        }

        button[data-baseweb="tab"] {
            font-size: 1.2rem !important;
            font-weight: 900 !important;
            color: #000000 !important;
        }

        .stSelectbox label, .stMultiSelect label, .stSlider label, .stTextInput label, .stTextArea label {
            font-size: 1.15rem !important;
            color: #000000 !important;
            font-weight: 900 !important;
        }

        [data-testid="stMetricValue"] {
            font-size: 2.0rem !important;
            color: #000000 !important;
            font-weight: 900 !important;
        }
        [data-testid="stMetricLabel"] {
            font-size: 1.15rem !important;
            color: #000000 !important;
            font-weight: 900 !important;
        }

        .stAlert {
            background-color: #fef08a !important;
            border: 3px solid #000000 !important;
        }
        .stAlert p {
            font-size: 1.15rem !important;
            color: #000000 !important;
            font-weight: 900 !important;
        }
        
        code {
            color: #000000 !important;
            background-color: #fef08a !important;
            font-weight: 900 !important;
            font-size: 1.15rem !important;
            border: 2px solid #000000 !important;
            padding: 2px 6px !important;
        }
    </style>
    """, unsafe_allow_html=True)

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
    # MOTOR TÉRMICO DE ELLIOTT & SELEÇÃO DE ELITE
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
            dados[n] = {
                "numero": n,
                "score": round(score_total, 1),
                "atraso": atr,
                "is_fib": PROPS[n]["is_fib"],
                "is_primo": PROPS[n]["is_primo"],
                "is_par": PROPS[n]["is_par"],
                "dc": PROPS[n]["dc"],
                "dd": PROPS[n]["dd"]
            }

        return dados

    def extrair_analise_elite(dados_calor):
        ranking = sorted(dados_calor.values(), key=lambda x: x["score"], reverse=True)
        
        melhores_primos = [x["numero"] for x in ranking if x["is_primo"]][:5]
        melhores_pares = [x["numero"] for x in ranking if x["is_par"]][:3]
        melhores_impares = [x["numero"] for x in ranking if not x["is_par"]][:5]
        
        dc_scores = {d: 0.0 for d in range(10)}
        dd_scores = {d: 0.0 for d in range(10)}
        for n, val in dados_calor.items():
            dc_scores[val["dc"]] += val["score"]
            dd_scores[val["dd"]] += val["score"]
            
        melhores_dc = sorted(dc_scores.keys(), key=lambda d: dc_scores[d], reverse=True)[:3]
        melhores_dd = sorted(dd_scores.keys(), key=lambda d: dd_scores[d], reverse=True)[:3]
        
        pool_elite = sorted(list(set(melhores_primos) | set(melhores_pares) | set(melhores_impares)))
        
        return {
            "primos": melhores_primos,
            "pares": melhores_pares,
            "impares": melhores_impares,
            "dc": melhores_dc,
            "dd": melhores_dd,
            "pool_elite": pool_elite
        }

    # ==============================================================================
    # ENGENHARIA REVERSA & FILTROS
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
    # MOTOR COMBINATÓRIO BLINDADO
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

    def executar_varredura_pool(pool_dezenas, cfg, bar_progresso, ticker_metricas, teto_max=None):
        t_inicio = time.time()
        dezenas_candidatas = sorted(list(pool_dezenas))
        k_escolhidas = len(dezenas_candidatas)

        if k_escolhidas < 6:
            return []

        total_combinacoes = math.comb(k_escolhidas, 6)
        jogos_aprovados = []
        testadas = 0
        t_ultimo_update = 0.0

        for comb in combinations(dezenas_candidatas, 6):
            testadas += 1

            if validar_aposta_final_6(comb, cfg):
                jogos_aprovados.append(list(comb))
                if teto_max is not None and len(jogos_aprovados) >= teto_max:
                    break

            t_agora = time.time()
            if t_agora - t_ultimo_update >= 0.25:
                t_ultimo_update = t_agora
                prog = min(1.0, testadas / total_combinacoes)
                bar_progresso.progress(prog)
                velocidade = int(testadas / max(0.001, t_agora - t_inicio))
                ticker_metricas.markdown(
                    f"**Processando:** `{testadas:,}` de `{total_combinacoes:,}` ({prog*100:.1f}%) | "
                    f"Aprovadas: `{len(jogos_aprovados):,}` | "
                    f"Velocidade: `{velocidade:,} comb/s`"
                )

        bar_progresso.progress(1.0)
        delta_final = max(0.001, time.time() - t_inicio)
        ticker_metricas.markdown(
            f"**Concluído:** `{testadas:,}` combinações testadas | "
            f"Aprovadas: `{len(jogos_aprovados):,}` apostas | "
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
            f"<span style='display:inline-flex;align-items:center;justify-content:center;width:48px;height:48px;"
            f"background:#facc15;color:#000000;font-weight:900;font-size:22px;"
            f"border-radius:50%;margin:0 6px;border:3px solid #000000;"
            f"font-family:monospace;'>{n:02d}</span>"
            for n in dezenas
        ])
        st.markdown(
            f"""
            <div style="background:#ffffff;border:4px solid #000000;border-radius:12px;padding:16px;margin:12px 0;text-align:center;">
                <div style="font-weight:900;color:#000000;font-size:18px;margin-bottom:10px;text-transform:uppercase;">🏆 {titulo}</div>
                <div style="display:flex;justify-content:center;align-items:center;flex-wrap:wrap;gap:8px;">{bolas_html}</div>
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
                    celulas += f'<div style="width:42px;height:42px;background:#facc15;color:#000000;font-weight:900;border:3px solid #000000;border-radius:6px;display:flex;flex-direction:column;align-items:center;justify-content:center;font-family:monospace;font-size:15px;">{n:02d}<span style="font-size:11px;line-height:8px;font-weight:900;">★</span></div>'
                elif n in jogo_set:
                    celulas += f'<div style="width:42px;height:42px;background:#38bdf8;color:#000000;font-weight:900;border:3px solid #000000;border-radius:6px;display:flex;align-items:center;justify-content:center;font-family:monospace;font-size:15px;">{n:02d}</div>'
                elif n in sorteio_set:
                    celulas += f'<div style="width:42px;height:42px;background:#ffffff;color:#000000;font-weight:900;border:3px dashed #000000;border-radius:6px;display:flex;align-items:center;justify-content:center;font-family:monospace;font-size:15px;">{n:02d}</div>'
                else:
                    celulas += f'<div style="width:42px;height:42px;background:#ffffff;color:#000000;border:1px solid #000000;font-weight:900;border-radius:6px;display:flex;align-items:center;justify-content:center;font-family:monospace;font-size:15px;">{n:02d}</div>'

        html = f"""
        <!DOCTYPE html><html><head><meta charset="utf-8">
        <style>*{{box-sizing:border-box;}}body{{margin:0;padding:0;display:flex;justify-content:center;background:transparent;font-family:Arial,sans-serif;}}
        .box{{background:#fff;border:4px solid #000000;border-radius:10px;padding:12px;width:fit-content;}}
        .grid{{display:grid;grid-template-columns:repeat(10,42px);gap:5px;}}</style></head><body>
        <div class="box"><div style="font-weight:900;font-size:16px;margin-bottom:12px;color:#000000;text-align:center;">{titulo}</div>
        <div class="grid">{celulas}</div>
        <div style="margin-top:12px;display:flex;justify-content:center;gap:14px;font-size:13px;font-weight:900;color:#000000;">
            <span style="background:#facc15;padding:3px 10px;border:2px solid #000000;border-radius:4px;">★ Acerto</span>
            <span style="background:#38bdf8;padding:3px 10px;border:2px solid #000000;border-radius:4px;">■ Jogado</span>
            <span style="background:#ffffff;padding:3px 10px;border:2px dashed #000000;border-radius:4px;">□ Sorteado</span>
        </div></div></body></html>
        """
        components.html(html, height=390, scrolling=False)

    # ==============================================================================
    # INICIALIZAÇÃO DE ESTADO
    # ==============================================================================
    if "historico" not in st.session_state:
        st.session_state.historico = [sorted(list(j)) for j in FALLBACK_MEGASENA]
        st.session_state.origem = "Base Local Offline"

    if "jogos_aprovados" not in st.session_state:
        st.session_state.jogos_aprovados = []

    if "jogos_upload" not in st.session_state:
        st.session_state.jogos_upload = []

    if "jogos_filtrados_upload" not in st.session_state:
        st.session_state.jogos_filtrados_upload = []

    if "presets_filtros" not in st.session_state:
        st.session_state.presets_filtros = PRESETS_PADRAO.copy()

    if "input_resultado_reverso_val" not in st.session_state:
        ult_res = st.session_state.historico[-1] if st.session_state.historico else [5, 9, 16, 40, 41, 59]
        st.session_state.input_resultado_reverso_val = " ".join([f"{n:02d}" for n in sorted(ult_res)])

    if "linha_trabalho_reverso" not in st.session_state:
        st.session_state.linha_trabalho_reverso = None

    dados_calor = calcular_metricas_elliott(st.session_state.historico)
    ranking_elliott = sorted(dados_calor.values(), key=lambda x: x["score"], reverse=True)
    top_40_dezenas = {item["numero"] for item in ranking_elliott[:40]}
    pool_inicial = top_40_dezenas | DEZENAS_BASE_3010

    analise_elite = extrair_analise_elite(dados_calor)

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
        soma_raw = cfg_p.get("soma", (150, 190))
        st.session_state["sel_soma"] = (int(soma_raw[0]), int(soma_raw[1]))

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
                [f"{n:02d}" for n in sorted(st.session_state.historico[-1])]
            )

    # ==============================================================================
    # INTERFACE PRINCIPAL
    # ==============================================================================
    st.title("🍀 MEGA60 - PAINEL BLINDADO")
    st.caption("MATRIZ 6x10 • ALTO CONTRASTE PRETO • MOTOR ROBUSTO SEM RISCO DE FALHA")

    tab_cartela, tab_config, tab_volante, tab_upload, tab_historico = st.tabs([
        "🎟️ Cartela & Seleção Elite",
        "🎛️ Filtros & Engenharia Reversa",
        "🗺️ Volante & Raio-X",
        "📥 Upload & Filtragem Sucessiva",
        "📊 Histórico & API Caixa"
    ])

    # ==============================================================================
    # ABA 1: CARTELA & PAINEL DE ELITE
    # ==============================================================================
    with tab_cartela:
        with st.container(border=True):
            st.markdown("### 🏆 NÚMEROS DE ELITE SEPARADOS (FONTE GRANDE E PRETO)")
            st.markdown("**Calculados pelo Motor de Elliott sobre os concursos ativos:**")

            c_el1, c_el2, c_el3, c_el4 = st.columns(4)

            with c_el1:
                st.markdown("#### 💎 MELHORES PRIMOS")
                p_txt = " • ".join([f"{n:02d}" for n in analise_elite["primos"]])
                st.markdown(f"<div style='font-size:1.5rem;color:#000000;font-weight:900;'>{p_txt}</div>", unsafe_allow_html=True)

            with c_el2:
                st.markdown("#### ⚖️ 3 MELHORES PARES")
                pa_txt = " • ".join([f"{n:02d}" for n in analise_elite["pares"]])
                st.markdown(f"<div style='font-size:1.5rem;color:#000000;font-weight:900;'>{pa_txt}</div>", unsafe_allow_html=True)

            with c_el3:
                st.markdown("#### ⚡ MELHORES ÍMPARES")
                i_txt = " • ".join([f"{n:02d}" for n in analise_elite["impares"]])
                st.markdown(f"<div style='font-size:1.5rem;color:#000000;font-weight:900;'>{i_txt}</div>", unsafe_allow_html=True)

            with c_el4:
                st.markdown("#### 📐 MELHORES DIAGONAIS")
                dc_txt = ", ".join([f"DC{d+1:02d}" for d in analise_elite["dc"]])
                dd_txt = ", ".join([f"DD{d+1:02d}" for d in analise_elite["dd"]])
                st.markdown(f"<div style='font-size:1.25rem;color:#000000;font-weight:900;'>CRESCENTES: {dc_txt}<br>DECRESCENTES: {dd_txt}</div>", unsafe_allow_html=True)

            st.divider()

            pool_elite_ordenado = analise_elite["pool_elite"]
            dezenas_elite_txt = " - ".join([f"{n:02d}" for n in pool_elite_ordenado])
            st.markdown(
                f"<div style='font-size:1.35rem;color:#000000;font-weight:900;padding:8px 0;'>"
                f"🎯 POOL CONSOLIDADO DAS ELITES ({len(pool_elite_ordenado)} DEZENAS AGRUPADAS):<br>"
                f"<span style='background:#facc15;padding:6px 14px;border:3px solid #000000;border-radius:6px;display:inline-block;margin-top:8px;'>"
                f"{dezenas_elite_txt}</span></div>",
                unsafe_allow_html=True
            )

            c_act1, c_act2 = st.columns([1, 1])
            with c_act1:
                if st.button("⭐ CARREGAR SOMENTE ESTE POOL DE ELITE NA CARTELA", use_container_width=True, type="primary"):
                    st.session_state.pool_trabalho = set(pool_elite_ordenado)
                    st.rerun()

            with c_act2:
                if st.button("🎛️ GERAR E ATIVAR FILTRO COM ESTAS CONDICIONANTES", use_container_width=True):
                    preset_elite = extrair_filtros_de_jogo(pool_elite_ordenado, modo="flexivel")
                    st.session_state.presets_filtros["FILTRO_ELITE_CONDICIONANTES"] = preset_elite
                    aplicar_preset("FILTRO_ELITE_CONDICIONANTES")
                    st.success("FILTRO 'FILTRO_ELITE_CONDICIONANTES' ATIVADO NA ABA 2!")
                    st.rerun()

        st.write("")

        st.subheader("🎟️ CARTELA DE 60 NÚMEROS (MATRIZ 6x10)")
        st.markdown("**AMARELO = MARCADO NO POOL | BRANCO = NÃO MARCADO | ⭐ = ELITE**")

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
            if st.button("⚡ +9 Fibonacci", use_container_width=True):
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

        set_elite = set(analise_elite["pool_elite"])

        for r in range(6):
            cols = st.columns(10)
            for c in range(10):
                n = r * 10 + c + 1
                meta = dados_calor[n]
                esta_ativa = n in st.session_state.pool_trabalho
                e_elite = n in set_elite

                tipo_btn = "primary" if esta_ativa else "secondary"
                star_ico = "⭐" if e_elite else ""
                rotulo = f"{n:02d}{star_ico}\n({meta['score']:.0f}p)"

                with cols[c]:
                    if st.button(rotulo, key=f"btn_num_{n}", type=tipo_btn, use_container_width=True):
                        toggle_dezena(n)
                        st.rerun()

        st.divider()
        col_inf1, col_inf2 = st.columns([3, 1])
        qtd_sel = len(st.session_state.pool_trabalho)
        with col_inf1:
            dezenas_txt = " - ".join([f"{n:02d}" for n in sorted(list(st.session_state.pool_trabalho))])
            st.markdown(
                f"<div style='font-size:1.3rem;font-weight:900;color:#000000;background:#fef08a;border:3px solid #000000;padding:12px;border-radius:8px;'>"
                f"DEZENAS ATIVAS NO POOL ({qtd_sel}):<br>{dezenas_txt if dezenas_txt else 'NENHUMA SELECIONADA'}</div>",
                unsafe_allow_html=True
            )
        with col_inf2:
            total_comb = math.comb(qtd_sel, 6) if qtd_sel >= 6 else 0
            st.metric("Total Selecionado", f"{qtd_sel} / 60")
            st.markdown(f"<div style='font-size:1.2rem;font-weight:900;color:#000000;'>Jogos Brutos: {total_comb:,}</div>", unsafe_allow_html=True)

    # ==============================================================================
    # ABA 2: CONFIGURAÇÃO DOS FILTROS & MOTOR COMBINATÓRIO
    # ==============================================================================
    with tab_config:
        st.markdown("### 🎛️ FILTROS ESTRUTURAIS & ENGENHARIA REVERSA")

        tipo_reverso = st.radio(
            "Selecione a Rotina de Engenharia Reversa:",
            [
                "🏛️ Rotina 1: Histórica Multiconcursos (Concursos Anteriores em Lote)",
                "⚡ Rotina 2: Amostra Personalizada (Digitar 6 a 60 Dezenas)"
            ],
            horizontal=True
        )

        if tipo_reverso.startswith("🏛️ Rotina 1"):
            with st.container(border=True):
                st.markdown("#### 🏛️ ENGENHARIA REVERSA MULTICONCURSOS")
                total_disp = len(st.session_state.historico)
                col_m1, col_m2, col_m3 = st.columns([1.5, 1.8, 1.7])
                with col_m1:
                    qtd_concursos_sel = st.slider(
                        "Concursos Anteriores:",
                        min_value=1,
                        max_value=max(1, total_disp),
                        value=min(10, total_disp)
                    )
                with col_m2:
                    nome_filtro_multi = st.text_input(
                        "Nome do Filtro:",
                        value=f"FILTRO_ULT_{qtd_concursos_sel}_CONCURSOS",
                        key="input_nome_multi"
                    )
                    carregar_pool_multi = st.checkbox(
                        "Carregar Dezenas no Pool Ativo",
                        value=True
                    )
                with col_m3:
                    tolerancia_multi = st.selectbox(
                        "Margem Estrutural:",
                        ["Envelope Preciso (100% dos Sorteios)", "Envelope Flexível (Margem +1 / -1)"],
                        index=0,
                        key="sel_tolerancia_multi"
                    )

                if st.button("🚀 PROCESSAR CONCURSOS, CRIAR E ATIVAR FILTRO", type="primary", use_container_width=True):
                    with st.spinner("Processando..."):
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
                            "status": "CONCLUÍDO & ATIVO",
                            "modo": tolerancia_multi,
                            "audit": audit_dados,
                            "pool_atualizado": carregar_pool_multi
                        }

                        st.success(f"Filtro para os últimos {qtd_concursos_sel} concursos ativado!")
                        st.rerun()

        else:
            with st.container(border=True):
                st.markdown("#### ⚡ ENGENHARIA REVERSA POR DEZENAS DIGITADAS")
                col_input_res, col_input_nome, col_input_tipo = st.columns([2.5, 1.8, 1.7])
                with col_input_res:
                    entrada_dezenas_filtro = st.text_area(
                        "Dezenas (6 a 60 números):",
                        value=st.session_state.input_resultado_reverso_val,
                        height=75,
                        key="input_resultado_reverso"
                    )
                with col_input_nome:
                    nome_filtro_novo = st.text_input(
                        "Nome do Filtro:",
                        value="MEU_NOVO_FILTRO",
                        key="input_nome_filtro_auto"
                    )
                    substituir_pool_opcao = st.checkbox(
                        "Definir como Pool Ativo",
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
                    if st.button("⚡ GERAR, GRAVAR E ATIVAR FILTRO", type="primary", use_container_width=True):
                        nums_parse = [int(x) for x in re.findall(r"\b\d+\b", entrada_dezenas_filtro)]
                        dezenas_limpas = sorted(list(set([n for n in nums_parse if 1 <= n <= 60])))
                        total_identificado = len(dezenas_limpas)

                        if total_identificado < 6:
                            st.error(f"Informe pelo menos 6 dezenas válidas (entre 01 e 60). Identificadas: {total_identificado}.")
                        elif total_identificado > 60:
                            st.error(f"O limite máximo é 60 dezenas. Informadas: {total_identificado}.")
                        elif not nome_filtro_novo.strip():
                            st.error("Informe um nome para o filtro.")
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
                                "status": "PROCESSADO & ATIVO",
                                "modo": tipo_tolerancia,
                                "pool_atualizado": substituir_pool_opcao
                            }

                            st.success(f"Filtro '{nome_salvar}' ativado com sucesso!")
                            st.rerun()

                with c_btn_rev2:
                    st.button("🔄 Puxar Último Concurso", on_click=cb_puxar_ultimo, use_container_width=True)

        # Linha de Trabalho
        st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
        if st.session_state.linha_trabalho_reverso:
            lt = st.session_state.linha_trabalho_reverso
            is_multi = lt.get("tipo") == "MULTICONCURSOS"
            dezenas_formatadas = " - ".join([f"{n:02d}" for n in sorted(lt["dezenas"])])

            if is_multi:
                detalhes_audit = (
                    f"• Concursos Analisados: {lt['qtd_concursos']}<br>"
                    f"• Dezenas Auditadas: {dezenas_formatadas}<br>"
                    f"• Soma Observada: {lt['audit']['soma_min_real']} até {lt['audit']['soma_max_real']} | "
                    f"Primos: {lt['audit']['primos_reais']} | Moldura: {lt['audit']['moldura_reais']}"
                )
            else:
                detalhes_audit = f"• Total de Dezenas: {lt['qtd_dezenas']}<br>• Dezenas: {dezenas_formatadas}"

            st.markdown(
                f"""
                <div style="background:#ffffff;border:4px solid #000000;border-radius:8px;padding:16px;margin-bottom:15px;">
                    <div style="font-weight:900;color:#000000;font-size:16px;">
                        STATUS DA LINHA: {lt['status']} ({lt['nome']}) | 🕒 {lt['timestamp']}
                    </div>
                    <div style="margin-top:10px;font-size:14px;color:#000000;font-weight:800;line-height:1.7;">
                        {detalhes_audit}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

        # Gerenciador de Predefinições
        with st.container(border=True):
            st.markdown("#### 💾 GERENCIADOR DE PREDEFINIÇÕES")
            col_puxar, col_gravar = st.columns(2)

            with col_puxar:
                lista_nomes = list(st.session_state.presets_filtros.keys())
                filtro_escolhido = st.selectbox("Carregar Filtro Salvo:", lista_nomes, index=0, key="select_preset_load")

                c_pux1, c_pux2 = st.columns(2)
                with c_pux1:
                    if st.button("🚀 APLICAR PREDEFINIÇÃO", use_container_width=True):
                        aplicar_preset(filtro_escolhido)
                        st.success(f"Filtro '{filtro_escolhido}' carregado!")
                        st.rerun()
                with c_pux2:
                    json_presets = json.dumps(st.session_state.presets_filtros, indent=2, ensure_ascii=False)
                    st.download_button(
                        "💾 BAIXAR (.JSON)",
                        data=json_presets,
                        file_name="meus_filtros_mega60.json",
                        mime="application/json",
                        use_container_width=True
                    )

            with col_gravar:
                nome_novo_filtro = st.text_input("Gravar Configuração Manual Atual:", placeholder="Ex: Meu Filtro 1", key="input_nome_filtro_manual")

                c_grv1, c_grv2 = st.columns(2)
                with c_grv1:
                    if st.button("💾 GRAVAR MANUAL", use_container_width=True):
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
                                "soma": (int(st.session_state.get("sel_soma", (150, 190))[0]), int(st.session_state.get("sel_soma", (150, 190))[1]))
                            }
                            st.session_state.presets_filtros[nome_novo_filtro.strip()] = novo_preset
                            st.success(f"Predefinição '{nome_novo_filtro.strip()}' gravada!")
                            st.rerun()
                with c_grv2:
                    arq_json_upload = st.file_uploader("Importar (.JSON):", type=["json"], label_visibility="collapsed")
                    if arq_json_upload is not None:
                        try:
                            st.session_state.presets_filtros.update(json.load(arq_json_upload))
                            st.success("Importado com sucesso!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao ler JSON: {e}")

        st.divider()
        opcoes_nomes = list(OPCOES_QUANTIDADE.keys())

        with st.container(border=True):
            st.markdown("#### 1️⃣ LINHAS INDIVIDUAIS (L01 a L06)")
            cols_l = st.columns(6)
            limites_linhas = []
            for r in range(6):
                with cols_l[r]:
                    val_padrao = st.session_state.get(f"sel_l_{r}", "0 a 2")
                    idx_sel = opcoes_nomes.index(val_padrao) if val_padrao in opcoes_nomes else 0
                    esc = st.selectbox(f"Linha {r+1:02d}", opcoes_nomes, index=idx_sel, key=f"sel_l_{r}")
                    limites_linhas.append(OPCOES_QUANTIDADE[esc])

        with st.container(border=True):
            st.markdown("#### 2️⃣ COLUNAS INDIVIDUAIS (C01 a C10)")
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
                st.markdown("#### 3️⃣ DIAGONAIS CRESCENTES (DC01 a DC10 /)")
                with st.expander("Expandir Diagonais Crescentes", expanded=False):
                    limites_dc = []
                    for d in range(10):
                        val_padrao = st.session_state.get(f"sel_dc_{d}", "0 a 2")
                        idx_sel = opcoes_nomes.index(val_padrao) if val_padrao in opcoes_nomes else 0
                        esc = st.selectbox(f"DC{d+1:02d}", opcoes_nomes, index=idx_sel, key=f"sel_dc_{d}")
                        limites_dc.append(OPCOES_QUANTIDADE[esc])
        with c_diag2:
            with st.container(border=True):
                st.markdown("#### 4️⃣ DIAGONAIS DECRESCENTES (DD01 a DD10 \\)")
                with st.expander("Expandir Diagonais Decrescentes", expanded=False):
                    limites_dd = []
                    for d in range(10):
                        val_padrao = st.session_state.get(f"sel_dd_{d}", "0 a 2")
                        idx_sel = opcoes_nomes.index(val_padrao) if val_padrao in opcoes_nomes else 0
                        esc = st.selectbox(f"DD{d+1:02d}", opcoes_nomes, index=idx_sel, key=f"sel_dd_{d}")
                        limites_dd.append(OPCOES_QUANTIDADE[esc])

        with st.container(border=True):
            st.markdown("#### 5️⃣ PRIMOS, PARES, MOLDURA E FAIXA DE SOMA")
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
                val_soma_estado = st.session_state.get("sel_soma", (150, 190))
                if isinstance(val_soma_estado, (list, tuple)) and len(val_soma_estado) == 2:
                    soma_min_val = int(val_soma_estado[0])
                    soma_max_val = int(val_soma_estado[1])
                else:
                    soma_min_val, soma_max_val = 150, 190

                faixa_soma = st.slider(
                    "Faixa de Soma:",
                    min_value=50,
                    max_value=320,
                    value=(soma_min_val, soma_max_val),
                    key="sel_soma"
                )

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

        st.markdown("#### ⚙️ CONTROLE DE EXECUÇÃO")
        c_ctrl1, c_ctrl2 = st.columns([2, 2])
        with c_ctrl1:
            sem_limite = st.checkbox(
                "♾️ SEM LIMITE (GERAR TODAS AS APROVADAS)",
                value=True
            )
        with c_ctrl2:
            if not sem_limite:
                teto_apostas = st.number_input(
                    "Teto Máximo de Jogos:",
                    min_value=1,
                    max_value=2000000,
                    value=5000,
                    step=500
                )
            else:
                teto_apostas = None
                st.info("Teto desativado: Todas as combinações válidas serão calculadas.")

        placeholder_metricas = st.empty()
        barra_progresso = st.progress(0, text="Pronto para processar...")

        pode_processar = len(st.session_state.pool_trabalho) >= 6

        col_btn_gen, col_btn_raw = st.columns(2)
        with col_btn_gen:
            if st.button("🚀 GERAR E FILTRAR APOSTAS", use_container_width=True, disabled=not pode_processar, type="primary"):
                if not primos_sel or not par_sel or not moldura_sel:
                    st.error("Selecione os parâmetros de Primos, Pares e Moldura.")
                else:
                    with st.spinner("🛠️ Processando Motor Combinatório..."):
                        t0 = time.time()
                        resultados = executar_varredura_pool(
                            st.session_state.pool_trabalho,
                            config_total,
                            barra_progresso,
                            placeholder_metricas,
                            teto_max=teto_apostas
                        )
                        t_fim = time.time() - t0
                        st.session_state.jogos_aprovados = resultados
                        total_gerado = len(resultados)

                        if total_gerado > 0:
                            st.success(f"✅ Sucesso: {total_gerado:,} apostas geradas em {t_fim:.2f}s.")
                        else:
                            st.warning(f"⚠️ Nenhuma combinação atendeu aos filtros selecionados em {t_fim:.2f}s.")

        with col_btn_raw:
            k_pool = len(st.session_state.pool_trabalho)
            comb_totais_pool = math.comb(k_pool, 6) if k_pool >= 6 else 0
            if st.button(f"📦 EXPORTAR POOL BRUTO ({comb_totais_pool:,} JOGOS)", use_container_width=True, disabled=not pode_processar):
                with st.spinner("Gerando arquivo..."):
                    dezenas_cands = sorted(list(st.session_state.pool_trabalho))
                    buffer_txt = io.StringIO()
                    for c in combinations(dezenas_cands, 6):
                        buffer_txt.write(" ".join([f"{n:02d}" for n in c]) + "\n")
                    st.session_state["raw_pool_file"] = buffer_txt.getvalue()
                    st.success("Pool bruto gerado!")

        if "raw_pool_file" in st.session_state:
            st.download_button(
                "💾 BAIXAR ARQUIVO DO POOL BRUTO (.TXT)",
                data=st.session_state["raw_pool_file"],
                file_name=f"mega60_pool_bruto_{len(st.session_state.pool_trabalho)}dezenas.txt",
                mime="text/plain",
                use_container_width=True
            )

        if st.session_state.jogos_aprovados:
            qtd_aprov = len(st.session_state.jogos_aprovados)
            st.success(f"Total Aprovado: {qtd_aprov:,} apostas geradas (menor para o maior).")
            txt_saida = "\n".join([" ".join([f"{n:02d}" for n in j]) for j in st.session_state.jogos_aprovados])

            c_d1, c_d2 = st.columns([3, 1])
            with c_d1:
                st.download_button(
                    "📥 BAIXAR JOGOS APROVADOS (.TXT)",
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
        st.subheader("DISSECAÇÃO DA CARTELA")
        jogos_exibir = st.session_state.jogos_aprovados or st.session_state.jogos_upload

        if jogos_exibir:
            total_jogos = len(jogos_exibir)
            sel_idx = st.slider("Aposta para inspecionar:", 1, total_jogos, 1) if total_jogos > 1 else 1
            jogo_ativo = sorted(jogos_exibir[sel_idx - 1])
            marcadas = set(jogo_ativo)

            c_v1, c_v2 = st.columns([1, 1])
            with c_v1:
                celulas = ""
                for r in range(6):
                    for c in range(10):
                        n = r * 10 + c + 1
                        if n in marcadas:
                            celulas += f'<div style="width:42px;height:42px;background:#facc15;color:#000000;border:3px solid #000000;font-weight:900;border-radius:6px;display:flex;align-items:center;justify-content:center;font-family:monospace;font-size:16px;">{n:02d}</div>'
                        else:
                            celulas += f'<div style="width:42px;height:42px;background:#ffffff;color:#000000;border:1px solid #000000;font-weight:900;border-radius:6px;display:flex;align-items:center;justify-content:center;font-family:monospace;font-size:16px;">{n:02d}</div>'

                html_cartela = f"""
                <!DOCTYPE html><html><head><meta charset="utf-8">
                <style>*{{box-sizing:border-box;}}body{{margin:0;padding:0;display:flex;justify-content:center;background:transparent;font-family:Arial,sans-serif;}}
                .box{{background:#fff;border:4px solid #000000;border-radius:10px;padding:12px;width:fit-content;}}
                .grid{{display:grid;grid-template-columns:repeat(10,42px);gap:5px;}}</style></head><body>
                <div class="box"><div style="font-weight:900;font-size:16px;margin-bottom:10px;color:#000000;text-align:center;">JOGO #{sel_idx:04d}: {' - '.join([f'{n:02d}' for n in jogo_ativo])}</div>
                <div class="grid">{celulas}</div></div></body></html>
                """
                components.html(html_cartela, height=360, scrolling=False)

            with c_v2:
                with st.container(border=True):
                    st.markdown("#### 🔬 RAIO-X DO JOGO")
                    cnt_linhas = Counter(PROPS[n]["r"] + 1 for n in jogo_ativo)
                    cnt_colunas = Counter(PROPS[n]["c"] + 1 for n in jogo_ativo)
                    cnt_dc = Counter(PROPS[n]["dc"] + 1 for n in jogo_ativo)
                    cnt_dd = Counter(PROPS[n]["dd"] + 1 for n in jogo_ativo)

                    st.markdown("**Linhas:** " + " • ".join([f"L{k}: **{v}x**" for k, v in sorted(cnt_linhas.items())]))
                    st.markdown("**Colunas:** " + " • ".join([f"C{k:02d}: **{v}x**" for k, v in sorted(cnt_colunas.items())]))
                    st.markdown("**Diagonais Cresc.:** " + " • ".join([f"DC{k:02d}: **{v}x**" for k, v in sorted(cnt_dc.items())]))
                    st.markdown("**Diagonais Decresc.:** " + " • ".join([f"DD{k:02d}: **{v}x**" for k, v in sorted(cnt_dd.items())]))

                    pr = sum(1 for n in jogo_ativo if PROPS[n]["is_primo"])
                    pa = sum(1 for n in jogo_ativo if PROPS[n]["is_par"])
                    mo = sum(1 for n in jogo_ativo if PROPS[n]["is_moldura"])
                    st.divider()
                    st.markdown(f"**Pares/Ímpares:** `{pa}P / {6-pa}I` | **Primos:** `{pr}` | **Moldura:** `{mo}` | **Soma:** `{sum(jogo_ativo)}`")
        else:
            st.info("Gere apostas para inspecionar no volante.")

    # ==============================================================================
    # ABA 4: UPLOAD & FILTRAGEM SUCESSIVA
    # ==============================================================================
    with tab_upload:
        st.subheader("📥 UPLOAD, FILTRAGEM & CONFERÊNCIA")
        arquivo_enviado = st.file_uploader("Carregue seu arquivo de apostas (.txt ou .csv):", type=["txt", "csv"])

        if arquivo_enviado is not None:
            conteudo = arquivo_enviado.read()
            jogos_carregados, invalidos = processar_arquivo_upload(conteudo)
            st.session_state.jogos_upload = jogos_carregados
            if invalidos > 0:
                st.warning(f"⚠️ {invalidos} linha(s) ignoradas.")

        if st.session_state.jogos_upload:
            jogos_up = st.session_state.jogos_upload
            total_up = len(jogos_up)
            st.success(f"Arquivo Carregado: {total_up:,} apostas em memória.")

            with st.container(border=True):
                st.markdown("#### ⚡ FILTRAR ARQUIVO CARREGADO")

                c_flt1, c_flt2 = st.columns([2, 1])
                with c_flt1:
                    if st.button("🔍 APLICAR FILTROS ATIVOS NO ARQUIVO", type="primary", use_container_width=True):
                        with st.spinner("Filtrando apostas..."):
                            t_ini_flt = time.time()
                            aprovados_do_arquivo = [
                                j for j in jogos_up if validar_aposta_final_6(tuple(j), config_total)
                            ]
                            t_fim_flt = time.time() - t_ini_flt
                            st.session_state.jogos_filtrados_upload = aprovados_do_arquivo
                            st.success(f"Concluído em {t_fim_flt:.2f}s! {len(aprovados_do_arquivo):,} de {total_up:,} aprovadas.")

                if st.session_state.jogos_filtrados_upload:
                    qtd_flt = len(st.session_state.jogos_filtrados_upload)
                    txt_flt = "\n".join([" ".join([f"{n:02d}" for n in j]) for j in st.session_state.jogos_filtrados_upload])
                    with c_flt2:
                        st.download_button(
                            f"💾 BAIXAR LOTE FILTRADO ({qtd_flt:,} JOGOS)",
                            data=txt_flt,
                            file_name=f"mega60_lote_filtrado_{qtd_flt}.txt",
                            mime="text/plain",
                            use_container_width=True
                        )

            st.divider()

            col_diag_left, col_conf_right = st.columns([1, 1], gap="large")

            with col_diag_left:
                st.markdown("### 📊 DIAGNÓSTICO DO ARQUIVO")
                cnt_nums = Counter()
                somas = []
                for j in jogos_up:
                    cnt_nums.update(j)
                    somas.append(sum(j))

                m1, m2, m3 = st.columns(3)
                m1.metric("Total", f"{total_up:,}")
                m2.metric("Soma Média", f"{sum(somas)/len(somas):.1f}")
                m3.metric("Mais Frequente", f"{cnt_nums.most_common(1)[0][0]:02d}")

                st.markdown("#### 🔥 FREQUÊNCIA NA MATRIZ")
                celulas_up_heat = ""
                for r in range(6):
                    for c in range(10):
                        n = r * 10 + c + 1
                        freq = cnt_nums[n]
                        bg = "#ffffff" if freq == 0 else "#fef08a"
                        celulas_up_heat += f'<div style="width:40px;height:40px;background:{bg};color:#000000;border-radius:6px;display:flex;flex-direction:column;align-items:center;justify-content:center;font-family:monospace;border:2px solid #000000;box-sizing:border-box;"><span style="font-size:13px;font-weight:900;">{n:02d}</span><span style="font-size:10px;font-weight:900;">{freq}x</span></div>'

                html_up = f'<!DOCTYPE html><html><head><meta charset="utf-8"><style>*{{box-sizing:border-box;}}body{{margin:0;padding:0;background:transparent;display:flex;justify-content:center;font-family:Arial,sans-serif;}}.box{{background:#fff;border:4px solid #000000;border-radius:10px;padding:10px;width:fit-content;}}.grid{{display:grid;grid-template-columns:repeat(10,40px);gap:4px;}}</style></head><body><div class="box"><div class="grid">{celulas_up_heat}</div></div></body></html>'
                components.html(html_up, height=310, scrolling=False)

            with col_conf_right:
                st.markdown("### 🎯 CONFERÊNCIA DE RESULTADOS")
                ult_sorteio = st.session_state.historico[-1] if st.session_state.historico else [4, 12, 18, 30, 35, 54]
                txt_padrao = " ".join([f"{n:02d}" for n in sorted(ult_sorteio)])

                modo_origem = st.radio("Origem:", ["Último Sorteio Oficial", "Digitar Manualmente"], horizontal=True)
                if modo_origem == "Último Sorteio Oficial":
                    dezenas_conf = sorted(ult_sorteio)
                else:
                    entrada_manual = st.text_input("6 Dezenas Sorteadas:", value=txt_padrao)
                    nums_man = [int(x) for x in re.findall(r"\b\d+\b", entrada_manual)]
                    dezenas_conf = sorted(list(set([n for n in nums_man if 1 <= n <= 60])))

                if len(dezenas_conf) != 6:
                    st.error("Informe exatamente 6 dezenas distintas entre 01 e 60.")
                else:
                    render_cartao_sorteio_html(dezenas_conf, titulo="SORTEIO CONFERIDO")
                    base_conferir = st.session_state.jogos_filtrados_upload or jogos_up
                    relatorio_conf, placar_conf = conferir_apostas_contra_sorteio(base_conferir, dezenas_conf)

                    c_s, c_q, c_qd, c_t = st.columns(4)
                    c_s.metric("Sena (6)", f"{len(placar_conf[6])}")
                    c_q.metric("Quina (5)", f"{len(placar_conf[5])}")
                    c_qd.metric("Quadra (4)", f"{len(placar_conf[4])}")
                    c_t.metric("Terno (3)", f"{len(placar_conf[3])}")

                    tot_prem = len(placar_conf[6]) + len(placar_conf[5]) + len(placar_conf[4])
                    if tot_prem > 0:
                        st.success(f"{tot_prem} aposta(s) premiada(s) encontradas!")
                        jogos_premiados_txt = "\n".join([
                            f"{' '.join([f'{n:02d}' for n in it['jogo']])} | {it['qtd_acertos']} ACERTOS"
                            for it in relatorio_conf if it["qtd_acertos"] >= 4
                        ])
                        st.download_button(
                            "📥 BAIXAR APOSTAS PREMIADAS (.TXT)",
                            data=jogos_premiados_txt,
                            file_name=f"mega60_apostas_premiadas_{tot_prem}.txt",
                            mime="text/plain",
                            use_container_width=True
                        )
                    else:
                        st.warning("Nenhuma aposta alcançou 4, 5 ou 6 acertos.")

                    jogos_com_acerto = [it for it in relatorio_conf if it["qtd_acertos"] >= 4] or relatorio_conf
                    opcoes_map = {
                        it["num_aposta"]: f"Aposta #{it['num_aposta']:04d} — {it['qtd_acertos']} acertos"
                        for it in jogos_com_acerto[:50]
                    }
                    idx_escolhido = st.selectbox(
                        "Inspecionar no Volante:",
                        list(opcoes_map.keys()),
                        format_func=lambda x: opcoes_map[x]
                    )
                    if idx_escolhido is not None:
                        item_ativo = next(it for it in relatorio_conf if it["num_aposta"] == idx_escolhido)
                        render_volante_conferencia(
                            item_ativo["jogo"],
                            dezenas_conf,
                            titulo=f"Aposta #{item_ativo['num_aposta']:04d} ({item_ativo['qtd_acertos']} Acertos)"
                        )
        else:
            st.info("Carregue um arquivo para conferência.")

    # ==============================================================================
    # ABA 5: HISTÓRICO & API CAIXA
    # ==============================================================================
    with tab_historico:
        st.subheader("BASE DE CONCURSOS OFICIAIS")
        st.markdown(f"**Total em memória:** `{len(st.session_state.historico)}` ({st.session_state.origem})")

        if st.button("🌐 SINCRONIZAR COM A CAIXA AGORA", type="primary"):
            with st.spinner("Conectando..."):
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
                            st.warning("Formato inesperado.")
                    else:
                        st.warning(f"Erro HTTP {r.status_code}.")
                except Exception as e:
                    st.error(f"Erro: {e}")

        with st.expander("Ver Concursos Armazenados"):
            for i, sorteio in enumerate(reversed(st.session_state.historico), start=1):
                st.markdown(f"**Concurso #{i:02d}:** `{' - '.join([f'{n:02d}' for n in sorted(sorteio)])}`")

except Exception as erro_global:
    # CAPTURA QUALQUER ERRO E EXIBE NA TELA EM PRETO E AMARELO
    st.error("🚨 Ocorreu um erro na execução do aplicativo:")
    st.code(traceback.format_exc())
