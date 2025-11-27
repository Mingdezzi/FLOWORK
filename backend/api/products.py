from flask import Blueprint, request, jsonify
from backend.models import Product, Variant, Stock, db
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.models import User

product_bp = Blueprint('products', __name__)

@product_bp.route('', methods=['GET'])
@jwt_required()
def get_products():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    query_str = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    
    # 기본 쿼리: 해당 브랜드 상품만
    base_query = Product.query.filter_by(brand_id=user.brand_id)
    
    if query_str:
        # 검색어 정리 (공백제거, 대문자)
        clean_q = query_str.replace(' ', '').upper()
        base_query = base_query.filter(
            (Product.search_code.contains(clean_q)) | 
            (Product.name.contains(query_str))
        )
    
    # 페이징
    pagination = base_query.paginate(page=page, per_page=20)
    
    results = []
    for p in pagination.items:
        # 대표 가격 및 총 재고 계산 (현재 접속한 매장 기준)
        variants_data = []
        total_stock = 0
        
        # Eager Loading 권장 (여기서는 로직 표현 위주)
        variants = Variant.query.filter_by(product_id=p.id).all()
        for v in variants:
            stock = Stock.query.filter_by(store_id=user.store_id, variant_id=v.id).first()
            qty = stock.quantity if stock else 0
            total_stock += qty
            
            variants_data.append({
                'id': v.id,
                'color': v.color,
                'size': v.size,
                'price': v.sale_price,
                'stock': qty
            })
            
        results.append({
            'id': p.id,
            'code': p.product_code,
            'name': p.name,
            'total_stock': total_stock,
            'price': variants_data[0]['price'] if variants_data else 0,
            'variants': variants_data
        })

    return jsonify({
        'items': results,
        'total': pagination.total,
        'pages': pagination.pages
    })