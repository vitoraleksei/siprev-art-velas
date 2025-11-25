import pandas as pd
import os
import re

# --- CONFIGURAÇÃO ---
PASTA_DOS_ARQUIVOS = "dados_brutos"
ARQUIVO_FINAL = "dados_vendas.csv"

# --- 🔧 DICIONÁRIO DE SUBSTITUIÇÃO DIRETA ---
DE_PARA_PRODUTOS = {
    "VELA VOTIVA 7D": "VOTIVA 7 DIAS",
    "MACO VELA PALITO": "VELA PALITO",
}

MAPA_MESES = {
    'janeiro': '01', 'fevereiro': '02', 'março': '03', 'marco': '03',
    'abril': '04', 'maio': '05', 'junho': '06',
    'julho': '07', 'agosto': '08', 'setembro': '09',
    'outubro': '10', 'novembro': '11', 'dezembro': '12'
}

lista_dfs = []

print(f"📂 Iniciando unificação V10 (Correção Erro Palito /100)...")

for arquivo in os.listdir(PASTA_DOS_ARQUIVOS):
    caminho_completo = os.path.join(PASTA_DOS_ARQUIVOS, arquivo)
    nome_arquivo_lower = arquivo.lower()

    try:
        df_temp = None
        data_arquivo = None

        # TIPO 1: EXCEL
        if arquivo.endswith(".xlsx") or arquivo.endswith(".xls"):
            try:
                df_header = pd.read_excel(caminho_completo, header=None, nrows=10)
                texto_periodo = str(df_header.iloc[8, 0])
                match_data = re.search(r'(\d{2}/\d{2}/\d{4})', texto_periodo)
                if match_data: data_arquivo = match_data.group(1)
            except:
                pass

            try:
                df_temp = pd.read_excel(caminho_completo, header=10, engine="calamine")
            except:
                df_temp = pd.read_excel(caminho_completo, header=10)

            df_temp.columns = [str(col).strip().upper() for col in df_temp.columns]
            df_temp = df_temp.rename(columns={'PRODUTO': 'Produto', 'QUANTIDADE': 'Quantidade'})

        # TIPO 2: CSV
        elif arquivo.endswith(".csv"):
            lido = False
            for sep in [';', ',', '\t']:
                for enc in ['latin1', 'utf-8', 'utf-16']:
                    try:
                        df_temp = pd.read_csv(caminho_completo, sep=sep, encoding=enc)
                        if len(df_temp.columns) > 1:
                            lido = True
                            break
                    except:
                        continue
                if lido: break
            if not lido: continue

            df_temp.columns = [str(col).strip().lower() for col in df_temp.columns]
            mapa_csv = {'nome': 'Produto', 'desc_item': 'Produto', 'produto': 'Produto',
                        'numero de vendas': 'Quantidade', 'qtde': 'Quantidade', 'quantidade': 'Quantidade'}
            df_temp = df_temp.rename(columns=mapa_csv)

        # DATA
        if data_arquivo is None:
            mes_detectado = None
            for mes_nome, mes_num in MAPA_MESES.items():
                if mes_nome in nome_arquivo_lower:
                    mes_detectado = mes_num
                    break
            match_ano = re.search(r'(202[3-9])|[-_.](\d{2})[-_.]', arquivo)
            ano = "2024"
            if match_ano:
                v = match_ano.group(1) if match_ano.group(1) else match_ano.group(2)
                ano = v if len(v) == 4 else "20" + v
            elif "25" in arquivo:
                ano = "2025"
            elif "23" in arquivo:
                ano = "2023"
            if mes_detectado: data_arquivo = f"01/{mes_detectado}/{ano}"

        if df_temp is not None and 'Produto' in df_temp.columns and 'Quantidade' in df_temp.columns:
            if data_arquivo:
                df_temp['Data'] = data_arquivo
                lista_dfs.append(df_temp[['Data', 'Produto', 'Quantidade']])

    except Exception as e:
        print(f"  ❌ Erro em {arquivo}: {e}")

# --- CONSOLIDAÇÃO ---
if lista_dfs:
    df_final = pd.concat(lista_dfs, ignore_index=True)

    # 1. Limpeza Numérica e Texto
    df_final['Quantidade'] = df_final['Quantidade'].astype(str).str.replace(',', '.')
    df_final['Quantidade'] = pd.to_numeric(df_final['Quantidade'], errors='coerce')
    df_final['Produto'] = df_final['Produto'].astype(str).str.strip().str.upper()

    # Converte Data AGORA (necessário para o filtro de correção)
    df_final['Data'] = pd.to_datetime(df_final['Data'], dayfirst=True, errors='coerce')

    # --- 🚨 CORREÇÃO DE ERRO DE SISTEMA (PALITO / 100) ---
    print("🔧 Corrigindo erro do 'Palito C/100' (Fev/25 a Jul/25)...")

    # Filtro: Produto contém "PALITO C/100" E Data está entre Fev e Jul de 2025
    mask_palito = df_final['Produto'].str.contains("PALITO C/100", na=False)
    mask_data = (df_final['Data'] >= '2025-02-01') & (df_final['Data'] <= '2025-07-31')

    # Aplica a divisão por 100 apenas nessas linhas
    df_final.loc[mask_palito & mask_data, 'Quantidade'] = df_final.loc[mask_palito & mask_data, 'Quantidade'] / 100

    # --- FIM DA CORREÇÃO ---

    # Regras de Nomes
    print("🔧 Aplicando limpeza de nomes...")
    df_final['Produto'] = df_final['Produto'].str.replace("ALTAR ", "", regex=False)
    df_final['Produto'] = df_final['Produto'].str.replace(r"LIT.*GICA.*", "LITÚRGICA C/10", regex=True)
    df_final['Produto'] = df_final['Produto'].str.replace("VOTIVA 15CM", "15X5", regex=False)
    df_final['Produto'] = df_final['Produto'].replace(DE_PARA_PRODUTOS)

    # Finalização
    df_final = df_final.dropna(subset=['Produto', 'Quantidade'])
    df_final = df_final[df_final['Quantidade'] > 0]
    df_final = df_final.sort_values(by='Data')

    df_final.to_csv(ARQUIVO_FINAL, index=False)
    print(f"\n✨ SUCESSO! Dados corrigidos (Palitos divididos por 100).")
else:
    print("\n❌ Nenhum dado processado.")