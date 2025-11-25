from flask_login import current_user
from flowork.models import Setting
from flowork.extensions import cache # 캐시 모듈 임포트
from . import ui_bp
from datetime import date

@ui_bp.app_context_processor
def inject_image_helpers():
    default_prefix = 'https://files.ebizway.co.kr/files/10249/Style/'
    default_rule = '{product_number}.jpg'

    prefix = default_prefix
    rule = default_rule
    
    # [최적화] DB 조회 결과를 캐싱하여 반복적인 DB 접속 방지 (5분간 캐시)
    # 키는 brand_id에 따라 달라지도록 설정
    try:
        if current_user.is_authenticated and current_user.brand_id:
            brand_id = current_user.brand_id
            
            # 캐시 키 생성
            cache_key_prefix = f'brand_img_prefix_{brand_id}'
            cache_key_rule = f'brand_img_rule_{brand_id}'
            
            # 캐시에서 조회 시도
            cached_prefix = cache.get(cache_key_prefix)
            cached_rule = cache.get(cache_key_rule)

            if cached_prefix and cached_rule:
                prefix = cached_prefix
                rule = cached_rule
            else:
                # 캐시에 없으면 DB 조회
                setting_prefix = Setting.query.filter_by(
                    brand_id=brand_id, key='IMAGE_URL_PREFIX'
                ).first()
                
                setting_rule = Setting.query.filter_by(
                    brand_id=brand_id, key='IMAGE_NAMING_RULE'
                ).first()

                if setting_prefix and setting_prefix.value:
                    prefix = setting_prefix.value
                
                if setting_rule and setting_rule.value:
                    rule = setting_rule.value
                
                # 조회 결과 캐시에 저장 (300초 = 5분)
                cache.set(cache_key_prefix, prefix, timeout=300)
                cache.set(cache_key_rule, rule, timeout=300)
                
    except Exception:
        pass

    def get_image_url(product):
        if not product: return ''
        
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
            filename = rule.format(
                product_number=pn,
                color=color,
                year=year
            )
        except Exception:
            filename = f"{pn}.jpg"
            
        return f"{prefix}{filename}"

    return dict(
        IMAGE_URL_PREFIX=prefix,
        get_image_url=get_image_url
    )

@ui_bp.app_context_processor
def inject_global_vars():
    shop_name = 'FLOWORK' 
    try:
        if current_user.is_authenticated:
            # [최적화] 사용자 정보 객체에 이미 로드된 관계나 속성을 사용하여 DB 쿼리 최소화
            if current_user.is_super_admin:
                shop_name = 'FLOWORK (Super Admin)'
            elif current_user.store_id and current_user.store: # .store 접근 시 로드됨
                shop_name = current_user.store.store_name
            elif current_user.brand_id and current_user.brand: # .brand 접근 시 로드됨
                shop_name = f"{current_user.brand.brand_name} (본사)"
    except Exception:
        pass
    
    today_date = date.today().strftime('%Y-%m-%d')
    
    return dict(shop_name=shop_name, today_date=today_date)