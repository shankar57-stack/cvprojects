import urllib.request
import os

proto_url = "https://raw.githubusercontent.com/CMU-Perceptual-Computing-Lab/openpose/master/models/pose/coco/pose_deploy_linevec.prototxt"
weights_url = "https://huggingface.co/camenduru/openpose/resolve/main/models/pose/coco/pose_iter_440000.caffemodel"

proto_file = "pose_deploy_linevec.prototxt"
weights_file = "pose_iter_440000.caffemodel"

def download_file(url, filename):
    print(f"Downloading {filename}...")
    try:
        # Create a request with a User-Agent header, sometimes HuggingFace blocks empty user agents
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response, open(filename, 'wb') as out_file:
            data = response.read()
            out_file.write(data)
        print(f"Successfully downloaded {filename}")
    except Exception as e:
        print(f"Failed to download {filename}: {e}")

if not os.path.exists(proto_file):
    download_file(proto_url, proto_file)
else:
    print(f"{proto_file} already exists.")

if not os.path.exists(weights_file):
    download_file(weights_url, weights_file)
else:
    print(f"{weights_file} already exists.")
