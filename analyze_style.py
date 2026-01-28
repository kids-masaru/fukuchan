import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv(dotenv_path=r"C:\Users\HP\OneDrive\ドキュメント\yamasaki\welfare_record_app\.env")
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

image_paths = [
    r"C:/Users/HP/.gemini/antigravity/brain/41fa0418-41f8-4e26-8ff3-25025d74fd8a/uploaded_image_0_1769003475067.png",
    r"C:/Users/HP/.gemini/antigravity/brain/41fa0418-41f8-4e26-8ff3-25025d74fd8a/uploaded_image_1_1769003475067.png",
    r"C:/Users/HP/.gemini/antigravity/brain/41fa0418-41f8-4e26-8ff3-25025d74fd8a/uploaded_image_2_1769003475067.png",
    r"C:/Users/HP/.gemini/antigravity/brain/41fa0418-41f8-4e26-8ff3-25025d74fd8a/uploaded_image_3_1769003475067.png"
]

model = genai.GenerativeModel('gemini-1.5-flash')

prompt = """
これらの画像は「ケース会議議事録」の記入例です。
以下の点を分析して要約してください。プロンプトの指示として使える形式で出力してください。

1. 文体の特徴（「です・ます」調か、「だ・である」調か、箇条書きなど）
2. 「検討内容と結果」の書き方のパターン（「本人：〜」「・〜」など）
3. 具体的な言い回しの特徴
"""

parts = [prompt]
for path in image_paths:
    if os.path.exists(path):
        parts.append(genai.upload_file(path))
    else:
        print(f"Skipping missing file: {path}")

response = model.generate_content(parts)
print(response.text)
