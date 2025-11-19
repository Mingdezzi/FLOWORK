import os
import asyncio
import aiohttp
import io
import random
import traceback
from PIL import Image, ImageDraw, ImageFont
from rembg import remove
from flask import current_app
from flowork.extensions import db
from flowork.models import Product, Setting
from flowork.services.drive import get_drive_service, get_or_create_folder, upload_file_to_drive

RESAMPLE_LANCZOS = Image.Resampling.LANCZOS

def process_style_code_group(brand_id, style_code):
    products = []
    try:
        products = Product.query.filter_by(brand_id=brand_id).filter(
            Product.product_number.like(f"{style_code}%")
        ).all()
        
        if not products:
            return False, "해당 품번의 상품이 없습니다."

        drive_service = get_drive_service(products[0].brand.brand_name)
        if not drive_service:
            _update_product_status(products, 'FAILED')
            return False, "Google Drive 연결 실패 (인증 파일 확인 필요)"

        variants_map = {}
        for p in products:
            color_code = ""
            if len(p.product_number) >= len(style_code) + 2:
                color_code = p.product_number[len(style_code):len(style_code)+2]
            
            if color_code and color_code not in variants_map:
                variants_map[color_code] = {
                    'product': p,
                    'color_code': color_code,
                    'files': {
                        'DF': [], 
                        'DM': [], 
                        'NOBG': None 
                    }
                }

        if not variants_map:
            _update_product_status(products, 'FAILED')
            return False, "처리할 컬러 옵션을 찾을 수 없습니다."

        temp_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'temp_images', style_code)
        os.makedirs(temp_dir, exist_ok=True)

        patterns_config = _get_brand_url_patterns(brand_id)
        
        asyncio.run(_download_all_variants(style_code, variants_map, patterns_config, temp_dir))

        valid_variants = []
        for color_code, data in variants_map.items():
            if data['files']['DF']:
                rep_image_path = data['files']['DF'][0]
                nobg_path = _remove_background(rep_image_path)
                if nobg_path:
                    data['files']['NOBG'] = nobg_path
                    valid_variants.append(data)

        if not valid_variants:
            _update_product_status(products, 'FAILED')
            return False, "이미지 다운로드 실패 또는 배경 제거 실패"

        thumbnail_path = _create_thumbnail(valid_variants, temp_dir, style_code)
        detail_path = _create_detail_image(valid_variants, temp_dir, style_code)

        result_links = _upload_structure_to_drive(
            drive_service, brand_id, style_code, variants_map, thumbnail_path, detail_path
        )

        _update_product_db(products, result_links)
        
        return True, f"성공: {len(valid_variants)}개 컬러 처리 완료"

    except Exception as e:
        print(f"Image processing error: {e}")
        traceback.print_exc()
        if products:
            _update_product_status(products, 'FAILED')
        return False, f"오류 발생: {str(e)}"

def _update_product_status(products, status):
    try:
        for p in products:
            p.image_status = status
        db.session.commit()
    except:
        db.session.rollback()

def _update_product_db(products, links):
    try:
        for p in products:
            p.image_status = 'COMPLETED'
            if 'thumbnail' in links:
                p.thumbnail_url = links['thumbnail']
            if 'detail' in links:
                p.detail_image_url = links['detail']
            
            color_code = ""
            style_code_len = len(p.product_number) - 2
            if len(p.product_number) > style_code_len:
                color_code = p.product_number[style_code_len:]
            
            if color_code and color_code in links.get('drive_folders', {}):
                p.image_drive_link = links['drive_folders'][color_code]

        db.session.commit()
    except:
        db.session.rollback()

def _get_brand_url_patterns(brand_id):
    setting = Setting.query.filter_by(brand_id=brand_id, key='IMAGE_DOWNLOAD_PATTERNS').first()
    if setting and setting.value:
        import json
        try:
            return json.loads(setting.value)
        except:
            pass
    return {}

def _get_brand_root_folder_id(brand_id):
    setting = Setting.query.filter_by(brand_id=brand_id, key='GOOGLE_DRIVE_SETTINGS').first()
    if setting and setting.value:
        import json
        try:
            data = json.loads(setting.value)
            return data.get('TARGET_FOLDER_ID')
        except:
            pass
    return None

async def _download_all_variants(style_code, variants_map, patterns_config, save_dir):
    connector = aiohttp.TCPConnector(limit=10)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = []
        
        year = ""
        if len(style_code) >= 5 and style_code[3:5].isdigit():
            year = "20" + style_code[3:5]

        for color_code, data in variants_map.items():
            full_code = f"{style_code}{color_code}"
            color_dir = os.path.join(save_dir, color_code)
            os.makedirs(color_dir, exist_ok=True)

            if 'DF' in patterns_config:
                tasks.append(_download_sequence(session, full_code, year, patterns_config['DF'], color_dir, 'DF', data))
            
            if 'DM' in patterns_config:
                tasks.append(_download_sequence(session, full_code, year, patterns_config['DM'], color_dir, 'DM', data))
                
        await asyncio.gather(*tasks)

async def _download_sequence(session, code, year, patterns, save_dir, img_type, data_ref):
    num = 1
    consecutive_failures = 0
    
    while True:
        found_any_pattern = False
        
        for num_fmt in [f"{num:02d}", f"{num}"]: 
            for pattern in patterns:
                url = pattern.format(year=year, code=code, num=num_fmt)
                try:
                    async with session.get(url, timeout=10) as response:
                        if response.status == 200:
                            content = await response.read()
                            ext = ".jpg"
                            if url.lower().endswith(".png"): ext = ".png"
                            
                            filename = f"{code}_{img_type}_{num_fmt}{ext}"
                            save_path = os.path.join(save_dir, filename)
                            
                            with open(save_path, 'wb') as f:
                                f.write(content)
                            
                            data_ref['files'][img_type].append(save_path)
                            found_any_pattern = True
                            break 
                except:
                    continue
            
            if found_any_pattern:
                break

        if found_any_pattern:
            num += 1
            consecutive_failures = 0
        else:
            consecutive_failures += 1
            if consecutive_failures >= 1: 
                break

def _remove_background(input_path):
    try:
        output_path = input_path.replace(os.path.splitext(input_path)[1], '_nobg.png')
        with open(input_path, 'rb') as i:
            with open(output_path, 'wb') as o:
                input_data = i.read()
                output_data = remove(input_data)
                o.write(output_data)
        return output_path
    except Exception as e:
        print(f"Rembg error for {input_path}: {e}")
        return None

def _create_thumbnail(variants, temp_dir, style_code):
    try:
        canvas_size = 800
        canvas = Image.new("RGBA", (canvas_size, canvas_size), (255, 255, 255, 255))
        
        images = []
        for v in variants:
            if v['files']['NOBG']:
                img = Image.open(v['files']['NOBG']).convert("RGBA")
                images.append(img)
        
        if not images: return None

        count = len(images)
        grid_layout = _get_grid_layout(count)
        cell_size = canvas_size // 2 
        
        for idx, img in enumerate(images):
            if idx >= len(grid_layout): break
            
            row, col = grid_layout[idx]
            target_h = int(canvas_size * 0.55) 
            
            width, height = img.size
            ratio = target_h / height
            new_w = int(width * ratio)
            new_h = int(height * ratio)
            
            resized = img.resize((new_w, new_h), RESAMPLE_LANCZOS)
            
            cx = int(col * cell_size + cell_size / 2)
            cy = int(row * cell_size + cell_size / 2)
            
            x = cx - new_w // 2
            y = cy - new_h // 2
            
            jitter_x = random.randint(-10, 10)
            jitter_y = random.randint(-10, 10)
            
            canvas.alpha_composite(resized, (x + jitter_x, y + jitter_y))
            
        output_path = os.path.join(temp_dir, f"{style_code}_thumbnail.png")
        canvas.save(output_path)
        return output_path
    except Exception as e:
        print(f"Thumbnail creation error: {e}")
        return None

def _get_grid_layout(count):
    if count == 1: return [(0.5, 0.5)] 
    if count == 2: return [(0.5, 0), (0.5, 1)]
    if count == 3: return [(0, 0.5), (1, 0), (1, 1)]
    if count == 4: return [(0, 0), (0, 1), (1, 0), (1, 1)]
    
    layout = []
    for r in range(2):
        for c in range(2):
            layout.append((r, c))
    return layout

def _create_detail_image(variants, temp_dir, style_code):
    try:
        width = 800
        item_height = 800
        total_height = item_height * len(variants)
        
        canvas = Image.new("RGBA", (width, total_height), (255, 255, 255, 255))
        draw = ImageDraw.Draw(canvas)
        
        try:
            font = ImageFont.truetype("arial.ttf", 40)
        except:
            font = ImageFont.load_default()

        for idx, v in enumerate(variants):
            if not v['files']['NOBG']: continue
            
            img = Image.open(v['files']['NOBG']).convert("RGBA")
            w, h = img.size
            ratio = (item_height - 100) / h
            new_w = int(w * ratio)
            new_h = int(h * ratio)
            resized = img.resize((new_w, new_h), RESAMPLE_LANCZOS)
            
            y_offset = idx * item_height
            x_pos = (width - new_w) // 2
            y_pos = y_offset + 50
            
            canvas.alpha_composite(resized, (x_pos, y_pos))
            
            text = f"COLOR: {v['color_code']}"
            bbox = draw.textbbox((0, 0), text, font=font)
            text_w = bbox[2] - bbox[0]
            
            draw.text(((width - text_w) // 2, y_offset + item_height - 60), text, fill="black", font=font)
            
        output_path = os.path.join(temp_dir, f"{style_code}_detail.png")
        canvas.save(output_path)
        return output_path
    except Exception as e:
        print(f"Detail image creation error: {e}")
        return None

def _upload_structure_to_drive(service, brand_id, style_code, variants_map, thumb_path, detail_path):
    root_id = _get_brand_root_folder_id(brand_id)
    
    product_folder_id = get_or_create_folder(service, style_code, root_id)
    
    thumb_folder_id = get_or_create_folder(service, 'THUMBNAIL', product_folder_id)
    detail_folder_id = get_or_create_folder(service, 'DETAILCOLOR', product_folder_id)
    
    result = {'drive_folders': {}, 'thumbnail': None, 'detail': None}

    if thumb_path:
        link = upload_file_to_drive(service, thumb_path, f"{style_code}_thumb.png", thumb_folder_id)
        result['thumbnail'] = link
        
    if detail_path:
        link = upload_file_to_drive(service, detail_path, f"{style_code}_detail.png", detail_folder_id)
        result['detail'] = link

    for color_code, data in variants_map.items():
        color_folder_id = get_or_create_folder(service, color_code, product_folder_id)
        result['drive_folders'][color_code] = f"https://drive.google.com/drive/folders/{color_folder_id}"
        
        original_folder_id = get_or_create_folder(service, 'ORIGINAL', color_folder_id)
        nobg_folder_id = get_or_create_folder(service, 'NOBG', color_folder_id)
        model_folder_id = get_or_create_folder(service, 'MODEL', color_folder_id)

        for path in data['files']['DF']:
            upload_file_to_drive(service, path, os.path.basename(path), original_folder_id)
            
        if data['files']['NOBG']:
            upload_file_to_drive(service, data['files']['NOBG'], os.path.basename(data['files']['NOBG']), nobg_folder_id)
            
        for path in data['files']['DM']:
            upload_file_to_drive(service, path, os.path.basename(path), model_folder_id)

    return result