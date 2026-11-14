#!/usr/bin/env python3
"""Gera os cards de estatísticas em português do README do perfil.

Uso local:   python3 scripts/gerar-cards.py          (usa o token do `gh`)
Uso na CI:   GITHUB_TOKEN definido pela Action       (ver .github/workflows/atualizar-cards.yml)

Os cards são gravados em .github/cards/*.svg e são lidos pelo README.
"""
import json
import math
import os
import subprocess
import sys
import urllib.request
from collections import Counter

USUARIO = "Tyago-santos"
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASTA = os.path.join(RAIZ, ".github", "cards")

FUNDOS = "#0d1117"
BORDA = "#30363d"
AZUL = "#58a6ff"
CINZA = "#8b949e"
BRANCO = "#ffffff"
VERDE = "#3fb950"

MESES_PT = ["jan", "fev", "mar", "abr", "mai", "jun",
            "jul", "ago", "set", "out", "nov", "dez"]

CORES_LINGUAGEM = {
    "TypeScript": "#3178C6",
    "JavaScript": "#F7DF1E",
    "CSS": "#1572B6",
    "HTML": "#E34F26",
    "Python": "#3572A5",
    "Java": "#b07219",
    "Sem linguagem": "#8b949e",
}


# ---------------------------------------------------------------- API

def obter_token():
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        return token
    try:
        return subprocess.check_output(["gh", "auth", "token"], text=True).strip()
    except Exception:
        sys.exit("Erro: defina GITHUB_TOKEN/GH_TOKEN ou autentique o `gh`.")


def graphql(query):
    requisicao = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query}).encode(),
        headers={
            "Authorization": f"Bearer {obter_token()}",
            "Content-Type": "application/json",
            "User-Agent": "gerar-cards-perfil",
        },
    )
    with urllib.request.urlopen(requisicao, timeout=60) as resposta:
        carga = json.load(resposta)
    if carga.get("errors"):
        sys.exit(f"Erro do GraphQL: {carga['errors']}")
    return carga["data"]["user"]


CONSULTA = """
query {
  user(login: "%s") {
    contributionsCollection {
      totalCommitContributions
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
    pullRequests { totalCount }
    issues { totalCount }
    repositories(first: 100, ownerAffiliations: OWNER) {
      totalCount
      nodes { name stargazerCount primaryLanguage { name } }
    }
  }
}
""" % USUARIO


def coletar():
    dados = graphql(CONSULTA)
    repos = dados["repositories"]["nodes"]
    calendario = dados["contributionsCollection"]["contributionCalendar"]

    por_mes = {}
    for semana in calendario["weeks"]:
        for dia in semana["contributionDays"]:
            if dia["contributionCount"]:
                chave = dia["date"][:7]
                por_mes[chave] = por_mes.get(chave, 0) + dia["contributionCount"]

    return {
        "commits": dados["contributionsCollection"]["totalCommitContributions"],
        "pr": dados["pullRequests"]["totalCount"],
        "issues": dados["issues"]["totalCount"],
        "total_contribuicoes": calendario["totalContributions"],
        "repos": dados["repositories"]["totalCount"],
        "estrelas": sum(r["stargazerCount"] for r in repos),
        "linguagens": Counter(
            (r["primaryLanguage"] or {}).get("name", "Sem linguagem") for r in repos
        ),
        "por_mes": dict(sorted(por_mes.items())[-12:]),
    }


# ------------------------------------------------------------- cards

def cartao(tamanho=(340, 200)):
    largura, altura = tamanho
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{largura}" height="{altura}" '
        f'viewBox="0 0 {largura} {altura}" font-family="Segoe UI, Ubuntu, Helvetica, Arial, sans-serif">'
        f'<rect width="{largura}" height="{altura}" rx="12" fill="{FUNDOS}" stroke="{BORDA}"/>'
    )


def texto(x, y, conteudo, tamanho=13, cor=BRANCO, peso=None, ancora="start"):
    extra = f' font-weight="{peso}"' if peso else ""
    return (
        f'<text x="{x}" y="{y}" font-size="{tamanho}" fill="{cor}" '
        f'text-anchor="{ancora}"{extra}>{conteudo}</text>'
    )


def card_estatisticas(d):
    svg = [cartao(), texto(22, 36, "Estatísticas", 17, AZUL, "bold")]
    linhas = [
        ("#e3b341", "Total de estrelas", d["estrelas"]),
        ("#3fb950", "Total de commits", d["commits"]),
        ("#a371f7", "Pull requests", d["pr"]),
        ("#f85149", "Issues", d["issues"]),
        ("#58a6ff", "Repositórios", d["repos"]),
    ]
    y = 78
    for cor, rotulo, valor in linhas:
        svg.append(f'<circle cx="30" cy="{y - 4}" r="5" fill="{cor}"/>')
        svg.append(texto(46, y, rotulo, 13, CINZA))
        svg.append(texto(318, y, str(valor), 14, BRANCO, "bold", "end"))
        y += 26
    svg.append("</svg>")
    return "".join(svg)


def arco(cx, cy, raio, grossura, inicio, comprimento):
    """Segmento de anel desenhado com stroke-dasharray (círculo completo = 1)."""
    circunferencia = 2 * math.pi * raio
    deslocamento = -inicio * circunferencia
    return (
        f'<circle cx="{cx}" cy="{cy}" r="{raio}" fill="none" '
        f'stroke-width="{grossura}" stroke-dasharray="{comprimento * circunferencia:.2f} '
        f'{circunferencia:.2f}" stroke-dashoffset="{deslocamento:.2f}" '
        f'transform="rotate(-90 {cx} {cy})"/>'
    )


def card_linguagens(linguagens):
    svg = [cartao(), texto(22, 36, "Linguagens por repositório", 15, AZUL, "bold")]
    total = sum(linguagens.values()) or 1
    itens = sorted(linguagens.items(), key=lambda item: -item[1])[:5]

    cx, cy, raio, grossura = 92, 118, 52, 22
    angulo = 0.0
    for nome, quantidade in itens:
        fatia = quantidade / total
        cor = CORES_LINGUAGEM.get(nome, "#8b949e")
        svg.append(f'<g stroke="{cor}" fill="none" stroke-width="{grossura}">')
        svg.append(arco(cx, cy, raio, grossura, angulo, fatia))
        svg.append("</g>")
        angulo += fatia

    y = 74
    for nome, quantidade in itens:
        cor = CORES_LINGUAGEM.get(nome, "#8b949e")
        svg.append(f'<rect x="176" y="{y - 9}" width="10" height="10" rx="2" fill="{cor}"/>')
        svg.append(texto(194, y, nome, 12, "#c9d1d9"))
        svg.append(texto(318, y, str(quantidade), 12, BRANCO, "bold", "end"))
        y += 24
    svg.append("</svg>")
    return "".join(svg)


def card_contribuicoes(por_mes):
    svg = [
        cartao(),
        texto(22, 34, "Contribuições nos últimos 12 meses", 14, AZUL, "bold"),
        texto(22, 54, f'Total: {sum(por_mes.values())} contribuições', 11, CINZA),
    ]

    if por_mes:
        maximo = max(por_mes.values()) or 1
        inicio_x, largura_area, base, altura_max = 24, 292, 168, 96
        passo = largura_area / len(por_mes)
        for indice, (chave, valor) in enumerate(por_mes.items()):
            altura = (valor / maximo) * altura_max
            x = inicio_x + indice * passo + 3
            y = base - altura
            svg.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{passo - 6:.1f}" '
                f'height="{altura:.1f}" rx="2" fill="{VERDE}" opacity="0.85"/>'
            )
            mes = MESES_PT[int(chave[5:7]) - 1]
            svg.append(texto(x + (passo - 6) / 2, 184, mes, 9, CINZA, None, "middle"))

    svg.append("</svg>")
    return "".join(svg)


# ---------------------------------------------------------------- main

def main():
    dados = coletar()
    os.makedirs(PASTA, exist_ok=True)
    cards = {
        "estatisticas.svg": card_estatisticas(dados),
        "linguagens.svg": card_linguagens(dados["linguagens"]),
        "contribuicoes.svg": card_contribuicoes(dados["por_mes"]),
    }
    for nome, conteudo in cards.items():
        caminho = os.path.join(PASTA, nome)
        with open(caminho, "w", encoding="utf-8") as arquivo:
            arquivo.write(conteudo)
        print(f"gerado: {caminho} ({len(conteudo)} bytes)")


if __name__ == "__main__":
    main()
