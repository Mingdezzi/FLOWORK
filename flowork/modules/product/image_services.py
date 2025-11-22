import os
import asyncio
import aiohttp
import shutil
import json
from PIL import Image, ImageDraw, ImageFont, ImageStat
from flask import current_app
from flowork.extensions import db
from flowork.models import Product, Setting, Brand
from rembg import remove, new_session

RESAMPLE_LANCZOS = Image.Resampling.LANCZOS
_REMBG_SESSION = None

def _get_rembg_session():
    global _REMBG_SESSION
    if _REMBG_SESSION is None:
        model_name = "u2net"
        _REMBG_SESSION = new_session(model_name)
    return _REMBG_SESSION

def _hex_to_rgb(hex_value):
    hex_value = hex_value.lstrip('#')
    return tuple(int(hex_value[i:i+2], 16) for i in (0, 2, 4))

def process_style_code_group(brand_id, style_code, options=None):
    products = []
    try:
        if options is None: options = {}

        brand = db.session.get(Brand, brand_id)
        if not brand: return False, "브랜드 정보를 찾을 수 없습니다."
        brand_name = brand.brand_name

        products = Product.query.filter_by(brand_id=brand_id).filter(
            Product.product_number.like(f"{style_code}%")
        ).all()
        
        if not products: return False, "해당 품번의 상품이 없습니다."

        variants_map = {}
        for p in products:
            if not p.variants: continue
            unique_colors = set()
            for v in p.variants:
                if v.color: unique_colors.add(v.color)
            if not unique_colors: unique_colors.add("UnknownColor")

            for color_name in unique_colors:
                if color_name not in variants_map:
                    variants_map[color_name] = {
                        'product': p,
                        'color_code': color_name,
                        'files': { 'DF': [], 'DM': [], 'NOBG': None }
                    }
        
        if not variants_map:
            _update_product_status(products, 'FAILED', "처리할 컬러 옵션 없음")
            return False, "처리할 컬러 옵션을 찾을 수 없습니다."

        temp_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'temp_images', style_code)
        os.makedirs(temp_dir, exist_ok=True)

        patterns_config = _get_brand_url_patterns(brand_id)
        if not patterns_config:
             _update_product_status(products, 'FAILED', "URL 패턴 설정 없음")
             return False, "이미지 다운로드 URL 패턴 설정이 없습니다."

        asyncio.run(_download_all_variants(style_code, variants_map, patterns_config, temp_dir))

        valid_variants = []
        for color_name, data in variants_map.items():
            if data['files']['DF']:
                rep_image_path = data['files']['DF'][0]
                nobg_path = _remove_background(rep_image_path)
                if nobg_path:
                    data['files']['NOBG'] = nobg_path
                    valid_variants.append(data)
            elif data['files']['DM']:
                 valid_variants.append(data)

        if not valid_variants:
            _update_product_status(products, 'FAILED', "다운로드 실패")
            return False, "유효한 이미지를 하나도 다운로드하지 못했습니다."

        logo_path = os.path.join(current_app.root_path, 'static', 'thumbnail_logo.png')
        if not os.path.exists(logo_path): logo_path = None

        thumbnail_path = _create_thumbnail(valid_variants, temp_dir, style_code, logo_path=logo_path, options=options)
        detail_path = _create_detail_image(valid_variants, temp_dir, style_code, options=options)

        result_links = _save_structure_locally(brand_name, style_code, variants_map, thumbnail_path, detail_path)
        _update_product_db(products, result_links)
        
        try: shutil.rmtree(temp_dir)
        except: pass

        return True, f"성공: {len(valid_variants)}개 컬러 처리 완료"

    except Exception as e:
        if products: _update_product_status(products, 'FAILED', f"오류: {str(e)}")
        return False, f"오류 발생: {str(e)}"

def _update_product_status(products, status, message=None):
    try:
        for p in products:
            p.image_status = status
            if message: p.last_message = message
        db.session.commit()
    except: db.session.rollback()

def _update_product_db(products, links):
    try:
        updated_count = 0
        for p in products:
            db.session.refresh(p)
            if p.image_status != 'PROCESSING': continue
            p.image_status = 'COMPLETED'
            p.last_message = '처리 완료'
            if 'thumbnail' in links: p.thumbnail_url = links['thumbnail']
            if 'colordetail' in links: p.detail_image_url = links['colordetail']
            updated_count += 1
        if updated_count > 0: db.session.commit()
    except: db.session.rollback()

def _get_brand_url_patterns(brand_id):
    setting = Setting.query.filter_by(brand_id=brand_id, key='IMAGE_DOWNLOAD_PATTERNS').first()
    if setting and setting.value:
        try: return json.loads(setting.value)
        except: pass
    
    try:
        brand = db.session.get(Brand, brand_id)
        if brand:
            json_path = os.path.join(current_app.root_path, 'brands', f'{brand.brand_name}.json')
            if os.path.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as f:
                    return json.load(f).get('IMAGE_DOWNLOAD_PATTERNS', {})
    except: pass
    return {}

async def _download_all_variants(style_code, variants_map, patterns_config, save_dir):
    connector = aiohttp.TCPConnector(limit=10)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = []
        year = ""
        if len(style_code) >= 5 and style_code[3:5].isdigit():
            year = "20" + style_code[3:5]

        for color_name, data in variants_map.items():
            p_num = data['product'].product_number
            c_code = color_name.strip() if color_name and color_name != "UnknownColor" else ""
            full_code = f"{p_num}{c_code}"
            color_dir = os.path.join(save_dir, color_name)
            os.makedirs(color_dir, exist_ok=True)

            if 'DF' in patterns_config:
                tasks.append(_download_sequence(session, full_code, year, patterns_config['DF'], color_dir, 'DF', data))
            if 'DM' in patterns_config:
                tasks.append(_download_sequence(session, full_code, year, patterns_config['DM'], color_dir, 'DM', data))
            if 'DG' in patterns_config:
                tasks.append(_download_sequence(session, full_code, year, patterns_config['DG'], color_dir, 'DG', data))
        await asyncio.gather(*tasks)

async def _download_sequence(session, code, year, patterns, save_dir, img_type, data_ref):
    num = 1
    consecutive_failures = 0
    MAX_FAILURES = 5 
    while True:
        found_any = False
        for num_fmt in [f"{num:02d}", f"{num}", f"{num:03d}"]: 
            for pattern in patterns:
                url = pattern.format(year=year, code=code, num=num_fmt)
                try:
                    async with session.get(url, timeout=10) as response:
                        if response.status == 200:
                            content = await response.read()
                            ext = ".png" if url.lower().endswith(".png") else ".jpg"
                            filename = f"{code}_{img_type}_{num_fmt}{ext}"
                            save_path = os.path.join(save_dir, filename)
                            with open(save_path, 'wb') as f: f.write(content)
                            data_ref['files'][img_type].append(save_path)
                            found_any = True
                            break 
                except: continue
            if found_any: break
        if found_any:
            num += 1
            consecutive_failures = 0
        else:
            consecutive_failures += 1
            if consecutive_failures >= MAX_FAILURES: break
            num += 1

def _remove_background(input_path):
    try:
        name, _ = os.path.splitext(input_path)
        output_path = f"{name}_nobg.png"
        model_home = '/app/models'
        os.environ['U2NET_HOME'] = model_home
        os.makedirs(model_home, exist_ok=True)
        session = _get_rembg_session()
        with open(input_path, 'rb') as i:
            with open(output_path, 'wb') as o:
                o.write(remove(i.read(), session=session))
        return output_path
    except: return None

def _create_thumbnail(variants, temp_dir, style_code, logo_path=None, options=None):
    try:
        if options is None: options = {}
        canvas_w, canvas_h = 800, 800
        padding = int(options.get('padding', 10))
        direction = options.get('direction', 'SE')
        bg_color = _hex_to_rgb(options.get('bg_color', '#FFFFFF'))
        
        logo_h = 80 if logo_path else 0
        prod_area_h = canvas_h - logo_h
        
        layout = Image.new("RGBA", (canvas_w, canvas_h), (255,255,255,0))
        loaded = []
        for v in variants:
            if v['files']['NOBG']:
                img = Image.open(v['files']['NOBG']).convert("RGBA")
                bbox = img.getbbox()
                if bbox: img = img.crop(bbox)
                stat = ImageStat.Stat(img.convert('L'))
                loaded.append({'img': img, 'bright': stat.mean[0]})
        
        if not loaded: return None
        loaded.sort(key=lambda x: x['bright'], reverse=True)
        
        count = len(loaded)
        scale = 0.90 if count==1 else (0.80 if count==2 else 0.75)
        target_size = int(min(canvas_w, prod_area_h) * scale)
        
        resized = []
        for item in loaded:
            img = item['img']
            w, h = img.size
            if w > h:
                nw, nh = target_size, int(h * (target_size/w))
            else:
                nh, nw = target_size, int(w * (target_size/h))
            resized.append(img.resize((nw, nh), RESAMPLE_LANCZOS))
            
        fw, fh = resized[0].size
        min_x, max_x = padding, canvas_w - padding - fw
        min_y, max_y = logo_h + padding, logo_h + prod_area_h - padding - fh
        cx, cy = (canvas_w - fw)//2, logo_h + (prod_area_h - fh)//2
        
        if max_x < min_x: max_x = min_x = cx
        if max_y < min_y: max_y = min_y = cy
        
        sx, sy, ex, ey = cx, cy, cx, cy
        if count > 1:
            if direction == 'SE': sx, sy, ex, ey = min_x, min_y, max_x, max_y
            elif direction == 'SW': sx, sy, ex, ey = max_x, min_y, min_x, max_y
            elif direction == 'E': sx, sy, ex, ey = min_x, cy, max_x, cy
            elif direction == 'W': sx, sy, ex, ey = max_x, cy, min_x, cy
            
        step_x = (ex - sx) // (count - 1) if count > 1 else 0
        step_y = (ey - sy) // (count - 1) if count > 1 else 0
        
        for i, img in enumerate(resized):
            layout.alpha_composite(img, (int(sx + i*step_x), int(sy + i*step_y)))
            
        final = Image.new("RGB", (canvas_w, canvas_h), bg_color)
        final.paste(layout, (0,0), layout)
        
        if logo_path:
            logo = Image.open(logo_path).convert("RGBA")
            align = options.get('logo_align', 'left')
            ratio = (logo_h * 0.7) / logo.height
            lw, lh = int(logo.width * ratio), int(logo.height * ratio)
            logo = logo.resize((lw, lh), RESAMPLE_LANCZOS)
            lx = (canvas_w - lw)//2 if align=='center' else (canvas_w - lw - 20 if align=='right' else 20)
            final.paste(logo, (lx, (logo_h - lh)//2), logo)
            
        out = os.path.join(temp_dir, f"{style_code}_thumbnail.jpg")
        final.save(out, "JPEG", quality=95)
        return out
    except: return None

def _create_detail_image(variants, temp_dir, style_code, options=None):
    try:
        if options is None: options = {}
        bg_color = _hex_to_rgb(options.get('bg_color', '#FFFFFF'))
        cw = 800
        cell_w = cw // 2
        target_w = int(cell_w * 0.9)
        
        if not variants or not variants[0]['files']['NOBG']: return None
        
        sample = Image.open(variants[0]['files']['NOBG'])
        bbox = sample.getbbox()
        if bbox: sample = sample.crop(bbox)
        
        ratio = target_w / sample.width
        cell_h = int(sample.height * ratio) + 120
        rows = (len(variants) + 1) // 2
        
        layout = Image.new("RGBA", (cw, rows * cell_h), (255,255,255,0))
        draw = ImageDraw.Draw(layout)
        
        try: font = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf", 25)
        except: font = ImageFont.load_default()
        
        for i, v in enumerate(variants):
            if not v['files']['NOBG']: continue
            img = Image.open(v['files']['NOBG']).convert("RGBA")
            if img.getbbox(): img = img.crop(img.getbbox())
            
            nw, nh = int(img.width * ratio), int(img.height * ratio)
            img = img.resize((nw, nh), RESAMPLE_LANCZOS)
            
            row, col = i // 2, i % 2
            cx, cy = col * cell_w, row * cell_h
            
            layout.alpha_composite(img, (cx + (cell_w - nw)//2, cy + 20))
            
            text = f"#COLOR : {v['color_code']}"
            try: tw = draw.textbbox((0,0), text, font=font)[2]
            except: tw = len(text) * 10
            
            draw.text((cx + (cell_w - tw)//2, cy + nh + 35), text, fill="black", font=font)
            
        final = Image.new("RGB", (cw, rows * cell_h), bg_color)
        final.paste(layout, (0,0), layout)
        out = os.path.join(temp_dir, f"{style_code}_detail.jpg")
        final.save(out, "JPEG", quality=90)
        return out
    except: return None

def _save_structure_locally(brand_name, style_code, variants_map, thumb_path, detail_path):
    base = os.path.join(current_app.root_path, 'static', 'product_images', brand_name, style_code)
    for d in ['THUMBNAIL', 'COLORDETAIL', 'DETAIL']: os.makedirs(os.path.join(base, d), exist_ok=True)
    
    res = {}
    if thumb_path and os.path.exists(thumb_path):
        shutil.copy2(thumb_path, os.path.join(base, 'THUMBNAIL', f"{style_code}_thumb.jpg"))
        res['thumbnail'] = f"/static/product_images/{brand_name}/{style_code}/THUMBNAIL/{style_code}_thumb.jpg"
    if detail_path and os.path.exists(detail_path):
        shutil.copy2(detail_path, os.path.join(base, 'COLORDETAIL', f"{style_code}_colordetail.jpg"))
        res['colordetail'] = f"/static/product_images/{brand_name}/{style_code}/COLORDETAIL/{style_code}_colordetail.jpg"
        
    for color, data in variants_map.items():
        c_base = os.path.join(base, color)
        for sub in ['ORIGINAL', 'MODEL', 'NOBG']: os.makedirs(os.path.join(c_base, sub), exist_ok=True)
        
        for f in data['files']['DF']: shutil.copy2(f, os.path.join(c_base, 'ORIGINAL', os.path.basename(f)))
        for f in data['files']['DM']: shutil.copy2(f, os.path.join(c_base, 'MODEL', os.path.basename(f)))
        if data['files']['NOBG']: shutil.copy2(data['files']['NOBG'], os.path.join(c_base, 'NOBG', os.path.basename(data['files']['NOBG'])))
            
    return res