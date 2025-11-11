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
    """
    상품 정보를 바탕으로 바코드를 생성합니다.
    brand_settings에 'BARCODE_FORMAT' 설정이 있으면 해당 포맷을 사용합니다.
    기본값: {pn_final}{color}{size_final} (기존 로직)
    """
    try:
        pn = str(row_data.get('product_number', '')).strip()
        color = str(row_data.get('color', '')).strip()
        size = str(row_data.get('size', '')).strip()
        
        # 기본 정제 데이터 준비
        pn_cleaned = pn.replace('-', '')
        size_upper = size.upper()
        
        # 1. 품번 처리 (10자리 이하면 00 붙임 - 기존 로직 호환용)
        pn_final = pn_cleaned + '00' if len(pn_cleaned) <= 10 else pn_cleaned
        
        # 2. 사이즈 처리 (3자리 패딩 - 기존 로직 호환용)
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

        # 설정된 포맷 규칙 확인
        format_rule = None
        if brand_settings:
            format_rule = brand_settings.get('BARCODE_FORMAT')

        if format_rule:
            # 포맷에 맞춰 문자열 생성 (필요한 변수들을 모두 전달)
            return format_rule.format(
                product_number=pn,
                color=color,
                size=size,
                pn_cleaned=pn_cleaned,
                size_upper=size_upper,
                pn_final=pn_final,
                size_final=size_final
            ).upper()
        
        # 설정이 없으면 기본 로직 (기존 하드코딩 방식) 사용
        if pn_final and color and size_final: 
            return f"{pn_final}{color}{size_final}".upper()
        else: 
            print(f"Barcode generation skipped (missing fields): {row_data}")
            return None
            
    except Exception as e: 
        print(f"Error generating barcode for {row_data}: {e}")
        return None

def get_sort_key(variant, brand_settings=None):
    """
    옵션(Variant) 정렬을 위한 키를 반환합니다.
    brand_settings에 'SIZE_SORT_ORDER' (JSON 리스트)가 있으면 그 순서를 따릅니다.
    """
    color = variant.color or ''
    size_str = str(variant.size).upper().strip()
    
    # 1. 브랜드별 커스텀 정렬 순서 확인
    custom_order_map = None
    if brand_settings:
        size_order_json = brand_settings.get('SIZE_SORT_ORDER')
        if size_order_json:
            try:
                size_list = json.loads(size_order_json)
                # 리스트 인덱스를 우선순위로 사용 (0부터 시작)
                custom_order_map = {s.upper(): i for i, s in enumerate(size_list)}
            except json.JSONDecodeError:
                pass

    # 커스텀 순서가 있고, 현재 사이즈가 그 안에 포함된 경우
    if custom_order_map and size_str in custom_order_map:
        # 우선순위 0: 커스텀 리스트 순서대로
        sort_key = (0, custom_order_map[size_str], '')
    else:
        # 2. 기본 정렬 로직 (기존 하드코딩 유지 - 커스텀 설정 없을 때 fallback)
        custom_order = {'2XS': 'XXS', '2XL': 'XXL', '3XL': 'XXXL'}
        size_str = custom_order.get(size_str, size_str)
        order_map = {'XXS': 0, 'XS': 1, 'S': 2, 'M': 3, 'L': 4, 'XL': 5, 'XXL': 6, 'XXXL': 7}
        
        if size_str.isdigit(): 
            # 우선순위 1: 숫자 사이즈
            sort_key = (1, int(size_str), '')
        elif size_str in order_map: 
            # 우선순위 2: 영문 표준 사이즈 (XXS~XXXL)
            sort_key = (2, order_map[size_str], '')
        else: 
            # 우선순위 3: 그 외 문자열 (알파벳순)
            sort_key = (3, 0, size_str)
            
    # 컬러명 -> 사이즈 정렬 키 순으로 반환
    return (color, sort_key)