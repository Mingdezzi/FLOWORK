from flask_login import current_user
from flowork.models import Setting
from . import ui_bp
from datetime import date

@ui_bp.app_context_processor
def inject_image_helpers():
    default_prefix = 'https://files.ebizway.co.kr/files/10249/Style/'
    default_rule = '{product_number}.jpg'

    prefix = default_prefix
    rule = default_rule
    
    try:
        if current_user.is_authenticated and current_user.brand_id:
            setting_prefix = Setting.query.filter_by(
                brand_id=current_user.brand_id, key='IMAGE_URL_PREFIX'
            ).first()
            if setting_prefix and setting_prefix.value:
                prefix = setting_prefix.value
            
            setting_rule = Setting.query.filter_by(
                brand_id=current_user.brand_id, key='IMAGE_NAMING_RULE'
            ).first()
            if setting_rule and setting_rule.value:
                rule = setting_rule.value
                
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
            if current_user.is_super_admin:
                shop_name = 'FLOWORK (Super Admin)'
            elif current_user.store_id:
                shop_name = current_user.store.store_name
            elif current_user.brand_id:
                shop_name = f"{current_user.brand.brand_name} (본사)"
    except Exception:
        pass
    
    today_date = date.today().strftime('%Y-%m-%d')
    
    return dict(shop_name=shop_name, today_date=today_date)