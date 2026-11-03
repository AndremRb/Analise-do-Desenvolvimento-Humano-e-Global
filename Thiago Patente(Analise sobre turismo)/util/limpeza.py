# -*- coding: utf-8 -*-
"""Duplicados, ausentes e cobertura."""
import pandas as pd


def resumo_duplicados(df, chaves):
    """Linhas que repetem a mesma chave (ex.: cod_ibge + ano)."""
    return df[df.duplicated(subset=chaves, keep=False)].sort_values(chaves)


def remover_duplicados(df, chaves, manter="first"):
    return df.drop_duplicates(subset=chaves, keep=manter).reset_index(drop=True)


def resumo_ausentes(df):
    qtd = df.isna().sum()
    res = pd.DataFrame({"ausentes": qtd, "percentual": (qtd / len(df) * 100).round(2)})
    return res[res["ausentes"] > 0]


def verificar_cobertura(df, col_ano="ano", esperado=27):
    """Quantas UFs existem por ano (deve ser 27)."""
    cont = df.groupby(col_ano)["cod_ibge"].nunique().rename("ufs").to_frame()
    cont["completo"] = cont["ufs"] == esperado
    return cont