# -*- coding: utf-8 -*-
"""Gravação de tabelas e figuras."""
import os


def _garantir_pasta(caminho):
    pasta = os.path.dirname(caminho)
    if pasta:
        os.makedirs(pasta, exist_ok=True)


def salvar_dataframe(df, caminho):
    _garantir_pasta(caminho)
    if caminho.lower().endswith(".csv"):
        df.to_csv(caminho, index=False, sep=";", encoding="utf-8-sig", decimal=",")
    elif caminho.lower().endswith(".xlsx"):
        df.to_excel(caminho, index=False)
    else:
        raise ValueError("Use .csv ou .xlsx")
    print(f"Salvo: {caminho} ({len(df)} linhas)")


def salvar_figura(fig, caminho, dpi=150):
    _garantir_pasta(caminho)
    fig.savefig(caminho, dpi=dpi, bbox_inches="tight")
    print(f"Figura salva: {caminho}")