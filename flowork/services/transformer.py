import pandas as pd
import numpy as np
from flowork.services.brand_logic import get_brand_logic

def transform_horizontal_to_vertical(file_stream, size_mapping_config, category_mapping_config, column_map_indices):
    file_stream.seek(0)
    try:
        df_stock = pd.read_excel(file_stream, dtype=str)
    except:
        file_stream.seek(0)
        try:
            df_stock = pd.read_csv(file_stream, encoding='utf-8', dtype=str)
        except UnicodeDecodeError:
            file_stream.seek(0)
            df_stock = pd.read_csv(file_stream, encoding='cp949', dtype=str)

    new_columns = []
    for col in df_stock.columns:
        str_col = str(col).strip()
        if str_col.endswith('.0'):
            str_col = str_col[:-2]
        new_columns.append(str_col)
    df_stock.columns = new_columns

    extracted_data = pd.DataFrame()
    field_to_col_idx = {
        'product_number': column_map_indices.get('product_number'),
        'product_name': column_map_indices.get('product_name'),
        'color': column_map_indices.get('color'),
        'original_price': column_map_indices.get('original_price'),
        'sale_price': column_map_indices.get('sale_price'),
        'release_year': column_map_indices.get('release_year'),
        'item_category': column_map_indices.get('item_category'), 
    }

    total_cols = len(df_stock.columns)
    for field, idx in field_to_col_idx.items():
        if idx is not None and 0 <= idx < total_cols:
            extracted_data[field] = df_stock.iloc[:, idx]
        else:
            extracted_data[field] = None

    target_size_headers = [str(i) for i in range(30)]
    size_cols = [col for col in df_stock.columns if col in target_size_headers]
    
    if not size_cols:
        print("Warning: No size columns (0-29) found in Excel header.")
        return pd.DataFrame()

    df_merged = pd.concat([extracted_data, df_stock[size_cols]], axis=1)

    logic_name = category_mapping_config.get('LOGIC', 'GENERIC')
    logic_module = get_brand_logic(logic_name)

    df_merged['DB_Category'] = df_merged.apply(lambda r: logic_module.get_db_item_category(r, category_mapping_config), axis=1)
    df_merged['Mapping_Key'] = df_merged.apply(logic_module.get_size_mapping_key, axis=1)

    id_vars = ['product_number', 'product_name', 'color', 'original_price', 'sale_price', 'release_year', 'DB_Category', 'Mapping_Key']
    
    df_melted = df_merged.melt(
        id_vars=id_vars, 
        value_vars=size_cols, 
        var_name='Size_Code', 
        value_name='Quantity'
    )

    mapping_list = []
    for key, map_data in size_mapping_config.items():
        for code, real_size in map_data.items():
            mapping_list.append({
                'Mapping_Key': key,
                'Size_Code': str(code),
                'Real_Size': str(real_size)
            })
    
    df_map = pd.DataFrame(mapping_list)
    
    df_melted['Size_Code'] = df_melted['Size_Code'].astype(str)
    df_final = df_melted.merge(df_map, on=['Mapping_Key', 'Size_Code'], how='left')

    if '기타' in size_mapping_config:
        other_map_list = [{'Size_Code': str(code), 'Real_Size_Other': str(val)} 
                          for code, val in size_mapping_config['기타'].items()]
        df_other_map = pd.DataFrame(other_map_list)
        df_final = df_final.merge(df_other_map, on='Size_Code', how='left')
        df_final['Real_Size'] = df_final['Real_Size'].fillna(df_final['Real_Size_Other'])

    df_final = df_final.dropna(subset=['Real_Size'])

    df_final['hq_stock'] = pd.to_numeric(df_final['Quantity'], errors='coerce').fillna(0).astype(int)
    
    df_final['original_price'] = pd.to_numeric(df_final['original_price'], errors='coerce').fillna(0).astype(int)
    df_final['sale_price'] = pd.to_numeric(df_final['sale_price'], errors='coerce').fillna(0).astype(int)
    
    condition_op_only = (df_final['original_price'] > 0) & (df_final['sale_price'] == 0)
    condition_sp_only = (df_final['sale_price'] > 0) & (df_final['original_price'] == 0)
    
    df_final['sale_price'] = np.where(condition_op_only, df_final['original_price'], df_final['sale_price'])
    df_final['original_price'] = np.where(condition_sp_only, df_final['sale_price'], df_final['original_price'])
    
    df_final['release_year'] = pd.to_numeric(df_final['release_year'], errors='coerce').fillna(0).astype(int)
    
    str_cols = ['product_number', 'product_name', 'color', 'Real_Size', 'DB_Category']
    for col in str_cols:
        df_final[col] = df_final[col].astype(str).str.strip()

    df_final['is_favorite'] = 0

    df_final = df_final.rename(columns={
        'Real_Size': 'size',
        'DB_Category': 'item_category'
    })

    final_cols = [
        'product_number', 'product_name', 'color', 'size', 
        'hq_stock', 'sale_price', 'original_price', 
        'item_category', 'release_year', 'is_favorite'
    ]
    
    return df_final[final_cols]