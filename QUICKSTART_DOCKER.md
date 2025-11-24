# ROCm Docker環境 クイックスタートガイド

このガイドでは、ROCm Docker環境でStyle-Bert-VITS2を推論直前までセットアップする手順を説明します。

## 前提条件

- ROCm 7.1 がインストールされたLinux環境（Ubuntu 24.04推奨）
- Dockerがインストールされていること
- `/dev/kfd` と `/dev/dri` デバイスへのアクセス権限

## セットアップ手順

### 1. Dockerイメージのビルド（初回のみ）

```bash
docker build -t style-bert-vits2-rocm:7.1 .
```

数分かかります。ベースイメージが大きいため、初回はダウンロードに時間がかかる場合があります。

### 2. モデルの初期化（推論用、初回のみ）

推論に必要なモデルをダウンロードします：

```bash
./init_docker.sh
```

このコマンドで以下のモデルがダウンロードされます：
- BERTモデル（日本語、中国語、英語用）
- デフォルト音声モデル（jvnv-F1/F2/M1/M2、koharune-ami、amitaro）
- 設定ファイル（`configs/paths.yml`）

ダウンロードには数分〜数十分かかる場合があります（モデルのサイズとネットワーク速度によります）。

### 3. 推論サーバーの起動

初期化が完了したら、推論サーバーを起動できます。

**方法1: docker-composeを使用（推奨）**

```bash
docker-compose up
```

**方法2: run_rocm_docker.shスクリプトを使用**

```bash
./run_rocm_docker.sh app.py
```

### 4. WebUIにアクセス

ブラウザで以下のURLにアクセス：

- **WebUI（全機能）**: http://localhost:7860
- **FastAPI（API）**: http://localhost:8000/docs

## 完全な手順（コピペ用）

```bash
# 1. Dockerイメージのビルド
docker build -t style-bert-vits2-rocm:7.1 .

# 2. モデルの初期化（推論用）
./init_docker.sh

# 3. 推論サーバーの起動
docker-compose up
# または
./run_rocm_docker.sh app.py
```

## 起動後の確認

WebUIが起動したら、以下を確認してください：

1. **モデルの読み込み**: 左側の「モデル選択」にダウンロードしたモデルが表示されること
2. **GPU認識**: ログに `device: cuda` と表示されること（ROCm環境でもこの表示になります）

## トラブルシューティング

### GPUが認識されない

```bash
# コンテナ内でGPU認識を確認
docker exec style-bert-vits2-rocm python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
```

### モデルが表示されない

- `model_assets/` ディレクトリにモデルファイルが存在するか確認
- 初期化スクリプトが正常に完了したか確認

### ポートが使用中

`docker-compose.yml` のポート番号を変更：

```yaml
ports:
  - "7861:7860"  # ホスト側のポートを変更
```

## 次のステップ

- [DOCKER_USAGE.md](DOCKER_USAGE.md): 詳細な使用方法とトラブルシューティング
- [README.md](README.md): プロジェクト全体のドキュメント
- [ROCm_Docker_DIFF.md](ROCm_Docker_DIFF.md): 変更内容の詳細

## よくある質問

**Q: 学習も行いたい場合は？**

A: `./init_docker.sh --full` を実行して、学習用モデルもダウンロードしてください。

**Q: デフォルトモデルは必要ない？**

A: 自分のモデルのみ使用する場合は `./init_docker.sh --skip-default` を実行してください。

**Q: コンテナを削除してもモデルは残る？**

A: はい、モデルはホストマシンの `model_assets/`, `bert/` ディレクトリに保存されるため、コンテナを削除しても残ります。

