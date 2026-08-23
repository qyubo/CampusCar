#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
下载RDD2020真实路面缺陷图片用于测试
"""
import sys
import io
import urllib.request
from pathlib import Path

# 修复Windows控制台编码
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def download_sample_image():
    """从GitHub下载真实路面缺陷图片"""
    output_dir = Path('real_samples')
    output_dir.mkdir(exist_ok=True)
    
    # 使用RDD2020数据集中的真实图片（GitHub公开链接）
    sample_urls = {
        'real_crack.jpg': 'https://raw.githubusercontent.com/sekilab/RoadDamageDetector/master/RDD2020/dataset/train/Japan/images/Japan_000002.jpg',
        'real_pothole.jpg': 'https://raw.githubusercontent.com/sekilab/RoadDamageDetector/master/RDD2020/dataset/train/Japan/images/Japan_000005.jpg',
    }
    
    downloaded = []
    for filename, url in sample_urls.items():
        filepath = output_dir / filename
        if filepath.exists():
            print(f"✅ 已存在: {filepath}")
            downloaded.append(str(filepath))
            continue
            
        try:
            print(f"📥 正在下载: {filename}")
            print(f"   URL: {url}")
            urllib.request.urlretrieve(url, filepath)
            downloaded.append(str(filepath))
            print(f"✅ 下载成功: {filepath}")
        except Exception as e:
            print(f"⚠️  下载失败: {e}")
            print("尝试备用链接...")
            
            # 备用：使用其他公开数据源
            alt_url = f"https://github.com/sekilab/RoadDamageDetector/raw/master/data_sample/Japan/images/{filename}"
            try:
                urllib.request.urlretrieve(alt_url, filepath)
                downloaded.append(str(filepath))
                print(f"✅ 备用下载成功: {filepath}")
            except Exception as e2:
                print(f"❌ 备用也失败: {e2}")
    
    if downloaded:
        print(f"\n✅ 成功下载 {len(downloaded)} 张真实路面图片")
        print(f"保存位置: {output_dir}/")
        return downloaded[0] if downloaded else None
    else:
        print("\n⚠️  所有下载失败，将使用本地测试图片")
        return None

if __name__ == '__main__':
    download_sample_image()
