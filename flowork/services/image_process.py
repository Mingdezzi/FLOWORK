import os
import asyncio
import aiohttp
import shutil
import random
import traceback
import json
import statistics
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageStat
from flask import current_app
from flowork.extensions import db
from flowork.models import Product, Setting, Brand
from rembg import remove, new_session

RESAMPLE_LANCZOS = Image.Resampling.LANCZOS

_REMBG_SESSION = None

def _log(message):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ImageProcess] {message}")

def _get_rembg_session():
    global _REMBG_SESSION
    if _REMBG_SESSION is None:
        model_name = "u2net"
        _REMBG_SESSION = new_session(model_name)
    return _REMBG_SESSION

def process_style_code_group(brand_id, style_code):
    products = []
    try:
        brand = db.session.get(Brand, brand_id)
        if not brand:
            return False, "브랜드 정보를 찾을 수 없습니다."
        brand_name = brand.brand_name

        products = Product.query.filter_by(brand_id=brand_id).filter(
            Product.product_number.like(f"{style_code}%")
        ).all()
        
        if not products:
            return False, "해당 품번의 상품이 없습니다."

        variants_map = {}
        for p in products:
            if not p.variants:
                continue

            unique_colors = set()
            for v in p.variants:
                if v.color:
                    unique_colors.add(v.color)
            
            if not unique_colors:
                unique_colors.add("UnknownColor")

            for color_name in unique_colors:
                if color_name not in variants_map:
                    variants_map[color_name] = {
                        'product': p,
                        'color_code': color_name,
                        'files': {
                            'DF': [], 
                            'DM': [], 
                            'NOBG': None 
                        }
                    }
        
        if not variants_map:
            msg = "처리할 컬러 옵션을 찾을 수 없습니다."
            _update_product_status(products, 'FAILED', msg)
            return False, msg

        temp_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'temp_images', style_code)
        os.makedirs(temp_dir, exist_ok=True)

        patterns_config = _get_brand_url_patterns(brand_id)
        if not patterns_config:
             msg = "이미지 다운로드 URL 패턴 설정이 없습니다."
             _update_product_status(products, 'FAILED', msg)
             return False, msg

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
            msg = "유효한 이미지를 하나도 다운로드하지 못했습니다."
            _update_product_status(products, 'FAILED', msg)
            return False, msg

        logo_path = os.path.join(current_app.root_path, 'static', 'logo.png')
        if not os.path.exists(logo_path):
            logo_path = None

        thumbnail_path = _create_thumbnail(valid_variants, temp_dir, style_code, logo_path=logo_path)
        detail_path = _create_detail_image(valid_variants, temp_dir, style_code)

        result_links = _save_structure_locally(brand_name, style_code, variants_map, thumbnail_path, detail_path)

        _update_product_db(products, result_links)
        
        try:
            shutil.rmtree(temp_dir)
        except:
            pass

        return True, f"성공: {len(valid_variants)}개 컬러 처리 완료"

    except Exception as e:
        if products:
            _update_product_status(products, 'FAILED', f"오류 발생: {str(e)}")
        return False, f"오류 발생: {str(e)}"

def _update_product_status(products, status, message=None):
    try:
        for p in products:
            p.image_status = status
            if message:
                p.last_message = message
        db.session.commit()
    except:
        db.session.rollback()

def _update_product_db(products, links):
    try:
        updated_count = 0
        for p in products:
            db.session.refresh(p)
            if p.image_status != 'PROCESSING':
                continue

            p.image_status = 'COMPLETED'
            p.last_message = '처리 완료'
            
            if 'thumbnail' in links:
                p.thumbnail_url = links['thumbnail']
            if 'colordetail' in links:
                p.detail_image_url = links['colordetail']
            
            updated_count += 1

        if updated_count > 0:
            db.session.commit()
    except Exception as e:
        db.session.rollback()

def _load_brand_config_from_file(brand_id):
    try:
        brand = db.session.get(Brand, brand_id)
        if not brand: return None
        
        json_path = os.path.join(current_app.root_path, 'brands', f'{brand.brand_name}.json')
        if os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        pass
    return None

def _get_brand_url_patterns(brand_id):
    setting = Setting.query.filter_by(brand_id=brand_id, key='IMAGE_DOWNLOAD_PATTERNS').first()
    if setting and setting.value:
        try:
            return json.loads(setting.value)
        except:
            pass
    config = _load_brand_config_from_file(brand_id)
    if config:
        return config.get('IMAGE_DOWNLOAD_PATTERNS', {})
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
        found_any_pattern = False
        num_formats = [f"{num:02d}", f"{num}", f"{num:03d}"]
        for num_fmt in num_formats: 
            for pattern in patterns:
                url = pattern.format(year=year, code=code, num=num_fmt)
                try:
                    async with session.get(url, timeout=10) as response:
                        if response.status == 200:
                            content = await response.read()
                            ext = ".jpg"
                            if url.lower().endswith(".png"): ext = ".png"
                            elif url.endswith(".JPG"): ext = ".JPG"
                            
                            filename = f"{code}_{img_type}_{num_fmt}{ext}"
                            save_path = os.path.join(save_dir, filename)
                            
                            with open(save_path, 'wb') as f:
                                f.write(content)
                            
                            data_ref['files'][img_type].append(save_path)
                            found_any_pattern = True
                            break 
                except:
                    continue
            if found_any_pattern: break
        
        if found_any_pattern:
            num += 1
            consecutive_failures = 0
        else:
            consecutive_failures += 1
            if consecutive_failures >= MAX_FAILURES: 
                break
            num += 1

def _remove_background(input_path):
    try:
        name, ext = os.path.splitext(input_path)
        output_path = f"{name}_nobg.png"
        
        model_home = '/app/models'
        os.environ['U2NET_HOME'] = model_home
        os.makedirs(model_home, exist_ok=True)

        session = _get_rembg_session()

        with open(input_path, 'rb') as i:
            with open(output_path, 'wb') as o:
                input_data = i.read()
                output_data = remove(input_data, session=session)
                o.write(output_data)
        return output_path
    except Exception as e:
        return None

def _calculate_brightness(image):
    try:
        greyscale_image = image.convert('L')
        stat = ImageStat.Stat(greyscale_image)
        return stat.mean[0]
    except:
        return 0

def _trim_image(img):
    bbox = img.getbbox()
    if bbox:
        return img.crop(bbox)
    return img

def _paste_logo(final_image, logo_path, logo_config):
    try:
        logo = Image.open(logo_path).convert("RGBA")
        
        area_height = logo_config.get('height', 80)
        align = logo_config.get('align', 'left')
        
        max_logo_h = int(area_height * 0.7)
        
        ratio = max_logo_h / logo.height
        new_w = int(logo.width * ratio)
        new_h = int(logo.height * ratio)
        logo = logo.resize((new_w, new_h), RESAMPLE_LANCZOS)
        
        canvas_w = final_image.width
        
        margin_x = 20
        
        y = (area_height - new_h) // 2
        
        if align == 'center':
            x = (canvas_w - new_w) // 2
        elif align == 'right':
            x = canvas_w - new_w - margin_x
        else:
            x = margin_x
            
        final_image.paste(logo, (x, y), logo)
        
    except Exception as e:
        print(f"Logo paste error: {e}")

def _create_thumbnail(variants, temp_dir, style_code, bg_color=(255, 255, 255), logo_path=None):
    try:
        canvas_w = 800
        canvas_h = 800
        
        logo_config = {
            'height': 80,
            'align': 'left'
        }
        
        logo_area_h = logo_config['height'] if logo_path else 0
        
        prod_area_w = canvas_w
        prod_area_h = canvas_h - logo_area_h
        
        PADDING = 10 
        
        layout_layer = Image.new("RGBA", (canvas_w, canvas_h), (255, 255, 255, 0))
        
        loaded_images = []
        for v in variants:
            if v['files']['NOBG']:
                img = Image.open(v['files']['NOBG']).convert("RGBA")
                img = _trim_image(img)
                brightness = _calculate_brightness(img)
                loaded_images.append({'img': img, 'brightness': brightness})
        
        if not loaded_images: return None
        
        loaded_images.sort(key=lambda x: x['brightness'], reverse=True)
        
        count = len(loaded_images)
        
        if count == 1:
            scale = 0.90
        elif count == 2:
            scale = 0.80
        elif count == 3:
            scale = 0.75
        elif count == 4:
            scale = 0.70
        elif count == 5:
            scale = 0.65
        else:
            scale = 0.60
            
        target_max_size = int(min(prod_area_w, prod_area_h) * scale)
        
        resized_images = []
        for item in loaded_images:
            img = item['img']
            width, height = img.size
            
            if width > height:
                ratio = target_max_size / width
                new_w = target_max_size
                new_h = int(height * ratio)
            else:
                ratio = target_max_size / height
                new_h = target_max_size
                new_w = int(width * ratio)
                
            resized_images.append(img.resize((new_w, new_h), RESAMPLE_LANCZOS))
        
        first_w, first_h = resized_images[0].size
        
        offset_y = logo_area_h
        
        if count == 1:
            start_x = (prod_area_w - first_w) // 2
            start_y = offset_y + (prod_area_h - first_h) // 2
            step_x, step_y = 0, 0
        else:
            start_x = PADDING
            start_y = offset_y + PADDING
            
            max_x = prod_area_w - PADDING - first_w
            max_y = offset_y + prod_area_h - PADDING - first_h
            
            if max_x < start_x: 
                start_x = (prod_area_w - first_w) // 2
                max_x = start_x
            if max_y < start_y:
                start_y = offset_y + (prod_area_h - first_h) // 2
                max_y = start_y

            travel_x = max_x - start_x
            travel_y = max_y - start_y
            
            step_x = travel_x // (count - 1) if count > 1 else 0
            step_y = travel_y // (count - 1) if count > 1 else 0
                
        for idx, img in enumerate(resized_images):
            x = int(start_x + (idx * step_x))
            y = int(start_y + (idx * step_y))
            layout_layer.alpha_composite(img, (x, y))
            
        final_image = Image.new("RGB", (canvas_w, canvas_h), bg_color)
        
        final_image.paste(layout_layer, (0, 0), layout_layer)
        
        if logo_path:
            _paste_logo(final_image, logo_path, logo_config)
            
        output_path = os.path.join(temp_dir, f"{style_code}_thumbnail.jpg")
        final_image.save(output_path, "JPEG", quality=95)
        return output_path
        
    except Exception as e:
        traceback.print_exc()
        return None

def _create_detail_image(variants, temp_dir, style_code, bg_color=(255, 255, 255)):
    try:
        canvas_width = 800
        cell_width = canvas_width // 2
        target_img_width = int(cell_width * 0.9)
        text_area_height = 80
        
        if not variants or not variants[0]['files']['NOBG']: return None
        
        sample_img = Image.open(variants[0]['files']['NOBG'])
        sample_img = _trim_image(sample_img)
        
        ratio = target_img_width / sample_img.width
        target_img_height = int(sample_img.height * ratio)
        
        cell_height = target_img_height + text_area_height + 40
        
        count = len(variants)
        rows = (count + 1) // 2
        total_height = rows * cell_height
        
        layout_layer = Image.new("RGBA", (canvas_width, total_height), (255, 255, 255, 0))
        draw = ImageDraw.Draw(layout_layer)
        
        font = None
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf", 25)
        except:
            try:
                font = ImageFont.truetype("arial.ttf", 25)
            except:
                font = ImageFont.load_default()

        for idx, v in enumerate(variants):
            if not v['files']['NOBG']: continue
            
            img = Image.open(v['files']['NOBG']).convert("RGBA")
            img = _trim_image(img)
            
            w, h = img.size
            ratio = target_img_width / w
            new_w = int(w * ratio)
            new_h = int(h * ratio)
            resized = img.resize((new_w, new_h), RESAMPLE_LANCZOS)
            
            row = idx // 2
            col = idx % 2
            
            cell_x = col * cell_width
            cell_y = row * cell_height
            
            img_x = cell_x + (cell_width - new_w) // 2
            img_y = cell_y + 20
            
            layout_layer.alpha_composite(resized, (img_x, img_y))
            
            color_text = f"#COLOR : {v['color_code']}"
            
            try:
                bbox = draw.textbbox((0, 0), color_text, font=font)
                text_w = bbox[2] - bbox[0]
            except:
                text_w = len(color_text) * 10
            
            text_x = cell_x + (cell_width - text_w) // 2
            text_y = img_y + new_h + 15
            
            draw.text((text_x, text_y), color_text, fill="black", font=font)
            
        final_image = Image.new("RGB", (canvas_width, total_height), bg_color)
        final_image.paste(layout_layer, (0, 0), layout_layer)

        output_path = os.path.join(temp_dir, f"{style_code}_detail.jpg")
        final_image.save(output_path, "JPEG", quality=90)
        return output_path
        
    except Exception as e:
        traceback.print_exc()
        return None

def _save_structure_locally(brand_name, style_code, variants_map, thumb_path, detail_path):
    base_static_path = os.path.join(current_app.root_path, 'static', 'product_images')
    product_base_dir = os.path.join(base_static_path, brand_name, style_code)
    
    thumb_dir = os.path.join(product_base_dir, 'THUMBNAIL')
    colordetail_dir = os.path.join(product_base_dir, 'COLORDETAIL')
    detail_dir = os.path.join(product_base_dir, 'DETAIL')
    
    os.makedirs(thumb_dir, exist_ok=True)
    os.makedirs(colordetail_dir, exist_ok=True)
    os.makedirs(detail_dir, exist_ok=True)
    
    result = {'thumbnail': None, 'colordetail': None}

    if thumb_path and os.path.exists(thumb_path):
        dest_thumb = os.path.join(thumb_dir, f"{style_code}_thumb.jpg")
        shutil.copy2(thumb_path, dest_thumb)
        result['thumbnail'] = f"/static/product_images/{brand_name}/{style_code}/THUMBNAIL/{style_code}_thumb.jpg"
        
    if detail_path and os.path.exists(detail_path):
        dest_detail = os.path.join(colordetail_dir, f"{style_code}_colordetail.jpg")
        shutil.copy2(detail_path, dest_detail)
        result['colordetail'] = f"/static/product_images/{brand_name}/{style_code}/COLORDETAIL/{style_code}_colordetail.jpg"
        
    for color_name, data in variants_map.items():
        color_base_dir = os.path.join(product_base_dir, color_name)
        original_dir = os.path.join(color_base_dir, 'ORIGINAL')
        model_dir = os.path.join(color_base_dir, 'MODEL')
        nobg_dir = os.path.join(color_base_dir, 'NOBG')
        
        if data['files']['DF']:
            os.makedirs(original_dir, exist_ok=True)
            for path in data['files']['DF']:
                filename = os.path.basename(path)
                shutil.copy2(path, os.path.join(original_dir, filename))
        
        if data['files']['DM']:
            os.makedirs(model_dir, exist_ok=True)
            for path in data['files']['DM']:
                filename = os.path.basename(path)
                shutil.copy2(path, os.path.join(model_dir, filename))
            
        if data['files']['NOBG'] and os.path.exists(data['files']['NOBG']):
            os.makedirs(nobg_dir, exist_ok=True)
            filename = os.path.basename(data['files']['NOBG'])
            shutil.copy2(data['files']['NOBG'], os.path.join(nobg_dir, filename))

    return result
