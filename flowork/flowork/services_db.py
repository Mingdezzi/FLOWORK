import re
from sqlalchemy import or_, update, exc
from flowork.models import db, Product, Variant, StoreStock
from flowork.utils import get_choseong, clean_string_upper

def get_filter_options_from_db(brand_id):
    try:
        base_query = db.session.query(Product).filter_by(brand_id=brand_id)
        
        categories = [r[0] for r in base_query.distinct(Product.item_category).with_entities(Product.item_category).order_by(Product.item_category).all() if r[0]]
        
        years = [r[0] for r in base_query.distinct(Product.release_year).with_entities(Product.release_year).order_by(Product.release_year.desc()).all() if r[0]]
        
        variant_query = db.session.query(Variant).join(Product).filter(Product.brand_id == brand_id)
        
        colors = [r[0] for r in variant_query.distinct(Variant.color).with_entities(Variant.color).order_by(Variant.color).all() if r[0]]
        
        sizes_raw = [r[0] for r in variant_query.distinct(Variant.size).with_entities(Variant.size).all() if r[0]]
        
        def size_sort_key(size_str):
            size_str_upper = str(size_str).upper().strip()
            custom_order = {'2XS': 'XXS', '2XL': 'XXL', '3XL': 'XXXL'}
            size_str_upper = custom_order.get(size_str_upper, size_str_upper)
            order_map = {'XXS': 0, 'XS': 1, 'S': 2, 'M': 3, 'L': 4, 'XL': 5, 'XXL': 6, 'XXXL': 7}
            
            if size_str_upper.isdigit():
                return (1, int(size_str_upper))
            elif size_str_upper in order_map:
                return (2, order_map[size_str_upper])
            else:
                return (3, size_str_upper)
        
        sizes = sorted(sizes_raw, key=size_sort_key)

        original_prices = [r[0] for r in variant_query.distinct(Variant.original_price).with_entities(Variant.original_price).order_by(Variant.original_price.desc()).all() if r[0] and r[0] > 0]
        sale_prices = [r[0] for r in variant_query.distinct(Variant.sale_price).with_entities(Variant.sale_price).order_by(Variant.sale_price.desc()).all() if r[0] and r[0] > 0]


        return {
            'categories': categories,
            'years': years,
            'colors': colors,
            'sizes': sizes,
            'original_prices': original_prices,
            'sale_prices': sale_prices
        }
    except Exception as e:
        print(f"Error fetching filter options: {e}")
        return { 'categories': [], 'years': [], 'colors': [], 'sizes': [], 'original_prices': [], 'sale_prices': [] }

def sync_missing_data_in_db(brand_id):
    updated_variant_count = 0
    updated_product_count = 0
    
    try:
        print("Creating product default data lookup for sync...")
        all_variants = db.session.query(Variant).join(Product).filter(Product.brand_id == brand_id).all()
        all_products = db.session.query(Product).filter(Product.brand_id == brand_id).all()

        product_default_lookup = {}
        
        for v in all_variants:
            pn = v.product.product_number 
            if pn not in product_default_lookup:
                 product_default_lookup[pn] = {}
            
            if 'original_price' not in product_default_lookup[pn] and v.original_price > 0:
                 product_default_lookup[pn]['original_price'] = v.original_price
            if 'sale_price' not in product_default_lookup[pn] and v.sale_price > 0:
                 product_default_lookup[pn]['sale_price'] = v.sale_price

        for p in all_products:
             if p.product_number not in product_default_lookup:
                 product_default_lookup[p.product_number] = {}

             if 'item_category' not in product_default_lookup[p.product_number] and p.item_category:
                  product_default_lookup[p.product_number]['item_category'] = p.item_category
             if 'release_year' not in product_default_lookup[p.product_number] and p.release_year:
                  product_default_lookup[p.product_number]['release_year'] = p.release_year

        print(f"Default data lookup created with {len(product_default_lookup)} entries.")

        variants_to_update = db.session.query(Variant).join(Product).filter(
            Product.brand_id == brand_id,
            or_(Variant.original_price == 0, Variant.original_price.is_(None),
                Variant.sale_price == 0, Variant.sale_price.is_(None))
        ).all()
        print(f"Found {len(variants_to_update)} variants to update PRICE.")

        for variant in variants_to_update:
            defaults = product_default_lookup.get(variant.product.product_number)
            if defaults:
                updated_this_variant = False
                if (variant.original_price is None or variant.original_price == 0) and 'original_price' in defaults:
                    variant.original_price = defaults['original_price']
                    updated_this_variant = True
                if (variant.sale_price is None or variant.sale_price == 0) and 'sale_price' in defaults:
                    variant.sale_price = defaults['sale_price']
                    updated_this_variant = True
                if updated_this_variant:
                    updated_variant_count += 1

        products_to_update = db.session.query(Product).filter(
             Product.brand_id == brand_id,
             or_(Product.item_category.is_(None), Product.item_category == '',
                 Product.release_year.is_(None),
                 Product.product_name_choseong.is_(None)) 
        ).all()
        print(f"Found {len(products_to_update)} products to update INFO.")
        
        year_pattern = re.compile(r'^M(2[0-9])')

        for product in products_to_update:
            defaults = product_default_lookup.get(product.product_number)
            updated_this_product = False
            
            if (not product.item_category) and defaults and 'item_category' in defaults:
                product.item_category = defaults['item_category']
                updated_this_product = True
            
            if product.release_year is None:
                if defaults and 'release_year' in defaults:
                    product.release_year = defaults['release_year']
                    updated_this_product = True
                else:
                    pn_cleaned = product.product_number_cleaned or clean_string_upper(product.product_number)
                    match = year_pattern.match(pn_cleaned)
                    if match:
                        year_short = match.group(1)
                        product.release_year = int(f"20{year_short}")
                        updated_this_product = True
            
            if not product.product_name_choseong:
                product.product_name_choseong = get_choseong(product.product_name)
                updated_this_product = True

            if updated_this_product:
                updated_product_count += 1
        
        if updated_variant_count > 0 or updated_product_count > 0:
            db.session.commit()
            return (True, f"동기화 완료: 상품(품목/년도/초성) {updated_product_count}개, SKU(가격) {updated_variant_count}개가 업데이트되었습니다.", "success")
        else:
            return (True, "동기화할 데이터가 없거나, 참조할 데이터가 충분하지 않습니다.", "info")

    except Exception as e:
        db.session.rollback()
        print(f"Sync error: {e}")
        import traceback
        traceback.print_exc()
        return (False, f"동기화 중 오류 발생: {e}", "error")