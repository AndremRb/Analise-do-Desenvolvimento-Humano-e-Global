
from pathlib import Path

import pandas as pd

_MARCAS_BOM = ("\ufeff", "ï»¿")


def detectar_encoding(caminho):
    """Retorna 'utf-8-sig' se o arquivo for UTF-8; caso contrário, 'latin-1'."""
    dados = Path(caminho).read_bytes()
    try:
        dados.decode("utf-8-sig")
        return "utf-8-sig"
    except UnicodeDecodeError:
        return "latin-1"


def _limpar(texto):
    """Remove marcas de BOM e espaços extras."""
    texto = str(texto)
    for marca in _MARCAS_BOM:
        texto = texto.replace(marca, "")
    return texto.strip()


def ler_titulo_ipeadata(caminho):
    """Lê a primeira linha do arquivo (título ou cabeçalho do Ipeadata)."""
    with open(caminho, encoding=detectar_encoding(caminho)) as arquivo:
        return _limpar(arquivo.readline()).rstrip(";").strip()


def identificar_arquivo_ipeadata(caminho):
    """Classifica o arquivo a partir do título da primeira linha."""
    titulo = ler_titulo_ipeadata(caminho).lower()
    if "pib" in titulo and "per capita" in titulo:
        return "pib_per_capita"
    if "infla" in titulo or "ipca" in titulo or "ipc" in titulo:
        return "inflacao"
    return "desconhecido"


def ler_ipeadata_por_uf(caminho, nome_valor, linhas_titulo=1):
    """
    Lê uma série estadual do Ipeadata (Sigla; Código; Estado; anos...)
    e converte para o formato longo: uf, cod_ibge, estado, ano, valor.
    """
    bruto = pd.read_csv(
        caminho,
        sep=";",
        decimal=",",
        skiprows=linhas_titulo,
        encoding=detectar_encoding(caminho),
    )
    bruto.columns = [_limpar(c) for c in bruto.columns]
    # O ';' no fim de cada linha gera uma coluna vazia "Unnamed".
    bruto = bruto.loc[:, ~bruto.columns.str.startswith("Unnamed")]

    bruto = bruto.rename(columns={
        bruto.columns[0]: "uf",
        bruto.columns[1]: "cod_ibge",
        bruto.columns[2]: "estado",
    })
    anos = [c for c in bruto.columns if c.isdigit()]

    longo = bruto.melt(
        id_vars=["uf", "cod_ibge", "estado"],
        value_vars=anos,
        var_name="ano",
        value_name=nome_valor,
    )
    longo["uf"] = longo["uf"].astype(str).str.strip()
    longo["estado"] = longo["estado"].astype(str).str.strip()
    longo["cod_ibge"] = pd.to_numeric(longo["cod_ibge"], errors="raise").astype(int)
    longo["ano"] = pd.to_numeric(longo["ano"], errors="raise").astype(int)
    longo[nome_valor] = pd.to_numeric(longo[nome_valor], errors="coerce")
    return longo


def ler_ipeadata_serie_anual(caminho, nome_valor):
    """Lê uma série nacional anual do Ipeadata (Data; valor)."""
    serie = pd.read_csv(
        caminho,
        sep=";",
        decimal=",",
        encoding=detectar_encoding(caminho),
    )
    serie = serie.iloc[:, :2].copy()
    serie.columns = ["ano", nome_valor]
    serie["ano"] = pd.to_numeric(serie["ano"], errors="coerce")
    serie[nome_valor] = pd.to_numeric(serie[nome_valor], errors="coerce")
    serie = serie.dropna(subset=["ano"]).astype({"ano": int})
    return serie.reset_index(drop=True)