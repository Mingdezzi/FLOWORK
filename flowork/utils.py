import json

CHOSUNG_LIST = ['ㄱ', 'ㄲ', 'ㄴ', 'ㄷ', 'ㄸ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅃ', 'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅉ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ']

def clean_string_upper(s, default=''):
    if not (s is not None and s == s): return default
    return str(s).replace('-', '').replace(' ', '').strip().upper()

def get_choseong(text):
    if not (text is not None and text == text): return ''
    text_cleaned = str(text).replace('-', '').replace(' ', '').strip().upper()
    result = ''
    for char in text_cleaned:
        if '가' <= char <= '힣':
            code = ord(char) - 0xAC00
            cho_index = code // (21 * 28)
            result += CHOSUNG_LIST[cho_index]
        elif 'ㄱ' <= char <= 'ㅎ':
            result += char
        elif 'A' <= char <= 'Z' or '0' <= char <= '9':
            result += char
    return result

def generate_barcode(row_data, brand_settings=None):
    try:
        pn = str(row_data.get('product_number', '')).strip()
        color = str(row_data.get('color', '')).strip()
        size = str(row_data.get('size', '')).strip()
        
        pn_cleaned = pn.replace('-', '')
        size_upper = size.upper()
        
        pn_final = pn_cleaned + '00' if len(pn_cleaned) <= 10 else pn_cleaned
        
        if size_upper == 'FREE': 
            size_final = '00F'
        elif size.isdigit():
            size_final = size.zfill(3)
        elif len(size_upper) <= 3 and not size.isdigit():
            if len(size_upper) == 3:
                size_final = size_upper
            else:
                size_final = size_upper.rjust(3, '0')
        else: 
            size_final = size_upper[:3]

        format_rule = None
        if brand_settings:
            format_rule = brand_settings.get('BARCODE_FORMAT')

        if format_rule:
            return format_rule.format(
                product_number=pn,
                color=color,
                size=size,
                pn_cleaned=pn_cleaned,
                size_upper=size_upper,
                pn_final=pn_final,
                size_final=size_final
            ).upper()
        
        if pn_final and color and size_final: 
            return f"{pn_final}{color}{size_final}".upper()
        else: 
            print(f"Barcode generation skipped (missing fields): {row_data}")
            return None
            
    except Exception as e: 
        print(f"Error generating barcode for {row_data}: {e}")
        return None

def get_sort_key(variant, brand_settings=None):
    product_number = ''
    if variant.product:
        product_number = variant.product.product_number
        
    color = variant.color or ''
    size_str = str(variant.size).upper().strip()
    
    custom_order_map = None
    if brand_settings:
        size_order_json = brand_settings.get('SIZE_SORT_ORDER')
        if size_order_json:
            try:
                size_list = json.loads(size_order_json)
                custom_order_map = {s.upper(): i for i, s in enumerate(size_list)}
            except json.JSONDecodeError:
                pass

    if custom_order_map and size_str in custom_order_map:
        sort_val = (0, custom_order_map[size_str], '')
    else:
        custom_order = {'2XS': 'XXS', '2XL': 'XXL', '3XL': 'XXXL'}
        size_str = custom_order.get(size_str, size_str)
        order_map = {'XXS': 0, 'XS': 1, 'S': 2, 'M': 3, 'L': 4, 'XL': 5, 'XXL': 6, 'XXXL': 7}
        
        if size_str.isdigit(): 
            sort_val = (1, int(size_str), '')
        elif size_str in order_map: 
            sort_val = (2, order_map[size_str], '')
        else: 
            sort_val = (3, 0, size_str)
            
    return (product_number, color, sort_val)