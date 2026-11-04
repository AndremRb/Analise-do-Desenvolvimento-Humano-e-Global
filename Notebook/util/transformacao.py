# -*- coding: utf-8 -*-
"""Filtro, junção e cálculo de variações."""
import numpy as np


def filtrar_anos(df, anos, col="ano"):
    return df[df[col].isin(anos)].copy().reset_index(drop=True)


def juntar_por_uf_ano(esquerda, direita, como="inner"):
    """Une duas bases por cod_ibge + ano (uf/estado vêm só da esquerda)."""
    direita = direita.drop(columns=[c for c in ("uf", "estado") if c in direita])
    return esquerda.merge(direita, on=["cod_ibge", "ano"], how=como,
                          validate="one_to_one")


def _movimento(serie):
    return np.select([serie < 0, serie > 0], ["caiu", "subiu"], "estável")


def variacao_entre_anos(df, ano_ini, ano_fim,
                        col_taxa="taxa_homicidios", col_viagens="viagens_mil"):
    """Por UF: variação da taxa (pontos) e das viagens (%) entre dois anos."""
    a = df[df["ano"] == ano_ini].set_index("cod_ibge")
    b = df[df["ano"] == ano_fim].set_index("cod_ibge")
    out = b[["uf", "estado"]].copy()
    out["taxa_ini"], out["taxa_fim"] = a[col_taxa], b[col_taxa]
    out["viagens_ini"], out["viagens_fim"] = a[col_viagens], b[col_viagens]
    out["delta_taxa"] = (out["taxa_fim"] - out["taxa_ini"]).round(2)
    out["var_viagens_pct"] = ((out["viagens_fim"] / out["viagens_ini"] - 1) * 100).round(2)
    out["taxa_mov"] = _movimento(out["delta_taxa"])
    out["viagens_mov"] = _movimento(out["var_viagens_pct"])
    return out.reset_index()


def indice_base(df, col_valor, ano_base, col_ano="ano", col_uf="uf"):
    """Índice por UF (ano_base = 100)."""
    piv = df.pivot(index=col_ano, columns=col_uf, values=col_valor)
    return piv / piv.loc[ano_base] * 100