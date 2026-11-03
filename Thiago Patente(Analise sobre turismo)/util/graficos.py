# -*- coding: utf-8 -*-
"""Gráficos reutilizáveis (matplotlib)."""
import matplotlib.pyplot as plt

import math

import numpy as np


def grafico_dispersao(var, titulo, destacar=()):
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.scatter(var["delta_taxa"], var["var_viagens_pct"], color="tab:blue")
    for _, l in var.iterrows():
        ax.annotate(l["uf"], (l["delta_taxa"], l["var_viagens_pct"]),
                    xytext=(3, 3), textcoords="offset points", fontsize=8,
                    color="red" if l["uf"] in destacar else "black")
    ax.axhline(0, color="gray", lw=0.8)
    ax.axvline(0, color="gray", lw=0.8)
    ax.set_xlabel("Variação da taxa de homicídios (por 100 mil hab.)")
    ax.set_ylabel("Variação das viagens recebidas (%)")
    ax.set_title(titulo)
    fig.tight_layout()
    return fig


def grafico_total_por_ano(df, col_valor, destaque=(), titulo="", rotulo_y=""):
    tot = df.groupby("ano")[col_valor].sum()
    cores = ["tab:red" if a in destaque else "tab:blue" for a in tot.index]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(tot.index.astype(str), tot.values, color=cores)
    ax.set_title(titulo)
    ax.set_ylabel(rotulo_y)
    fig.tight_layout()
    return fig


def grafico_indice_ufs(indice, titulo):
    """Linhas cinza = UFs; linha preta = mediana."""
    fig, ax = plt.subplots(figsize=(9, 5))
    x = indice.index.astype(str)
    for uf in indice.columns:
        ax.plot(x, indice[uf], color="lightgray", lw=1)
    ax.plot(x, indice.median(axis=1), color="black", lw=2.5, label="Mediana das UFs")
    ax.axhline(100, color="tab:blue", ls="--", lw=1)
    ax.set_title(titulo)
    ax.set_ylabel("Índice (ano-base = 100)")
    ax.legend()
    fig.tight_layout()
    return fig



def grafico_dispersao_indicador(var, prefixo, titulo, rotulo_x, destacar=(),
                                rotulo_y="Variação das viagens recebidas (%)"):
    """Dispersão das variações por UF, com reta de tendência e UFs destacadas."""
    x, y = f"{prefixo}_var_pct", "viagens_var_pct"
    fig, ax = plt.subplots(figsize=(10, 7))

    normais = var.loc[~var["uf"].isin(destacar)]
    especiais = var.loc[var["uf"].isin(destacar)]
    ax.scatter(normais[x], normais[y], s=50, label="UFs")
    if len(especiais):
        ax.scatter(especiais[x], especiais[y], s=80, color="orange",
                   label="Destacadas: " + ", ".join(destacar))

    if var[x].nunique() > 1:
        a, b = np.polyfit(var[x], var[y], 1)
        xs = np.linspace(var[x].min(), var[x].max(), 100)
        ax.plot(xs, a * xs + b, color="red", lw=1.2,
                label="Tendência linear (todas as UFs)")

    for _, linha in var.iterrows():
        ax.annotate(linha["uf"], (linha[x], linha[y]), xytext=(4, 4),
                    textcoords="offset points", fontsize=9)

    ax.axhline(0, color="gray", lw=0.8, ls="--")
    ax.axvline(0, color="gray", lw=0.8, ls="--")
    ax.set(title=titulo, xlabel=rotulo_x, ylabel=rotulo_y)
    ax.legend()
    fig.tight_layout()
    return fig


def grafico_indices_duplos(base, col_indicador, nome_indicador, ano_base=2019,
                           col_viagens="viagens_mil", titulo=None, ncols=6):
    """Um painel por UF com indicador e viagens em índice (ano_base = 100)."""
    dados = base.sort_values(["uf", "ano"]).copy()
    ref = dados.loc[dados["ano"].eq(ano_base)].set_index("uf")
    dados["idx_ind"] = dados[col_indicador] / dados["uf"].map(ref[col_indicador]) * 100
    dados["idx_via"] = dados[col_viagens] / dados["uf"].map(ref[col_viagens]) * 100

    anos = sorted(dados["ano"].unique())
    ufs = sorted(dados["uf"].unique())
    nrows = math.ceil(len(ufs) / ncols)

    fig, eixos = plt.subplots(nrows, ncols, figsize=(18, 3 * nrows),
                              sharex=True, sharey=True)
    for ax, uf in zip(eixos.flat, ufs):
        d = dados.loc[dados["uf"].eq(uf)]
        ax.plot(d["ano"], d["idx_ind"], marker="o", label=nome_indicador)
        ax.plot(d["ano"], d["idx_via"], marker="s", label="Viagens recebidas")
        ax.axhline(100, color="gray", lw=0.7, ls="--")
        ax.set_title(uf)
        ax.set_xticks(anos)
        ax.tick_params(axis="x", rotation=45)
    for ax in eixos.flat[len(ufs):]:
        ax.axis("off")

    handles, labels = eixos.flat[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper right", ncol=2)
    fig.suptitle(titulo or f"Índices ({ano_base} = 100)")
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    return fig



def grafico_brent_anual(brent_ano, titulo, rotulo_y="US$ por barril"):
    fig, ax = plt.subplots(figsize=(10, 5))
    cores = ["tab:gray" if p else "tab:blue" for p in brent_ano["parcial"]]
    barras = ax.bar(brent_ano["ano"], brent_ano["brent_media"], color=cores)
    for b, d in zip(barras, brent_ano["dias"]):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height(), f"{d} d",
                ha="center", va="bottom", fontsize=8)
    ax.set_xticks(brent_ano["ano"])
    ax.set_title(titulo + "\n(cinza = ano parcial; d = dias de dados)")
    ax.set_ylabel(rotulo_y)
    fig.tight_layout()
    return fig


def grafico_indices_brent(base, colunas, ano_base, titulo):
    """colunas = {coluna: rótulo}. Todas as séries em índice (ano_base = 100)."""
    d = base.sort_values("ano")
    fig, ax = plt.subplots(figsize=(10, 5))
    for col, rotulo in {"brent_media": "Brent (média anual)", **colunas}.items():
        ref = d.loc[d["ano"] == ano_base, col].iloc[0]
        ax.plot(d["ano"], d[col] / ref * 100, marker="o",
                lw=3 if col == "brent_media" else 1.8,
                color="black" if col == "brent_media" else None, label=rotulo)
    ax.axhline(100, color="gray", ls=":")
    ax.set_xticks(d["ano"])
    ax.set_title(titulo)
    ax.set_ylabel(f"Índice ({ano_base} = 100)")
    ax.legend(fontsize=8)
    fig.tight_layout()
    return fig


def grafico_dispersao_anos(var, x, y, titulo, rotulo_x, rotulo_y):
    d = var.dropna(subset=[x, y])
    fig, ax = plt.subplots(figsize=(7, 5.5))
    ax.scatter(d[x], d[y], s=60)
    for _, r in d.iterrows():
        ax.annotate(int(r["ano"]), (r[x], r[y]), textcoords="offset points",
                    xytext=(5, 5))
    if len(d) >= 3 and d[x].nunique() > 1:
        a, b = np.polyfit(d[x], d[y], 1)
        xs = np.linspace(d[x].min(), d[x].max(), 50)
        ax.plot(xs, a * xs + b, ls="--", color="gray")
    ax.axhline(0, color="gray", lw=0.8)
    ax.axvline(0, color="gray", lw=0.8)
    ax.set_title(titulo)
    ax.set_xlabel(rotulo_x)
    ax.set_ylabel(rotulo_y)
    fig.tight_layout()
    return fig


def grafico_barras_uf(rank, coluna, titulo, rotulo_x):
    d = rank.sort_values(coluna)
    fig, ax = plt.subplots(figsize=(8, 8))
    ax.barh(d["uf"], d[coluna],
            color=["tab:red" if v < 0 else "tab:blue" for v in d[coluna]])
    ax.set_title(titulo)
    ax.set_xlabel(rotulo_x)
    fig.tight_layout()
    return fig