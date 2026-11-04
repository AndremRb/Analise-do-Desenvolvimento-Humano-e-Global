# -*- coding: utf-8 -*-
from .texto import normalizar_texto, extrair_ano, converter_valor,detectar_encoding,_limpar,ler_titulo_ipeadata,identificar_arquivo_ipeadata,ler_ipeadata_por_uf,ler_ipeadata_serie_anual
from .ufs import UFS, MAPA_UF, CODIGO_PARA_UF, eh_estado, adicionar_dados_uf
from .leitura import (ler_csv_flexivel, encontrar_coluna,
                      ler_tabela_sidra_horizontal, padronizar_serie_por_codigo,ler_brent,brent_anual,_localizar_anos,ler_tabela_anual,_ler_rod_bruto,numerico,ler_rodoviario,total_oficial_rodoviario,quedas_bruscas,ranking_ufs,_ano_da_celula,achar_aba,achar_coluna,normalizarP,ler_aba_longa, ler_voos, ler_tarifa, ler_custos)
from .limpeza import (resumo_duplicados, remover_duplicados,
                      resumo_ausentes, verificar_cobertura)
from .transformacao import (filtrar_anos, juntar_por_uf_ano,
                            variacao_entre_anos, indice_base)
from .analise import (tabela_contingencia, correlacao,
                      teste_robustez, classificar_resultado,juntar_indicador,_movimento,variacao_indicador,tabela_contingencia_indicador,r_critico,teste_robustez_indicador,resumo_choque_indicador,juntar_series_anuais,variacoes_anuais,tabela_contingencia_sinais,r_critico_2,correlacao_temporal,teste_robustez_series)
from .graficos import grafico_dispersao, grafico_total_por_ano, grafico_indice_ufs,grafico_dispersao_indicador,grafico_indices_duplos,grafico_brent_anual,grafico_indices_brent,grafico_dispersao_anos,grafico_barras_uf
from .armazenamento import salvar_dataframe, salvar_figura