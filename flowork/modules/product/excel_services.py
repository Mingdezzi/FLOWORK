import pandas as pd
import numpy as np
import json
import traceback
from openpyxl.utils import column_index_from_string
from sqlalchemy.orm import selectinload
from flowork.models import db, Product, Variant, StoreStock, Setting, Store
from flowork.utils import clean_string_upper, get_choseong, generate_barcode
from flowork.services.brand_logic import get_brand_logic

def _get_column_indices(form, field_map):
    indices = {}
    for field, (key, req) in field_map.items():
        val = form.get(key)
        if req and not val: raise ValueError(f"{field} 열 선택 필수")
        indices[field] = (column_index_from_string(val) - 1) if val else None
    return indices

def _read_excel(file, indices):
    if hasattr(file, 'seek'): file.seek(0)
    try: df = pd.read_excel(file, header=0)
    except: 
        file.seek(0)
        df = pd.read_csv(file)
    
    if df.empty: return pd.DataFrame()
    
    rename_map = {}
    for field, idx in indices.items():
        if idx is not None and 0 <= idx < df.shape[1]:
            rename_map[df.columns[idx]] = field
            
    df = df[list(rename_map.keys())].rename(columns=rename_map)
    for field in indices:
        if field not in df.columns: df[field] = np.nan
    return df

def _optimize_df(df, settings, mode):
    if df.empty: return df
    df = df.dropna(subset=['product_number', 'color', 'size'])
    
    str_cols = ['product_number', 'product_name', 'color', 'size', 'item_category']
    for c in str_cols: 
        if c in df: df[c] = df[c].astype(str).str.strip().replace({'nan':None, 'None':None})
        
    num_cols = ['original_price', 'sale_price', 'release_year', 'hq_stock', 'store_stock']
    for c in num_cols:
        if c in df: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0).astype(int)

    if 'original_price' in df and 'sale_price' in df:
        op, sp = df['original_price'], df['sale_price']
        df['sale_price'] = np.where((op > 0) & (sp == 0), op, sp)
        df['original_price'] = np.where((sp > 0) & (op == 0), sp, op)

    if 'barcode' not in df: df['barcode'] = None
    no_bar = df['barcode'].isna() | (df['barcode'] == '')
    if no_bar.any():
        df.loc[no_bar, 'barcode'] = df[no_bar].apply(lambda r: generate_barcode(r.to_dict(), settings), axis=1)
    
    df = df.dropna(subset=['barcode'])
    
    df['product_number_cleaned'] = df['product_number'].apply(clean_string_upper)
    df['barcode_cleaned'] = df['barcode'].apply(clean_string_upper)
    if 'color' in df: df['color_cleaned'] = df['color'].apply(clean_string_upper)
    if 'size' in df: df['size_cleaned'] = df['size'].apply(clean_string_upper)
    if 'product_name' in df:
        df['product_name_cleaned'] = df['product_name'].apply(clean_string_upper)
        df['product_name_choseong'] = df['product_name'].apply(get_choseong)
    
    df['is_favorite'] = pd.to_numeric(df.get('is_favorite', 0), errors='coerce').fillna(0).astype(int)
    return df.drop_duplicates(subset=['barcode_cleaned'], keep='last')

def _transform_horizontal(file, settings, indices):
    file.seek(0)
    try: df = pd.read_excel(file, dtype=str)
    except: 
        file.seek(0)
        df = pd.read_csv(file, dtype=str)
    
    df.columns = [str(c).strip().replace('.0','') for c in df.columns]
    
    extracted = pd.DataFrame()
    for f, idx in indices.items():
        extracted[f] = df.iloc[:, idx] if idx is not None and 0 <= idx < len(df.columns) else None
        
    size_cols = [c for c in df.columns if c in [str(i) for i in range(30)]]
    if not size_cols: return pd.DataFrame()
    
    merged = pd.concat([extracted, df[size_cols]], axis=1)
    
    size_map_conf = json.loads(settings.get('SIZE_MAPPING', '{}'))
    cat_map_conf = json.loads(settings.get('CATEGORY_MAPPING_RULE', '{}'))
    logic = get_brand_logic(cat_map_conf.get('LOGIC', 'GENERIC'))
    
    merged['DB_Category'] = merged.apply(lambda r: logic.get_db_item_category(r, cat_map_conf), axis=1)
    merged['Mapping_Key'] = merged.apply(logic.get_size_mapping_key, axis=1)
    
    melted = merged.melt(
        id_vars=['product_number', 'product_name', 'color', 'original_price', 'sale_price', 'release_year', 'DB_Category', 'Mapping_Key'],
        value_vars=size_cols, var_name='Size_Code', value_name='Quantity'
    )
    
    map_list = []
    for k, m in size_map_conf.items():
        for c, s in m.items(): map_list.append({'Mapping_Key': k, 'Size_Code': str(c), 'Real_Size': str(s)})
    
    df_map = pd.DataFrame(map_list)
    melted['Size_Code'] = melted['Size_Code'].astype(str)
    final = melted.merge(df_map, on=['Mapping_Key', 'Size_Code'], how='left')
    
    if '기타' in size_map_conf:
        others = pd.DataFrame([{'Size_Code': str(c), 'Real_Size_Other': str(v)} for c, v in size_map_conf['기타'].items()])
        final = final.merge(others, on=['Size_Code'], how='left')
        final['Real_Size'] = final['Real_Size'].fillna(final['Real_Size_Other'])
        
    final = final.dropna(subset=['Real_Size'])
    final['hq_stock'] = pd.to_numeric(final['Quantity'], errors='coerce').fillna(0).astype(int)
    final = final.rename(columns={'Real_Size': 'size', 'DB_Category': 'item_category'})
    
    return final[['product_number', 'product_name', 'color', 'size', 'hq_stock', 'sale_price', 'original_price', 'item_category', 'release_year']]

def verify_stock_excel(file_path, form, upload_mode):
    try:
        field_map = {'product_number': ('col_pn', True)}
        column_map_indices = _get_column_indices(form, field_map)
        
        with open(file_path, 'rb') as f:
            df = _read_excel(f, column_map_indices)
            
        if df.empty:
            return {'status': 'success', 'suspicious_rows': []}

        df['_row_index'] = df.index + 2
        suspicious_rows = []
        
        for _, row in df.iterrows():
            pn = row.get('product_number')
            if pd.isna(pn) or str(pn).strip() == "":
                suspicious_rows.append({
                    'row_index': int(row['_row_index']), 
                    'preview': '(품번없음)', 
                    'reasons': '품번 누락'
                })
                
        return {'status': 'success', 'suspicious_rows': suspicious_rows[:100]}

    except Exception as e:
        return {'status': 'error', 'message': f"검증 중 오류: {e}"}

def process_stock_upsert(file, form, mode, brand_id, store_id=None, callback=None, allow_create=True, excluded_rows=None):
    try:
        settings = {s.key: s.value for s in Setting.query.filter_by(brand_id=brand_id).all()}
        is_horiz = form.get('is_horizontal') == 'on'
        
        fields = {
            'product_number': ('col_pn', True), 'color': ('col_color', True),
            'product_name': ('col_pname', False), 'release_year': ('col_year', False),
            'item_category': ('col_category', False), 'original_price': ('col_oprice', False),
            'sale_price': ('col_sprice', False), 'is_favorite': ('col_favorite', False)
        }
        
        if mode == 'hq' or mode == 'db_import':
            if not is_horiz:
                fields.update({'size': ('col_size', True), 'hq_stock': ('col_hq_stock', True)})
        elif mode == 'store':
            if not is_horiz:
                fields.update({'size': ('col_size', True), 'store_stock': ('col_store_stock', True)})
        
        indices = _get_column_indices(form, fields)
        
        if is_horiz:
            df = _transform_horizontal(file, settings, indices)
            if mode == 'store' and 'hq_stock' in df: df.rename(columns={'hq_stock': 'store_stock'}, inplace=True)
        else:
            df = _read_excel(file, indices)
            if excluded_rows:
                drop_indices = [r - 2 for r in excluded_rows]
                df = df.drop(index=drop_indices, errors='ignore')
            
        df = _optimize_df(df, settings, mode)
        if df.empty: return 0, 0, "유효 데이터 없음", "warning"
        
        p_map = {p.product_number_cleaned: p for p in Product.query.filter_by(brand_id=brand_id).options(selectinload(Product.variants).selectinload(Variant.stock_levels)).all()}
        v_map = {}
        for p in p_map.values():
            for v in p.variants: v_map[v.barcode_cleaned] = v
            
        store_stock_map = {}
        if mode == 'store':
            v_ids = [v.id for v in v_map.values()]
            if v_ids:
                stocks = StoreStock.query.filter(StoreStock.store_id==store_id, StoreStock.variant_id.in_(v_ids)).all()
                store_stock_map = {s.variant_id: s for s in stocks}
                
        cnt_prod, cnt_var, cnt_upd = 0, 0, 0
        total = len(df)
        records = df.to_dict('records')
        
        for i, row in enumerate(records):
            if callback and i % 500 == 0: callback(i, total)
            try:
                pn_clean, bc_clean = row['product_number_cleaned'], row['barcode_cleaned']
                
                prod = p_map.get(pn_clean)
                if not prod:
                    if not allow_create: continue
                    pname = row.get('product_name') or row['product_number']
                    prod = Product(
                        brand_id=brand_id, product_number=row['product_number'], product_name=pname,
                        product_number_cleaned=pn_clean, product_name_cleaned=clean_string_upper(pname),
                        product_name_choseong=get_choseong(pname)
                    )
                    db.session.add(prod)
                    p_map[pn_clean] = prod
                    cnt_prod += 1
                
                if row.get('release_year') and row['release_year'] > 0: prod.release_year = row['release_year']
                if row.get('item_category'): prod.item_category = row['item_category']
                if row.get('is_favorite') == 1: prod.is_favorite = 1
                
                var = v_map.get(bc_clean)
                if not var:
                    if not allow_create: continue
                    var = Variant(
                        product=prod, barcode=row['barcode'], color=row['color'], size=row['size'],
                        original_price=row['original_price'], sale_price=row['sale_price'], hq_quantity=0,
                        barcode_cleaned=bc_clean, color_cleaned=clean_string_upper(row['color']),
                        size_cleaned=clean_string_upper(row['size'])
                    )
                    db.session.add(var)
                    v_map[bc_clean] = var
                    cnt_var += 1
                else:
                    if row['original_price'] > 0: var.original_price = row['original_price']
                    if row['sale_price'] > 0: var.sale_price = row['sale_price']
                    
                if (mode == 'hq' or mode == 'db_import') and 'hq_stock' in row:
                    var.hq_quantity = row['hq_stock']
                    cnt_upd += 1
                elif mode == 'store' and 'store_stock' in row:
                    qty = row['store_stock']
                    if var.id in store_stock_map:
                        store_stock_map[var.id].quantity = qty
                    else:
                        exists = False
                        if hasattr(var, 'stock_levels'):
                            for s in var.stock_levels:
                                if s.store_id == store_id:
                                    s.quantity = qty
                                    exists = True
                                    break
                        if not exists:
                            new_s = StoreStock(store_id=store_id, quantity=qty)
                            var.stock_levels.append(new_s)
                    cnt_upd += 1
            except: continue
            
        db.session.commit()
        if callback: callback(total, total)
        return cnt_upd, cnt_var, f"성공: 상품 {cnt_prod} / 옵션 {cnt_var} 생성, {cnt_upd}건 업데이트", 'success'
        
    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        return 0, 0, str(e), 'error'

def import_db_full(file, form, brand_id, callback=None):
    try:
        res, cnt_prod, msg, cat = process_stock_upsert(file, form, 'db_import', brand_id, allow_create=True, callback=callback) 
        
        store_ids = db.session.query(Store.id).filter_by(brand_id=brand_id)
        db.session.query(StoreStock).filter(StoreStock.store_id.in_(store_ids)).delete(synchronize_session=False)
        
        return True, "DB 초기화 및 로드 완료", 'success'
    except Exception as e:
        return False, str(e), 'error'