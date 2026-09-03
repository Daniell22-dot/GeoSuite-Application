"""Download datasets for CV training."""
import urllib.request
import json
import os
import sys
import zipfile
import time

DATASETS_DIR = r"D:\Geospatial_suite\DATASETS"

def download_with_progress(url, output_path, label="file"):
    """Download a file with progress reporting."""
    print(f"Downloading {label}...")
    print(f"  URL: {url[:80]}...")
    
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (GeoSuite-CV)"})
    resp = urllib.request.urlopen(req, timeout=30)
    total = int(resp.headers.get("Content-Length", 0))
    
    downloaded = 0
    start = time.time()
    with open(output_path, "wb") as f:
        while True:
            chunk = resp.read(1024 * 1024)  # 1MB chunks
            if not chunk:
                break
            f.write(chunk)
            downloaded += len(chunk)
            elapsed = time.time() - start
            speed = downloaded / elapsed / 1024 / 1024 if elapsed > 0 else 0
            pct = (downloaded / total * 100) if total else 0
            print(f"\r  {downloaded // 1024 // 1024}MB / {total // 1024 // 1024}MB ({pct:.1f}%) - {speed:.1f} MB/s", end="", flush=True)
    
    print(f"\n  Done: {downloaded // 1024 // 1024}MB in {time.time()-start:.1f}s")
    return output_path


def download_eurosat():
    """Download EuroSAT RGB from Zenodo."""
    print("\n" + "=" * 60)
    print("EUROSAT RGB DATASET")
    print("  27,000 Sentinel-2 satellite images, 10 land-use classes")
    print("  64x64 pixels, RGB")
    print("=" * 60)
    
    zip_path = os.path.join(DATASETS_DIR, "EuroSAT_RGB.zip")
    extract_dir = os.path.join(DATASETS_DIR, "EuroSAT")
    
    # Check if already extracted
    if os.path.isdir(extract_dir) and len(os.listdir(extract_dir)) >= 10:
        print("  Already downloaded and extracted!")
        return True
    
    # Try Zenodo API
    try:
        print("\n  Fetching Zenodo record...")
        req = urllib.request.Request(
            "https://zenodo.org/api/records/7711810",
            headers={"User-Agent": "Mozilla/5.0"}
        )
        resp = urllib.request.urlopen(req, timeout=30)
        data = json.loads(resp.read())
        
        # Find RGB zip (the smaller one, typically ~2.3GB)
        rgb_file = None
        for f in data["files"]:
            if "RGB" in f["key"]:
                rgb_file = f
                break
        
        if not rgb_file:
            print("  Could not find EuroSAT_RGB.zip in Zenodo files")
            return False
        
        download_url = rgb_file["links"]["self"]
        size_mb = rgb_file["size"] // 1024 // 1024
        print(f"  Found: {rgb_file['key']} ({size_mb} MB)")
        
        download_with_progress(download_url, zip_path, f"EuroSAT RGB ({size_mb}MB)")
        
        # Extract
        print("  Extracting...")
        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(DATASETS_DIR)
        
        # Verify
        if os.path.isdir(extract_dir):
            classes = os.listdir(extract_dir)
            total = sum(len(os.listdir(os.path.join(extract_dir, c))) for c in classes if os.path.isdir(os.path.join(extract_dir, c)))
            print(f"  Extracted {len(classes)} classes, {total} images")
            # Cleanup zip
            os.remove(zip_path)
            return True
        
    except Exception as e:
        print(f"  Zenodo download failed: {e}")
    
    # Fallback: try DFKI
    try:
        print("\n  Trying DFKI hosting...")
        download_with_progress(
            "https://madm.dfki.de/files/sentinel/EuroSAT.zip",
            zip_path,
            "EuroSAT from DFKI"
        )
        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(DATASETS_DIR)
        os.remove(zip_path)
        return True
    except Exception as e:
        print(f"  DFKI download failed: {e}")
    
    return False


def download_deepglobe():
    """Download DeepGlobe Road Extraction dataset via Kaggle."""
    print("\n" + "=" * 60)
    print("DEEPGLOBE ROAD EXTRACTION DATASET")
    print("  6,226 satellite images with road masks")
    print("  1024x1024 pixels, 50cm resolution")
    print("=" * 60)
    
    extract_dir = os.path.join(DATASETS_DIR, "DeepGlobe")
    if os.path.isdir(extract_dir):
        print("  Already downloaded!")
        return True
    
    # Check for Kaggle API key
    kaggle_dir = os.path.expanduser("~/.kaggle")
    kaggle_json = os.path.join(kaggle_dir, "kaggle.json")
    
    if not os.path.exists(kaggle_json):
        print("\n  Kaggle API key not found!")
        print("  To download DeepGlobe dataset:")
        print("    1. Go to https://www.kaggle.com/settings")
        print("    2. Create API token (downloads kaggle.json)")
        print(f"    3. Place it in: {kaggle_json}")
        print("    4. Then run: kaggle datasets download -d balraj98/deepglobe-road-extraction-dataset -p", DATASETS_DIR)
        return False
    
    try:
        import subprocess
        result = subprocess.run(
            ["python", "-m", "kaggle", "datasets", "download",
             "-d", "balraj98/deepglobe-road-extraction-dataset",
             "-p", DATASETS_DIR, "--unzip"],
            capture_output=True, text=True, timeout=600
        )
        if result.returncode == 0:
            print("  Downloaded and extracted!")
            return True
        else:
            print(f"  Kaggle error: {result.stderr}")
            return False
    except Exception as e:
        print(f"  Kaggle download failed: {e}")
        return False


if __name__ == "__main__":
    os.makedirs(DATASETS_DIR, exist_ok=True)
    
    eurosat_ok = download_eurosat()
    deepglobe_ok = download_deepglobe()
    
    print("\n" + "=" * 60)
    print("DOWNLOAD SUMMARY")
    print("=" * 60)
    print(f"  EuroSAT:    {'OK' if eurosat_ok else 'FAILED'}")
    print(f"  DeepGlobe:  {'OK' if deepglobe_ok else 'NEEDS KAGGLE KEY'}")
    print(f"  ANGOROM:    Already in RAW DATA (9 survey plans)")
    print(f"  Landsat 8:  Already in RAW DATA (incomplete - angle bands only)")
    print(f"  Bathymetric: Already in RAW DATA (GEBCO Kenya coast)")
    print(f"  WorldCover:  Already in RAW DATA (459MB)")
