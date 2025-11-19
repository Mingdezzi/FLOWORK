import os
import asyncio
import aiohttp
import io
import random
import traceback
import json
from PIL import Image, ImageDraw, ImageFont
from flask import current_app
from flowork.extensions import db
from flowork.models import Product, Setting, Brand
from flowork.services.drive import get_drive_service, get_or_create_folder, upload_file_to_drive

RESAMPLE_LANCZOS = Image.Resampling.LANCZOS

def process_style_code_group(brand_id, style_code):
    """품번 그룹별 이미지 처리 메인 로직"""
    products = []
    try:
        # 0. 상품 조회
        products = Product.query.filter_by(brand_id=brand_id).filter(
            Product.product_number.like(f"{style_code}%")
        ).all()
        
        if not products:
            return False, "해당 품번의 상품이 없습니다."

        # 1. 구글 드라이브 설정 로드 및 연결
        drive_settings = _get_google_drive_settings(brand_id)
        if not drive_settings:
            msg = "구글 드라이브 설정을 찾을 수 없습니다. (DB 또는 JSON 파일 확인 필요)"
            _update_product_status(products, 'FAILED', msg)
            return False, msg

        key_filename = drive_settings.get('SERVICE_ACCOUNT_FILE')
        if not key_filename:
            msg = "설정에 'SERVICE_ACCOUNT_FILE' 항목이 누락되었습니다."
            _update_product_status(products, 'FAILED', msg)
            return False, msg
        
        drive_service = get_drive_service(key_filename)
        if not drive_service:
            msg = f"Google Drive 연결 실패. Secret File '{key_filename}'이(가) Render에 업로드되어 있는지 확인하세요."
            _update_product_status(products, 'FAILED', msg)
            return False, msg

        # 2. 컬러별 옵션 그룹화
        variants_map = {}
        for p in products:
            # DB의 Variant 테이블에서 컬러 정보를 조회
            color_name = "UnknownColor"
            if p.variants and len(p.variants) > 0:
                color_name = p.variants[0].color or "UnknownColor"
            
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

        # 3. 임시 폴더 생성
        temp_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'temp_images', style_code)
        os.makedirs(temp_dir, exist_ok=True)

        # 4. 이미지 다운로드 (비동기)
        patterns_config = _get_brand_url_patterns(brand_id)
        if not patterns_config:
             msg = "이미지 다운로드 URL 패턴 설정이 없습니다."
             _update_product_status(products, 'FAILED', msg)
             return False, msg

        asyncio.run(_download_all_variants(style_code, variants_map, patterns_config, temp_dir))

        # 5. 배경 제거
        valid_variants = []
        for color_name, data in variants_map.items():
            # DF 이미지가 있으면 배경제거 시도
            if data['files']['DF']:
                rep_image_path = data['files']['DF'][0]
                nobg_path = _remove_background(rep_image_path)
                if nobg_path:
                    data['files']['NOBG'] = nobg_path
                    valid_variants.append(data)
            
            # 모델컷(DM)만 있는 경우도 유효한 데이터로 간주할지 결정 (현재는 DF 우선)
            elif data['files']['DM']:
                 valid_variants.append(data)

        if not valid_variants:
            msg = "유효한 이미지를 하나도 다운로드하지 못했습니다. (URL 패턴 또는 품번 확인)"
            _update_product_status(products, 'FAILED', msg)
            return False, msg

        # 6. 썸네일 및 상세 이미지 생성
        thumbnail_path = _create_thumbnail(valid_variants, temp_dir, style_code)
        detail_path = _create_detail_image(valid_variants, temp_dir, style_code)

        # 7. 구글 드라이브 업로드
        try:
            result_links = _upload_structure_to_drive(
                drive_service, drive_settings, style_code, variants_map, thumbnail_path, detail_path
            )
        except Exception as upload_err:
            msg = f"구글 드라이브 업로드 중 오류: {upload_err}"
            _update_product_status(products, 'FAILED', msg)
            return False, msg

        # 8. 성공 처리 (DB 업데이트)
        _update_product_db(products, result_links)
        
        return True, f"성공: {len(valid_variants)}개 컬러 처리 완료"

    except Exception as e:
        err_msg = f"시스템 오류: {str(e)}\n{traceback.format_exc()}"
        print(f"Image processing fatal error: {err_msg}")
        if products:
            _update_product_status(products, 'FAILED', err_msg)
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
        for p in products:
            p.image_status = 'COMPLETED'
            p.last_message = '처리 완료'
            
            if 'thumbnail' in links:
                p.thumbnail_url = links['thumbnail']
            if 'detail' in links:
                p.detail_image_url = links['detail']
            
            my_color = "UnknownColor"
            if p.variants: my_color = p.variants[0].color or "UnknownColor"
            
            if my_color in links.get('drive_folders', {}):
                p.image_drive_link = links['drive_folders'][my_color]

        db.session.commit()
    except:
        db.session.rollback()

def _load_brand_config_from_file(brand_id):
    """브랜드 JSON 파일 직접 로드 (DB 설정 없을 때 Fallback)"""
    try:
        brand = db.session.get(Brand, brand_id)
        if not brand: return None
        
        # brands 폴더에서 파일 찾기
        json_path = os.path.join(current_app.root_path, 'brands', f'{brand.brand_name}.json')
        if os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Config load error for brand {brand_id}: {e}")
    return None

def _get_brand_url_patterns(brand_id):
    # 1. DB 확인
    setting = Setting.query.filter_by(brand_id=brand_id, key='IMAGE_DOWNLOAD_PATTERNS').first()
    if setting and setting.value:
        try:
            return json.loads(setting.value)
        except:
            pass
            
    # 2. 파일 확인 (Fallback)
    config = _load_brand_config_from_file(brand_id)
    if config:
        return config.get('IMAGE_DOWNLOAD_PATTERNS', {})
        
    return {}

def _get_google_drive_settings(brand_id):
    # 1. DB 확인
    setting = Setting.query.filter_by(brand_id=brand_id, key='GOOGLE_DRIVE_SETTINGS').first()
    if setting and setting.value:
        try:
            return json.loads(setting.value)
        except:
            pass
            
    # 2. 파일 확인 (Fallback)
    config = _load_brand_config_from_file(brand_id)
    if config:
        return config.get('GOOGLE_DRIVE_SETTINGS', {})
        
    return {}

async def _download_all_variants(style_code, variants_map, patterns_config, save_dir):
    connector = aiohttp.TCPConnector(limit=10)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = []
        
        year = ""
        if len(style_code) >= 5 and style_code[3:5].isdigit():
            year = "20" + style_code[3:5]

        for color_name, data in variants_map.items():
            full_code = data['product'].product_number 
            
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
    
    while True:
        found_any_pattern = False
        
        # 01, 1, 001 포맷 시도
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
            if consecutive_failures >= 1: 
                break

def _remove_background(input_path):
    try:
        # Lazy Import
        from rembg import remove
        
        name, ext = os.path.splitext(input_path)
        output_path = f"{name}_nobg.png"
        
        model_home = os.path.join(current_app.config['UPLOAD_FOLDER'], 'models')
        os.environ['U2NET_HOME'] = model_home
        os.makedirs(model_home, exist_ok=True)

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

def _upload_structure_to_drive(service, settings, style_code, variants_map, thumb_path, detail_path):
    root_id = settings.get('TARGET_FOLDER_ID')
    
    product_folder_id = get_or_create_folder(service, style_code, root_id)
    
    result = {'drive_folders': {}, 'thumbnail': None, 'detail': None}

    if thumb_path:
        thumb_folder_id = get_or_create_folder(service, 'THUMBNAIL', product_folder_id)
        link = upload_file_to_drive(service, thumb_path, f"{style_code}_thumb.png", thumb_folder_id)
        result['thumbnail'] = link
        
    if detail_path:
        detail_folder_id = get_or_create_folder(service, 'DETAILCOLOR', product_folder_id)
        link = upload_file_to_drive(service, detail_path, f"{style_code}_detail.png", detail_folder_id)
        result['detail'] = link

    for color_name, data in variants_map.items():
        color_folder_id = get_or_create_folder(service, color_name, product_folder_id)
        result['drive_folders'][color_name] = f"https://drive.google.com/drive/folders/{color_folder_id}"
        
        original_folder_id = get_or_create_folder(service, 'ORIGINAL', color_folder_id)
        nobg_folder_id = get_or_create_folder(service, 'NOBG', color_folder_id)
        model_folder_id = get_or_create_folder(service, 'MODEL', color_folder_id)

        for path in data['files']['DF']:
            upload_file_to_drive(service, path, os.path.basename(path), original_folder_id)
        
        for path in data['files']['DG']:
             pass 

        if data['files']['NOBG']:
            upload_file_to_drive(service, data['files']['NOBG'], os.path.basename(data['files']['NOBG']), nobg_folder_id)
            
        for path in data['files']['DM']:
            upload_file_to_drive(service, path, os.path.basename(path), model_folder_id)

    return result
