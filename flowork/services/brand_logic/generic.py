def get_size_mapping_key(row):
    val = str(row.get('item_category', '')).strip()
    if val and val not in ['nan', 'None', '']:
        return val
    return '기타'

def get_db_item_category(row, mapping_config=None):
    val = str(row.get('item_category', '')).strip()
    if val and val not in ['nan', 'None', '']:
        return val
    return '기타'