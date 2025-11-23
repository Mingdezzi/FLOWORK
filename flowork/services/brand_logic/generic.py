def get_size_mapping_key(row):
    """
    [범용] 사이즈 매핑 키 결정
    기본적으로 엑셀의 'item_category' 컬럼 값을 사용하거나 '기타'를 반환
    """
    val = str(row.get('item_category', '')).strip()
    if val and val not in ['nan', 'None', '']:
        return val
    return '기타'

def get_db_item_category(row, mapping_config=None):
    """
    [범용] DB 저장용 카테고리 결정
    엑셀의 'item_category' 컬럼 값을 그대로 사용
    """
    val = str(row.get('item_category', '')).strip()
    if val and val not in ['nan', 'None', '']:
        return val
    return '기타'