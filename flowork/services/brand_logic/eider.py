def get_size_mapping_key(row):
    pn = str(row.get('product_number', '')).strip().upper()
    if not pn: return '기타'

    first = pn[0] if len(pn) > 0 else ''
    gender = pn[1] if len(pn) > 1 else ''
    code = pn[5] if len(pn) > 5 else ''

    if first == "J": return "키즈"
    if code in ["1", "2", "4", "5", "6", "M", "7"]: return "상의"
    if code in ["G", "N"]: return "신발"
    if code == "C": return "모자"
    if code == "S": return "양말"
    if code in ["B", "T"]: return "가방스틱"
    if code == "V": return "장갑"
    if code in ["A", "8", "9"]: return "기타"
    
    if code == "3":
        if gender == "M": return "남성하의"
        if gender == "W": return "여성하의"
        return "남성하의"

    val = str(row.get('item_category', '')).strip()
    if val and val not in ['nan', 'None', '']: return val
         
    return "기타"

def get_db_item_category(row, mapping_config=None):
    product_code = str(row.get('product_number', '')).strip().upper()
    
    if product_code.startswith("J"): return "키즈"

    if mapping_config:
        target_index = mapping_config.get('INDEX', 5)
        mapping_map = mapping_config.get('MAP', {})
        default_value = mapping_config.get('DEFAULT', '기타')

        if len(product_code) > target_index:
            code_char = product_code[target_index]
            return mapping_map.get(code_char, default_value)
    
    val = str(row.get('item_category', '')).strip()
    return val if val and val not in ['nan', 'None'] else '기타'