# -*- coding: utf-8 -*-
"""Referência das UFs: sigla -> (nome, código IBGE)."""
from .texto import normalizar_texto

UFS = {
    "RO": ("Rondônia", 11), "AC": ("Acre", 12), "AM": ("Amazonas", 13),
    "RR": ("Roraima", 14), "PA": ("Pará", 15), "AP": ("Amapá", 16),
    "TO": ("Tocantins", 17), "MA": ("Maranhão", 21), "PI": ("Piauí", 22),
    "CE": ("Ceará", 23), "RN": ("Rio Grande do Norte", 24),
    "PB": ("Paraíba", 25), "PE": ("Pernambuco", 26), "AL": ("Alagoas", 27),
    "SE": ("Sergipe", 28), "BA": ("Bahia", 29), "MG": ("Minas Gerais", 31),
    "ES": ("Espírito Santo", 32), "RJ": ("Rio de Janeiro", 33),
    "SP": ("São Paulo", 35), "PR": ("Paraná", 41),
    "SC": ("Santa Catarina", 42), "RS": ("Rio Grande do Sul", 43),
    "MS": ("Mato Grosso do Sul", 50), "MT": ("Mato Grosso", 51),
    "GO": ("Goiás", 52), "DF": ("Distrito Federal", 53),
}

# texto normalizado (nome ou sigla) -> sigla
MAPA_UF = {}
for _s, (_n, _c) in UFS.items():
    MAPA_UF[normalizar_texto(_n)] = _s
    MAPA_UF[normalizar_texto(_s)] = _s

# código IBGE -> sigla
CODIGO_PARA_UF = {cod: sigla for sigla, (_, cod) in UFS.items()}


def eh_estado(valor) -> bool:
    """True se o valor for nome ou sigla de UF."""
    return normalizar_texto(valor) in MAPA_UF


def sigla_por_nome(valor):
    return MAPA_UF.get(normalizar_texto(valor))


def adicionar_dados_uf(df, col_sigla="uf"):
    """A partir da sigla, cria as colunas 'estado' e 'cod_ibge'."""
    df = df.copy()
    df["estado"] = df[col_sigla].map(lambda s: UFS[s][0])
    df["cod_ibge"] = df[col_sigla].map(lambda s: UFS[s][1])
    return df