from flask import request
from flask_login import current_user
from flowork.models import Setting
from flowork.extensions import cache
from . import ui_bp
from datetime import date

@ui_bp.app_context_processor
def inject_image_helpers():
    # [최적화] 이미지 URL 프리픽스 및 룰 계산
    # 캐시 적용: 동일 브랜드 ID에 대해 5분간 DB 조회 없이 메모리에서 반환
    return dict(
        IMAGE_URL_PREFIX=get_image_prefix(current_user.current_brand_id if current_user.is_authenticated else None),
        get_image_url=get_image_url_helper
    )

@cache.memoize(timeout=300)
def get_image_prefix_and_rule(brand_id):
    if not brand_id:
        return 'https://files.ebizway.co.kr/files/10249/Style/', '{product_number}.jpg'
    
    try:
        setting_prefix = Setting.query.filter_by(brand_id=brand_id, key='IMAGE_URL_PREFIX').first()
        setting_rule = Setting.query.filter_by(brand_id=brand_id, key='IMAGE_NAMING_RULE').first()
        
        prefix = setting_prefix.value if setting_prefix and setting_prefix.value else 'https://files.ebizway.co.kr/files/10249/Style/'
        rule = setting_rule.value if setting_rule and setting_rule.value else '{product_number}.jpg'
        return prefix, rule
    except:
        return 'https://files.ebizway.co.kr/files/10249/Style/', '{product_number}.jpg'

def get_image_prefix(brand_id):
    prefix, _ = get_image_prefix_and_rule(brand_id)
    return prefix

def get_image_url_helper(product):
    if not product: return ''
    
    # 여기서 brand_id를 가져오기 위해 product.brand_id를 쓸 수도 있지만, 
    # current_user 컨텍스트가 안전함
    brand_id = product.brand_id
    prefix, rule = get_image_prefix_and_rule(brand_id)
    
    pn = product.product_number.split(' ')[0]
    year = str(product.release_year) if product.release_year else ""
    if not year and len(pn) >= 5 and pn[3:5].isdigit():
        year = f"20{pn[3:5]}"
    
    color = '00'
    if product.variants:
        first_variant = product.variants[0]
        if first_variant.color:
            color = first_variant.color

    try:
        filename = rule.format(product_number=pn, color=color, year=year)
    except:
        filename = f"{pn}.jpg"
        
    return f"{prefix}{filename}"

@ui_bp.app_context_processor
def inject_global_vars():
    # [최적화] AJAX 요청(탭 내용 로드)일 때는 상단바/사이드바용 변수가 필요 없으므로 생략
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return {}

    shop_name = 'FLOWORK' 
    try:
        if current_user.is_authenticated:
            if current_user.is_super_admin:
                shop_name = 'FLOWORK (Super Admin)'
            elif current_user.store_id and current_user.store:
                shop_name = current_user.store.store_name
            elif current_user.brand_id and current_user.brand:
                shop_name = f"{current_user.brand.brand_name} (본사)"
    except Exception:
        pass
    
    today_date = date.today().strftime('%Y-%m-%d')
    
    return dict(shop_name=shop_name, today_date=today_date)