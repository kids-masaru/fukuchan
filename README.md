# 福祉記録業務支援Webアプリ

Excelテンプレートに音声やテキストから自動転記するWebアプリケーションです。

## セットアップ手順

1. **環境変数の設定**
   `.env.example` を `.env` にコピーし、Gemini APIキーを設定してください。
   ```bash
   cp .env.example .env
   # .envファイルを開き、GENAI_API_KEY=... を設定
   ```

2. **依存ライブラリのインストール**
   ```bash
   pip install -r requirements.txt
   ```

3. **アプリの起動**
   ```bash
   python -m uvicorn main:app --reload
   ```

4. **利用開始**
   ブラウザで `http://localhost:8000` にアクセスしてください。

## 使い方

1. **Excelテンプレートのアップロード**: 記入したい様式のExcelファイル(.xlsx)を選択します。
2. **記録データの入力**:
   - **音声メモ**: 音声ファイル(.mp3, .wav等)をアップロードします。
   - **テキスト**: 記録内容を直接入力します。
3. **作成**: ボタンを押すとAIが内容を解析し、Excelに記入します。
4. **ダウンロード**: 完了するとダウンロードボタンが表示されます。

## Railwayへのデプロイ
このフォルダの内容をGitHubにプッシュし、Railwayでリポジトリを接続するだけでデプロイ可能です。
環境変数 `GEMINI_API_KEY` をRailwayの管理画面で設定してください。
