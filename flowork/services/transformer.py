import pandas as pd
import io

def transform_horizontal_to_vertical(file_stream, size_mapping_config, category_mapping_config):
    """
    가로형 재고 데이터를 세로형으로 변환합니다.
    1. size_mapping_config: 사이즈 코드(0,1..)를 실제 사이즈(95,100..)로 변환하는 설정
    2. category_mapping_config: 품번 특정 자리를 분석해 품목(자켓, 바지..)을 결정하는 설정
    """
    # 1. 파일 로딩
    file_stream.seek(0)
    try:
        df_stock = pd.read_excel(file_stream)
    except:
        file_stream.seek(0)
        try:
            df_stock = pd.read_csv(file_stream, encoding='utf-8')
        except UnicodeDecodeError:
            file_stream.seek(0)
            df_stock = pd.read_csv(file_stream, encoding='cp949')

    # -------------------------------------------------------------------------
    # [로직 1] 사이즈 분류용 키 결정 (JSON 사이즈표 매핑용)
    # -------------------------------------------------------------------------
    def get_size_mapping_key(row):
        product_code = str(row.get('상품코드', '')).strip()
        original_category = str(row.get('구분', '')).strip()
        
        # 1. 키즈 체크
        if product_code.startswith('J'):
            return '키즈'
        
        # 2. 성별/아이템 코드 추출
        gender_code = product_code[1] if len(product_code) > 1 else ''
        item_type_code = product_code[2] if len(product_code) > 2 else ''

        # 3. 하의 정밀 분류
        if '하의' in original_category or item_type_code == '3':
            if gender_code == 'M': return '남성하의'
            elif gender_code == 'W': return '여성하의'
            elif gender_code == 'U': return '남성하의' # 공용 -> 남성하의
        
        # 4. 상의/신발/용품 분류
        if '상의' in original_category or item_type_code in ['1', '2', '4', '5', '6']:
            return '상의'
        elif '신발' in original_category or 'G' in product_code or 'N' in product_code:
            return '신발'
        elif '모자' in original_category: return '모자'
        elif '양말' in original_category: return '양말'
        elif '장갑' in original_category: return '장갑'
        elif '가방' in original_category or '스틱' in original_category: return '가방스틱'
            
        return original_category

    # -------------------------------------------------------------------------
    # [로직 2] DB 저장용 품목 결정 (JSON 설정 참조)
    # -------------------------------------------------------------------------
    def get_db_item_category(row):
        product_code = str(row.get('상품코드', '')).strip()
        
        # 설정이 없으면 기본값 반환
        if not category_mapping_config:
            return "기타"

        target_index = category_mapping_config.get('INDEX', 5) # 기본값: 6번째 글자(인덱스 5)
        mapping_map = category_mapping_config.get('MAP', {})
        default_value = category_mapping_config.get('DEFAULT', '기타')

        # 품번 길이가 인덱스보다 짧으면 분석 불가
        if len(product_code) <= target_index:
            return default_value
            
        code_char = product_code[target_index] 
        
        # 매핑 테이블에서 찾아서 반환, 없으면 DEFAULT 값
        return mapping_map.get(code_char, default_value)

    # 두 개의 독립적인 컬럼 생성
    df_stock['Mapping_Key'] = df_stock.apply(get_size_mapping_key, axis=1)
    df_stock['DB_Category'] = df_stock.apply(get_db_item_category, axis=1)

    # 3. 데이터 변환 (Melt: 가로 -> 세로)
    id_vars = ['상품코드', '상품명', '칼라', '현판매가', '구분', 'Mapping_Key', 'DB_Category']
    available_id_vars = [col for col in id_vars if col in df_stock.columns]
    
    # 사이즈 컬럼 찾기 (0 ~ 29)
    value_vars = [col for col in df_stock.columns if str(col) in [str(i) for i in range(30)]]

    if not value_vars:
        return []

    df_melted = df_stock.melt(
        id_vars=available_id_vars, 
        value_vars=value_vars, 
        var_name='Size_Code', 
        value_name='Quantity'
    )

    # 재고 수량 정리
    df_melted['Quantity'] = pd.to_numeric(df_melted['Quantity'], errors='coerce').fillna(0).astype(int)
    df_melted = df_melted[df_melted['Quantity'] > 0]

    # 4. 사이즈 코드 -> 실제 사이즈 매핑 (Mapping_Key 사용)
    def get_real_size(row):
        mapping_key = row['Mapping_Key']
        size_code = str(row['Size_Code'])
        
        if mapping_key in size_mapping_config:
            mapping = size_mapping_config[mapping_key]
            if size_code in mapping:
                return str(mapping[size_code])
        
        # 매핑 실패 시 '기타' 등으로 재시도
        if '기타' in size_mapping_config and size_code in size_mapping_config['기타']:
             return str(size_mapping_config['기타'][size_code])
             
        return "Unknown"

    df_melted['Real_Size'] = df_melted.apply(get_real_size, axis=1)
    
    # 매핑 실패한 데이터 제거
    df_final = df_melted[df_melted['Real_Size'] != "Unknown"]

    # 5. 결과 반환
    result_list = []
    for _, row in df_final.iterrows():
        item_data = {
            'product_number': str(row.get('상품코드', '')).strip(),
            'product_name': str(row.get('상품명', '')).strip(),
            'color': str(row.get('칼라', '')).strip(),
            'size': str(row.get('Real_Size', '')).strip(),
            'hq_stock': int(row.get('Quantity', 0)),
            'sale_price': int(row.get('현판매가', 0)),
            'original_price': int(row.get('현판매가', 0)),
            'item_category': str(row.get('DB_Category', '기타')), # 결정된 DB 품목 사용
            'release_year': None,
            'is_favorite': 0
        }
        result_list.append(item_data)

    return result_list