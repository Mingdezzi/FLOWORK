import os
import asyncio
import aiohttp
import io
import random
import math
from PIL import Image, ImageDraw, ImageFont
from rembg import remove
from flask import current_app
from sqlalchemy import or_
from flowork.extensions import db
from flowork.models import Product, Setting
from flowork.services.drive import get_drive_service, get_or_create_folder, upload_file_to_drive

RESAMPLE_LANCZOS = Image.Resampling.LANCZOS

def process_style_code_group(brand_id, style_code):
    try:
        drive_service = get_drive_service()
        if not drive_service:
            return False, "Google Drive 연결 실패"

        products = Product.query.filter_by(brand_id=brand_id).filter(
            Product.product_number.like(f"{style_code}%")
        ).all()
        
        if not products:
            return False, "해당 품번의 상품이 없습니다."

        variants_map = {}
        for p in products:
            color_code = ""
            if len(p.product_number) >= len(style_code) + 2:
                color_code = p.product_number[len(style_code):len(style_code)+2]
            
            if color_code and color_code not in variants_map:
                variants_map[color_code] = {
                    'product': p,
                    'color_code': color_code,
                    'images': {'original': None, 'nobg': None}
                }

        if not variants_map:
            return False, "처리할 컬러 옵션을 찾을 수 없습니다."

        temp_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'temp_images', style_code)
        os.makedirs(temp_dir, exist_ok=True)

        url_patterns = _get_brand_url_patterns(brand_id)
        
        asyncio.run(_download_images_async(style_code, variants_map, url_patterns, temp_dir))

        valid_variants = []
        for color_code, data in variants_map.items():
            if data['images']['original']:
                nobg_path = _remove_background(data['images']['original'])
                if nobg_path:
                    data['images']['nobg'] = nobg_path
                    valid_variants.append(data)

        if not valid_variants:
            return False, "이미지 다운로드 또는 배경 제거 실패"

        thumbnail_path = _create_thumbnail(valid_variants, temp_dir, style_code)
        detail_path = _create_detail_image(valid_variants, temp_dir, style_code)

        root_folder_id = _get_brand_drive_folder(drive_service, brand_id)
        style_folder_id = get_or_create_folder(drive_service, style_code, root_folder_id)

        result_links = {}
        
        if thumbnail_path:
            link = upload_file_to_drive(drive_service, thumbnail_path, f"{style_code}_thumb.png", style_folder_id)
            result_links['thumbnail'] = link
            
        if detail_path:
            link = upload_file_to_drive(drive_service, detail_path, f"{style_code}_detail.png", style_folder_id)
            result_links['detail'] = link

        _update_product_db(products, result_links)
        
        return True, f"성공: {len(valid_variants)}개 컬러 처리 완료"

    except Exception as e:
        print(f"Image processing error: {e}")
        return False, str(e)

def _get_brand_url_patterns(brand_id):
    setting = Setting.query.filter_by(brand_id=brand_id, key='IMAGE_URL_PATTERNS').first()
    if setting and setting.value:
        import json
        try:
            return json.loads(setting.value)
        except:
            pass
    
    return [
        "https://contents.k-village.co.kr/Prod/{year}/D/{code}/{code}_DF_01.jpg",
        "https://contents.k-village.co.kr/Prod/{year}/D/{code}/{code}_DM_01.jpg",
        "https://img.k-village.co.kr/product/{year}/{code}/{code}_DF_01.jpg"
    ]

def _get_brand_drive_folder(service, brand_id):
    folder_name = f"Brand_{brand_id}_Images"
    return get_or_create_folder(service, folder_name)

async def _download_images_async(style_code, variants_map, patterns, save_dir):
    async with aiohttp.ClientSession() as session:
        tasks = []
        for color_code, data in variants_map.items():
            full_code = f"{style_code}{color_code}"
            year = ""
            if len(style_code) >= 5 and style_code[3:5].isdigit():
                year = "20" + style_code[3:5]
                
            save_path = os.path.join(save_dir, f"{full_code}_org.jpg")
            tasks.append(_try_download(session, full_code, year, patterns, save_path, data))
        
        await asyncio.gather(*tasks)

async def _try_download(session, code, year, patterns, save_path, data_ref):
    for pattern in patterns:
        url = pattern.format(year=year, code=code)
        try:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    content = await response.read()
                    with open(save_path, 'wb') as f:
                        f.write(content)
                    data_ref['images']['original'] = save_path
                    return
        except:
            continue

def _remove_background(input_path):
    try:
        output_path = input_path.replace('_org.jpg', '_nobg.png')
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
            if v['images']['nobg']:
                img = Image.open(v['images']['nobg']).convert("RGBA")
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
            if not v['images']['nobg']: continue
            
            img = Image.open(v['images']['nobg']).convert("RGBA")
            
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

def _update_product_db(products, links):
    for p in products:
        p.image_status = 'COMPLETED'
        if 'thumbnail' in links:
            p.thumbnail_url = links['thumbnail']
        if 'detail' in links:
            p.detail_image_url = links['detail']
    db.session.commit()