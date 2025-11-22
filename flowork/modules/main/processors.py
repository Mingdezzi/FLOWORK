from flask_login import current_user
from flowork.models import Setting
from . import main_bp

@main_bp.app_context_processor
def inject_vars():
    shop = 'FLOWORK'
    prefix = 'https://files.ebizway.co.kr/files/10249/Style/'
    rule = '{product_number}.jpg'
    
    if current_user.is_authenticated:
        if current_user.is_super_admin: shop = 'FLOWORK (Admin)'
        elif current_user.store_id: shop = current_user.store.store_name
        elif current_user.brand_id:
            shop = f"{current_user.brand.brand_name} (본사)"
            s1 = Setting.query.filter_by(brand_id=current_user.brand_id, key='IMAGE_URL_PREFIX').first()
            if s1: prefix = s1.value
            s2 = Setting.query.filter_by(brand_id=current_user.brand_id, key='IMAGE_NAMING_RULE').first()
            if s2: rule = s2.value
            
    def get_img(p):
        if not p: return ''
        pn = p.product_number.split(' ')[0]
        yr = str(p.release_year) if p.release_year else (f"20{pn[3:5]}" if len(pn)>=5 and pn[3:5].isdigit() else "")
        col = p.variants[0].color if p.variants and p.variants[0].color else '00'
        try: fname = rule.format(product_number=pn, color=col, year=yr)
        except: fname = f"{pn}.jpg"
        return f"{prefix}{fname}"
        
    return dict(shop_name=shop, IMAGE_URL_PREFIX=prefix, get_image_url=get_img)