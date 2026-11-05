# -*- coding: utf-8 -*-
"""Correlação, robustez e classificação do resultado."""
import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr, t
from scipy import stats




def tabela_contingencia(var):
    """Cruza o movimento da taxa com o movimento das viagens."""
    return pd.crosstab(var["taxa_mov"], var["viagens_mov"], margins=True, margins_name="Total")


def correlacao(var, excluir=()):
    d = var[~var["uf"].isin(excluir)]
    x, y = d["delta_taxa"], d["var_viagens_pct"]
    return {
        "n": len(d),
        "pearson": round(x.corr(y), 3),
        "spearman": round(x.corr(y, method="spearman"), 3),
        # quanto variam as viagens (%) para +1 homicídio/100 mil
        "inclinacao_pct": round(np.polyfit(x, y, 1)[0], 3),
        "r_critico_5pct": round(1.96 / np.sqrt(len(d) - 1 + 1.96 ** 2) ** 1, 3),
    }


def teste_robustez(var, cenarios: dict):
    """cenarios = {'nome': [siglas a excluir]}"""
    return pd.DataFrame([{"cenario": nome, **correlacao(var, exc)}
                         for nome, exc in cenarios.items()])


def classificar_resultado(robustez, col="pearson"):
    """
    INDETERMINADO se nenhuma correlação for significativa
    OU se o sinal mudar entre os cenários.
    """
    r, crit = robustez[col], robustez["r_critico_5pct"]
    muda_sinal = (r > 0).any() and (r < 0).any()
    nenhuma_sig = (r.abs() < crit).all()
    if muda_sinal or nenhuma_sig:
        return "INDETERMINADO"
    return "NEGATIVA (compatível com a hipótese)" if (r < 0).all() else "POSITIVA (contrária)"



CHAVES = ["cod_ibge", "ano"]


def juntar_indicador(viagens, indicador, col_indicador, chaves=CHAVES):
    """Junta viagens e indicador por código IBGE e ano e confere as siglas."""
    colunas = chaves + [col_indicador]
    if "uf" in indicador.columns:
        colunas.append("uf")

    base = viagens.merge(
        indicador[colunas],
        on=chaves,
        how="inner",
        suffixes=("", "_indicador"),
        validate="one_to_one",
    )

    if "uf_indicador" in base.columns:
        divergentes = base.loc[
            base["uf"] != base["uf_indicador"],
            ["cod_ibge", "uf", "uf_indicador"],
        ].drop_duplicates()
        if len(divergentes):
            raise ValueError(f"Siglas divergentes para o mesmo código:\n{divergentes}")
        base = base.drop(columns="uf_indicador")

    return base.sort_values(["ano", "cod_ibge"]).reset_index(drop=True)


def _movimento(variacao):
    if variacao.isna().any():
        raise ValueError("Há variações ausentes; confira os dados de origem.")
    return pd.Series(
        np.select([variacao > 0, variacao < 0], ["subiu", "caiu"], default="estável"),
        index=variacao.index,
    )


def variacao_indicador(base, ano_ini, ano_fim, col_indicador, prefixo,
                       col_viagens="viagens_mil"):
    """Variação % do indicador e das viagens entre dois anos, por UF."""
    ini = base.loc[base["ano"].eq(ano_ini)].set_index("cod_ibge")
    fim = base.loc[base["ano"].eq(ano_fim)].set_index("cod_ibge")

    if ini.empty or fim.empty:
        raise ValueError(f"Ano ausente na base: {ano_ini} ou {ano_fim}.")
    if set(ini.index) != set(fim.index):
        raise ValueError("As UFs dos dois anos não coincidem.")
    fim = fim.loc[ini.index]

    var = pd.DataFrame({"uf": ini["uf"], "estado": ini["estado"]})
    var[f"{prefixo}_inicio"] = ini[col_indicador]
    var[f"{prefixo}_fim"] = fim[col_indicador]
    var[f"{prefixo}_var_pct"] = (fim[col_indicador] / ini[col_indicador] - 1) * 100
    var["viagens_inicio"] = ini[col_viagens]
    var["viagens_fim"] = fim[col_viagens]
    var["viagens_var_pct"] = (fim[col_viagens] / ini[col_viagens] - 1) * 100

    var[f"{prefixo}_mov"] = _movimento(var[f"{prefixo}_var_pct"])
    var["viagens_mov"] = _movimento(var["viagens_var_pct"])
    return var.reset_index()


def tabela_contingencia_indicador(var, prefixo):
    """Cruza o sentido da mudança do indicador com o das viagens."""
    return pd.crosstab(
        var[f"{prefixo}_mov"],
        var["viagens_mov"],
        margins=True,
        margins_name="Total",
    )


def r_critico(n, alfa=0.05):
    """|r| mínimo de Pearson para significância bilateral com n observações."""
    t = stats.t.ppf(1 - alfa / 2, n - 2)
    return t / np.sqrt(t**2 + n - 2)


def teste_robustez_indicador(var, prefixo, cenarios, alfa=0.05):
    """Pearson e Spearman (com valor-p) em cada cenário de sensibilidade."""
    x, y = f"{prefixo}_var_pct", "viagens_var_pct"
    linhas = []

    for nome, excluir in cenarios.items():
        d = var.loc[~var["uf"].isin(excluir), [x, y]].dropna()
        n = len(d)
        if n < 4 or d[x].nunique() < 2 or d[y].nunique() < 2:
            raise ValueError(f"Cenário '{nome}': dados insuficientes.")

        r_p, p_p = stats.pearsonr(d[x], d[y])
        r_s, p_s = stats.spearmanr(d[x], d[y])

        linhas.append({
            "cenario": nome,
            "n": n,
            "pearson": float(r_p),
            "p_pearson": float(p_p),
            "spearman": float(r_s),
            "p_spearman": float(p_s),
            "inclinacao": float(np.polyfit(d[x], d[y], 1)[0]),
            "r_critico_5pct": float(r_critico(n, alfa)),
            "significativo_5pct": bool(p_p < alfa),
        })

    return pd.DataFrame(linhas).round(3)


def resumo_choque_indicador(var, prefixo, nome_indicador):
    """Conta quedas do indicador, das viagens e quedas simultâneas."""
    caiu_ind = var[f"{prefixo}_mov"].eq("caiu")
    caiu_via = var["viagens_mov"].eq("caiu")
    return pd.Series({
        "UFs analisadas": len(var),
        f"{nome_indicador} caiu": int(caiu_ind.sum()),
        "Viagens caíram": int(caiu_via.sum()),
        "Ambos caíram": int((caiu_ind & caiu_via).sum()),
        "UFs com ambas as quedas": var.loc[caiu_ind & caiu_via, "uf"].tolist(),
    })



def juntar_series_anuais(brent_ano, outra, colunas, incluir_parciais=True):
    """Junta por ano (anos em comum) e mantém a marca de ano parcial do Brent."""
    b = brent_ano if incluir_parciais else brent_ano[~brent_ano["parcial"]]
    base = b[["ano", "brent_media", "dias", "parcial"]].merge(
        outra[["ano"] + colunas], on="ano", how="inner")
    return base.sort_values("ano").reset_index(drop=True)


def variacoes_anuais(base, colunas):
    """Variação % sobre o ano imediatamente anterior (só se o ano for consecutivo)."""
    d = base.sort_values("ano").copy()
    consecutivo = d["ano"].diff() == 1
    for c in colunas:
        d[f"{c}_var_pct"] = (d[c].pct_change() * 100).where(consecutivo)
    return d


def tabela_contingencia_sinais(var, x, y, rotulos=("caiu", "subiu")):
    """Cruza o sentido da variação de x (linhas) com o de y (colunas)."""
    d = var.dropna(subset=[x, y]).copy()
    mov = lambda s: np.where(s > 0, rotulos[1], rotulos[0])
    return pd.crosstab(pd.Series(mov(d[x]), name="brent_mov"),
                       pd.Series(mov(d[y]), name="y_mov"),
                       margins=True, margins_name="Total")


def r_critico_2(n, alfa=0.05):
    if n < 3:
        return np.nan
    tc = t.ppf(1 - alfa / 2, n - 2)
    return tc / np.sqrt(tc**2 + n - 2)


def correlacao_temporal(df, x, y):
    d = df[[x, y]].dropna()
    n = len(d)
    vazio = {"n": n, "pearson": np.nan, "p_pearson": np.nan,
             "spearman": np.nan, "p_spearman": np.nan,
             "r_critico_5pct": round(r_critico_2(n), 3) if n >= 3 else np.nan}
    if n < 3 or d[x].nunique() < 2 or d[y].nunique() < 2:
        return vazio
    rp, pp = pearsonr(d[x], d[y])
    rs, ps = spearmanr(d[x], d[y])
    return {"n": n, "pearson": round(rp, 3), "p_pearson": round(pp, 3),
            "spearman": round(rs, 3), "p_spearman": round(ps, 3),
            "r_critico_5pct": round(r_critico_2(n), 3)}


def teste_robustez_series(base, x, ys, cenarios):
    """cenarios = {nome: {'excluir': [anos], 'defasagem': k}}; x é defasado k anos."""
    linhas = []
    for y in ys:
        for nome, cfg in cenarios.items():
            d = base.sort_values("ano").copy()
            k = cfg.get("defasagem", 0)
            d["_x"] = (d["ano"] - k).map(d.set_index("ano")[x])
            d = d[~d["ano"].isin(cfg.get("excluir", []))][["ano", "_x", y]].dropna()
            res = correlacao_temporal(d, "_x", y)
            res["inclinacao"] = (round(np.polyfit(d["_x"], d[y], 1)[0], 3)
                                 if len(d) >= 3 and d["_x"].nunique() > 1 else np.nan)
            linhas.append({"variavel": y, "cenario": nome,
                           "anos": ", ".join(map(str, d["ano"])), **res})
    out = pd.DataFrame(linhas)
    out["significativo_5pct"] = out["p_pearson"] < 0.05
    return out