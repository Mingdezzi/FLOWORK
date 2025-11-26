# fileName: mingdezzi/flowork/FLOWORK-c3d0a854c8688593f920b4aabbc4e40547365c57/flowork/services/brand_logic/eider.py

# [Refactor] 하드코딩된 로직을 매핑 테이블로 분리
# 추후 DB의 Settings 테이블이나 JSON 설정 파일에서 로드하도록 개선 가능
CATEGORY_MAP = {
    "1": "자켓", "2": "티셔츠", "4": "셔츠", "5": "다운", "6": "조끼",
    "M": "세트", "7": "고어텍스", "G": "고어텍스 등산화", "N": "등산화",
    "C": "모자", "S": "양말", "B": "가방스틱", "T": "가방스틱", "V": "장갑",
    "A": "기타", "8": "기타", "9": "기타"
}

def get_size_mapping_key(row):
    pn = str(row.get('product_number', '')).strip().upper()
    if not pn: return '기타'

    first = pn[0] if len(pn) > 0 else ''
    gender = pn[1] if len(pn) > 1 else ''
    code = pn[5] if len(pn) > 5 else ''

    if first == "J":
        return "키즈"
    
    # 매핑 테이블 우선 조회
    if code in CATEGORY_MAP:
        return CATEGORY_MAP[code]
    
    # 특수 로직 (하의)
    if code == "3":
        return "남성하의" if gender == "M" else "여성하의"

    val = str(row.get('item_category', '')).strip()
    if val and val not in ['nan', 'None', '']:
         return val
         
    return "기타"

def get_db_item_category(row, mapping_config=None):
    product_code = str(row.get('product_number', '')).strip().upper()
    
    if product_code.startswith("J"):
         return "키즈"

    if mapping_config:
        target_index = mapping_config.get('INDEX', 5)
        mapping_map = mapping_config.get('MAP', {})
        default_value = mapping_config.get('DEFAULT', '기타')

        if len(product_code) > target_index:
            code_char = product_code[target_index]
            return mapping_map.get(code_char, default_value)
    
    val = str(row.get('item_category', '')).strip()
    return val if val and val not in ['nan', 'None'] else '기타'