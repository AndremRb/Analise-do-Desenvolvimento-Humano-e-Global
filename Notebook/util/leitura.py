# -*- coding: utf-8 -*-
"""Leitura genérica de tabelas SIDRA (IBGE) e de CSVs."""
import pandas as pd
import re
import unicodedata
import numpy as np



from .texto import normalizar_texto, extrair_ano, converter_valor
from .ufs import eh_estado, sigla_por_nome, adicionar_dados_uf, CODIGO_PARA_UF

_ANO_RE = re.compile(r"^\s*(20[0-3]\d)(?:\.0)?\s*\*?\s*$")

def ler_csv_flexivel(caminho, encodings=("utf-8-sig", "latin-1")):
    """Lê CSV detectando o separador (; ou ,) e testando encodings."""
    for enc in encodings:
        try:
            return pd.read_csv(caminho, sep=None, engine="python", encoding=enc)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Não foi possível ler {caminho}")


def encontrar_coluna(df, *palavras):
    """Primeira coluna cujo nome contém TODAS as palavras (sem acento/caixa)."""
    for col in df.columns:
        nome = normalizar_texto(col)
        if all(normalizar_texto(p) in nome for p in palavras):
            return col
    raise KeyError(f"Coluna com {palavras} não encontrada: {list(df.columns)}")


def ler_tabela_sidra_horizontal(caminho_excel, aba=0, nome_valor="valor"):
    """
    Lê tabelas do SIDRA no formato:
        linha de ANOS (células mescladas: 2019 ... 2020 ...)
        linha de UFs  (Rondônia, Acre, ... repetidas por ano)
        linha de VALORES
    Devolve formato longo: cod_ibge | uf | estado | ano | <nome_valor>
    """
    bruto = pd.read_excel(caminho_excel, sheet_name=aba, header=None, dtype=object)

    # 1) Linha das UFs = a linha com mais nomes de estado
    qtd_uf = bruto.apply(lambda linha: linha.map(eh_estado).sum(), axis=1)
    lin_uf = qtd_uf.idxmax()

    # 2) Linha dos anos = a mais próxima ACIMA da linha das UFs que tenha ano
    lin_ano = next(i for i in range(lin_uf - 1, -1, -1)
                   if bruto.loc[i].map(extrair_ano).notna().any())
    # células mescladas vêm vazias -> propaga o ano para a direita
    anos = bruto.loc[lin_ano].map(extrair_ano).ffill()

    # 3) Colunas que são UFs e linha dos valores (primeira linha numérica abaixo)
    colunas_uf = [c for c in bruto.columns if eh_estado(bruto.at[lin_uf, c])]
    lin_val = next(i for i in range(lin_uf + 1, len(bruto))
                   if bruto.loc[i, colunas_uf].map(converter_valor).notna().sum()
                   >= len(colunas_uf) // 2)

    # 4) Monta o formato longo
    df = pd.DataFrame({
        "ano": [int(anos[c]) for c in colunas_uf],
        "uf": [sigla_por_nome(bruto.at[lin_uf, c]) for c in colunas_uf],
        nome_valor: [converter_valor(bruto.at[lin_val, c]) for c in colunas_uf],
    })
    df = adicionar_dados_uf(df)
    return df[["cod_ibge", "uf", "estado", "ano", nome_valor]]


def padronizar_serie_por_codigo(df, nome_valor, col_codigo=None,
                                col_periodo=None, col_valor=None):
    """
    Padroniza séries no formato 'código | período | valor' (ex.: IPEA/Atlas).
    Detecta as colunas automaticamente; informe-as se a detecção falhar.
    """
    col_codigo = col_codigo or encontrar_coluna(df, "id")
    col_periodo = col_periodo or encontrar_coluna(df, "period")
    col_valor = col_valor or encontrar_coluna(df, "valor")

    out = pd.DataFrame({
        "cod_ibge": pd.to_numeric(df[col_codigo], errors="coerce"),
        "ano": df[col_periodo].map(extrair_ano),
        nome_valor: df[col_valor].map(converter_valor),
    })
    out = out[out["cod_ibge"].isin(CODIGO_PARA_UF)].copy()   # só as 27 UFs
    out["cod_ibge"] = out["cod_ibge"].astype(int)
    out["ano"] = out["ano"].astype(int)
    out["uf"] = out["cod_ibge"].map(CODIGO_PARA_UF)
    out = adicionar_dados_uf(out)
    return out[["cod_ibge", "uf", "estado", "ano", nome_valor]].reset_index(drop=True)


def normalizarP(txt):
    txt = unicodedata.normalize("NFKD", str(txt)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-zA-Z0-9]+", "_", txt).strip("_").lower()

def ler_brent(caminho):
    """CSV no formato Investing.com: devolve data e fechamento."""
    df = pd.read_csv(caminho, sep=None, engine="python",
                     encoding="utf-8-sig", dtype=str)
    df.columns = [normalizarP(c) for c in df.columns]
    df = df.rename(columns={"ultimo": "fechamento"})
    df["data"] = pd.to_datetime(df["data"], dayfirst=True)
    txt = df["fechamento"].str.strip()
    if txt.str.contains(",").any():
        txt = txt.str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    df["fechamento"] = pd.to_numeric(txt, errors="raise")
    return df[["data", "fechamento"]].sort_values("data").reset_index(drop=True)


def brent_anual(brent):
    """Resumo anual. 'parcial' = não começa até 15/jan ou não termina após 15/dez."""
    d = brent.assign(ano=brent["data"].dt.year)
    g = d.groupby("ano")
    r = g["fechamento"].agg(brent_media="mean", brent_min="min",
                            brent_max="max", dias="count")
    r["primeira_data"] = g["data"].min()
    r["ultima_data"] = g["data"].max()
    r["parcial"] = ((r["primeira_data"].dt.month > 1)
                    | (r["primeira_data"].dt.day > 15)
                    | (r["ultima_data"].dt.month < 12)
                    | (r["ultima_data"].dt.day < 15))
    return r.reset_index()



def _localizar_anos(bruto):
    """Maior bloco contíguo de anos (>= 3, sem repetição) em uma única coluna."""
    melhor = None
    for j in range(bruto.shape[1]):
        anos = [_ano_da_celula(v) for v in bruto.iloc[:, j]]
        i = 0
        while i < len(anos):
            if anos[i] is None:
                i += 1
                continue
            k = i
            while k < len(anos) and anos[k] is not None:
                k += 1
            bloco = anos[i:k]
            if len(bloco) >= 3 and len(set(bloco)) == len(bloco):
                if melhor is None or len(bloco) > len(melhor[1]):
                    melhor = (j, list(range(i, k)))
            i = k
    return melhor

def _linha_cabecalho(bruto, j, primeira):
    """Linha mais próxima acima do bloco com >= 2 células fora da coluna do ano."""
    for i in range(primeira - 1, -1, -1):
        outras = bruto.iloc[i].drop(bruto.columns[j]).notna().sum()
        if outras >= 2:
            return i
    return None


def ler_tabela_anual(caminho, aba):
    """Lê uma aba com anos em linhas ou em colunas e devolve 'ano' + séries."""
    bruto = pd.read_excel(caminho, sheet_name=aba, header=None)
    bruto = bruto.dropna(how="all").dropna(axis=1, how="all").reset_index(drop=True)
    bruto.columns = range(bruto.shape[1])

    achou = _localizar_anos(bruto)
    orientacao = "anos nas linhas"
    if achou is None:
        bruto = bruto.T.reset_index(drop=True)
        bruto.columns = range(bruto.shape[1])
        achou = _localizar_anos(bruto)
        orientacao = "anos nas colunas (tabela transposta)"
    if achou is None:
        print(bruto.head(15))
        raise ValueError(f"Não achei anos na aba '{aba}'. Confira o layout acima.")

    j, idx = achou
    cab = _linha_cabecalho(bruto, j, idx[0])

    nomes, usados = [], {}
    for k in range(bruto.shape[1]):
        if k == j:
            nome = "ano"
        elif cab is not None and pd.notna(bruto.iloc[cab, k]):
            nome = normalizarP(bruto.iloc[cab, k])
        else:
            nome = f"col_{k}"
        usados[nome] = usados.get(nome, 0) + 1
        nomes.append(nome if usados[nome] == 1 else f"{nome}_{usados[nome]}")

    df = bruto.loc[idx].copy()
    df.columns = nomes
    df["ano"] = df["ano"].map(_ano_da_celula).astype(int)
    for c in df.columns.drop("ano"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(axis=1, how="all").reset_index(drop=True)
    print(f"Aba '{aba}': {orientacao}; anos {df['ano'].min()}–{df['ano'].max()}; "
          f"cabeçalho na linha {cab}; colunas: {list(df.columns.drop('ano'))}")
    return df


# --------------------------------------------------------------- Rodoviário
def _ler_rod_bruto(caminho, aba=0):
    bruto = pd.read_excel(caminho, sheet_name=aba, header=None)
    linha = next(i for i in range(len(bruto))
                 if bruto.iloc[i].astype(str).str.contains("Unidade", case=False).any())
    df = bruto.iloc[linha + 1:].copy()
    df.columns = ["regiao", "uf"] + [int(float(a)) for a in bruto.iloc[linha, 2:]]
    df["regiao"] = df["regiao"].ffill()
    return df


def numerico(s):
    return pd.to_numeric(s.astype(str).str.replace(",", "", regex=False),
                         errors="coerce")


def ler_rodoviario(caminho, aba=0):
    """Formato longo: regiao, uf, ano, passageiros (sem a linha de total)."""
    df = _ler_rod_bruto(caminho, aba)
    df = df[df["uf"].notna()]
    longo = df.melt(id_vars=["regiao", "uf"], var_name="ano", value_name="passageiros")
    longo["ano"] = longo["ano"].astype(int)
    longo["passageiros"] = numerico(longo["passageiros"])
    longo["uf"] = longo["uf"].astype(str).str.strip().str.upper()
    return longo.reset_index(drop=True)


def total_oficial_rodoviario(caminho, aba=0):
    """Linha 'Total Origem' da planilha, para conferir com a soma das UFs."""
    df = _ler_rod_bruto(caminho, aba)
    lin = df[df["regiao"].astype(str).str.contains("Total", case=False)].iloc[0]
    return numerico(lin.drop(["regiao", "uf"])).rename("total_oficial")


def quedas_bruscas(rodov, limite_pct=-60):
    """Quedas anuais por UF iguais ou piores que o limite (sinal de quebra de cobertura)."""
    d = rodov.sort_values(["uf", "ano"]).copy()
    d["var_pct"] = (d.groupby("uf")["passageiros"].pct_change()
                    .replace([np.inf, -np.inf], np.nan) * 100)
    return d[d["var_pct"] <= limite_pct].round(1)


def ranking_ufs(rodov, ano_ini, ano_fim):
    """Variação absoluta e percentual por UF entre dois anos."""
    p = rodov.pivot(index="uf", columns="ano", values="passageiros")
    r = pd.DataFrame({"inicio": p[ano_ini], "fim": p[ano_fim]})
    r["var_abs"] = r["fim"] - r["inicio"]
    r["var_pct"] = (r["var_abs"] / r["inicio"].replace(0, np.nan) * 100).round(1)
    return r.sort_values("var_abs").reset_index()



def _ano_da_celula(v):
    """Devolve o ano (int) se a célula for um ano; senão None. Nunca gera erro."""
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return None
    m = _ANO_RE.match(str(v))
    return int(m.group(1)) if m else None



def achar_aba(caminho, nome):
    """Acha a aba pelo número da figura. 'Fig 2.1' não casa com 'Fig 2.10' nem 'Fig 2.21'."""
    abas = pd.ExcelFile(caminho).sheet_names

    # 1) nome exato (ignorando maiúsculas e espaços nas pontas)
    for a in abas:
        if str(a).strip().lower() == str(nome).strip().lower():
            return a

    # 2) mesmo número, com separador obrigatório entre os dígitos
    numeros = re.findall(r"\d+", str(nome))
    if not numeros:
        raise ValueError(f"'{nome}' não contém número de figura.")
    padrao = r"(?<!\d)" + r"[\s._\-]+".join(numeros) + r"(?!\d)"
    achadas = [a for a in abas if re.search(padrao, str(a))]
    if len(achadas) == 1:
        return achadas[0]
    raise ValueError(f"Aba '{nome}' não encontrada de forma única. "
                     f"Candidatas: {achadas}. Abas disponíveis: {abas}")


def achar_coluna(df, *trechos):
    """Coluna cujo nome contém todos os trechos; erro lista as opções."""
    alvo = [normalizarP(x) for x in trechos]
    achadas = [c for c in df.columns if all(a in c for a in alvo)]
    if len(achadas) != 1:
        raise ValueError(f"Esperava 1 coluna com {trechos}; achei {achadas}. "
                         f"Colunas: {list(df.columns)}")
    return achadas[0]

def _para_numero(serie):
    """Converte para número, aceitando vírgula decimal se a célula vier como texto."""
    if pd.api.types.is_numeric_dtype(serie):
        return serie.astype(float)
    txt = serie.astype(str).str.strip()
    com_virgula = txt.str.contains(",", regex=False)
    txt = txt.where(~com_virgula,
                    txt.str.replace(".", "", regex=False).str.replace(",", ".", regex=False))
    return pd.to_numeric(txt, errors="coerce")


def ler_aba_longa(caminho, aba):
    """Lê uma aba com título na 1.ª linha e cabeçalho que começa com 'ano'."""
    bruto = pd.read_excel(caminho, sheet_name=aba, header=None)
    bruto = bruto.dropna(how="all").dropna(axis=1, how="all").reset_index(drop=True)
    linha = next((i for i in range(len(bruto))
                  if normalizarP(bruto.iat[i, 0]) == "ano"), None)
    if linha is None:
        print(bruto.head(10))
        raise ValueError(f"Aba '{aba}': não achei o cabeçalho que começa com 'ano'.")
    df = bruto.iloc[linha + 1:].copy()
    df.columns = [normalizarP(c) for c in bruto.iloc[linha]]
    df = df.dropna(how="all")
    df["ano"] = df["ano"].map(_ano_da_celula)
    df = df.dropna(subset=["ano"])
    df["ano"] = df["ano"].astype(int)
    return df.reset_index(drop=True)


def ler_voos(caminho, aba):
    """Fig 2.1: ano, natureza, decolagens -> ano, voos_dom, voos_int."""
    df = ler_aba_longa(caminho, aba)
    df["decolagens"] = _para_numero(df["decolagens"])
    df["tipo"] = np.where(df["natureza"].map(normalizarP).str.startswith("dom"),
                          "voos_dom", "voos_int")
    out = df.pivot(index="ano", columns="tipo", values="decolagens")
    out.columns.name = None
    print(f"Aba '{aba}': anos {out.index.min()}–{out.index.max()}; "
          f"colunas: {list(out.columns)}")
    return out.reset_index()


def ler_tarifa(caminho, aba):
    """Fig 6.1: ano, indicador -> ano, tarifa_real."""
    df = ler_aba_longa(caminho, aba)
    df["tarifa_real"] = _para_numero(df["indicador"])
    print(f"Aba '{aba}': anos {df['ano'].min()}–{df['ano'].max()}")
    return df[["ano", "tarifa_real"]]


def ler_custos(caminho, aba):
    """Fig 7.8: ano, empresa, valor -> ano e uma coluna por empresa."""
    df = ler_aba_longa(caminho, aba)
    df["valor"] = _para_numero(df["valor"])
    df["empresa"] = df["empresa"].map(normalizarP)
    out = df.pivot(index="ano", columns="empresa", values="valor")
    out.columns.name = None
    print(f"Aba '{aba}': anos {out.index.min()}–{out.index.max()}; "
          f"empresas: {list(out.columns)}")
    return out.reset_index()