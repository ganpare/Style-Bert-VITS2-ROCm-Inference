# ROCm Docker環境 使用方法

このドキュメントは、ROCm 7.1環境でStyle-Bert-VITS2をDockerコンテナとして実行する方法を詳しく説明します。

## 目次

1. [前提条件](#前提条件)
2. [Dockerイメージのビルド](#dockerイメージのビルド)
3. [実行方法](#実行方法)
4. [オプショナル依存関係のインストール](#オプショナル依存関係のインストール)
5. [トラブルシューティング](#トラブルシューティング)

## 前提条件

- **OS**: Ubuntu 24.04 LTS（推奨）またはROCm 7.1が動作するLinux環境
- **ROCm**: ROCm 7.1がインストールされ、正常に動作していること
- **Docker**: Dockerがインストールされ、Dockerグループにユーザーが追加されていること
- **デバイスアクセス**: `/dev/kfd` と `/dev/dri` デバイスへのアクセス権限

### ROCm環境の確認

```bash
# ROCmデバイスの確認
rocminfo | grep -E "(gfx|Marketing)"

# GPU情報の確認
rocm-smi
```

### Dockerのセットアップ

```bash
# Dockerグループにユーザーを追加（再ログインが必要）
sudo usermod -aG docker $USER

# render, videoグループにも追加（ROCmアクセス用）
sudo usermod -aG render,video $USER
```

## Dockerイメージのビルド

初回のみ、またはDockerfileを変更した場合に実行します。

```bash
docker build -t style-bert-vits2-rocm:7.1 .
```

ビルドには数分かかります。ベースイメージ（`rocm/pytorch:rocm7.1_ubuntu24.04_py3.12_pytorch_release_2.8.0`）が大きいため、初回はダウンロードに時間がかかる場合があります。

## モデルの初期化

**推論のみを行う場合（推奨）:**

推論に必要な最小限のモデルをダウンロードします（約数GB）：

```bash
./init_docker.sh
```

このコマンドで以下のモデルがダウンロードされます：
- BERTモデル（日本語、中国語、英語用）
- デフォルト音声モデル（jvnv-F1/F2/M1/M2、koharune-ami、amitaro）
- 設定ファイル（`configs/paths.yml`）

**学習も行う場合:**

学習に必要な追加モデルも含めてダウンロードします（約数十GB）：

```bash
./init_docker.sh --full
```

追加でダウンロードされるモデル：
- SLMモデル（wavlm-base-plus）
- 事前学習済みモデル（Style-Bert-VITS2-1.0-base、2.0-base-JP-Extra）

**オプション:**

```bash
# デフォルトモデルをスキップ（自分のモデルのみ使用する場合）
./init_docker.sh --skip-default
```

## 実行方法

### 方法1: docker-composeを使用（推奨）

最も簡単な方法です。

```bash
# バックグラウンドで起動
docker-compose up -d

# ログを確認
docker-compose logs -f

# 停止
docker-compose down
```

デフォルトで `app.py` が起動し、`http://localhost:7860` でWebUIにアクセスできます。

**別のスクリプトを実行する場合:**

`docker-compose.yml` の `command` を変更するか、環境変数で上書きできます：

```bash
docker-compose run --rm style-bert-vits2-rocm python server_editor.py
docker-compose run --rm style-bert-vits2-rocm python server_fastapi.py
```

### 方法2: run_rocm_docker.shスクリプトを使用

シェルスクリプトを使った実行方法です。

```bash
# WebUI（app.py）を起動
./run_rocm_docker.sh app.py

# エディターサーバーを起動
./run_rocm_docker.sh server_editor.py --inbrowser

# FastAPIサーバーを起動
./run_rocm_docker.sh server_fastapi.py

# 引数付きで起動
./run_rocm_docker.sh app.py --device cuda --port 7860
```

### 方法3: docker runを直接使用

より細かい制御が必要な場合：

```bash
docker run -it --rm \
    --name style-bert-vits2-rocm \
    --device=/dev/kfd \
    --device-cgroup-rule='c 226:* rmw' \
    --security-opt seccomp=unconfined \
    -e HSA_OVERRIDE_GFX_VERSION=11.0.0 \
    -e ROCM_VISIBLE_DEVICES=all \
    -v "$PWD/model_assets:/app/Style-Bert-VITS2/model_assets" \
    -v "$PWD/inputs:/app/Style-Bert-VITS2/inputs" \
    -v "$PWD/outputs:/app/Style-Bert-VITS2/outputs" \
    -v "$PWD/configs:/app/Style-Bert-VITS2/configs" \
    -p 7860:7860 \
    -p 8000:8000 \
    style-bert-vits2-rocm:7.1 \
    python app.py
```

## オプショナル依存関係のインストール

コンテナ内で以下の機能を使用する場合は、個別にインストールが必要です。

### pyannote.audioのインストール

スタイル生成の高度な機能（話者分離など）を使用する場合：

```bash
# 実行中のコンテナに入る
docker exec -it style-bert-vits2-rocm bash

# インストール
pip install pyannote.audio

# コンテナから出る
exit
```

または、一度だけ実行する場合：

```bash
docker exec style-bert-vits2-rocm pip install pyannote.audio
```

**注意**: コンテナを削除するとインストール内容は消えます。永続化する場合は、カスタムDockerfileを作成するか、ボリュームマウントを使用してください。

### ONNX変換ツールのインストール

ONNX形式への変換機能を使用する場合：

```bash
docker exec -it style-bert-vits2-rocm bash
pip install onnx onnxconverter-common onnxsim
exit
```

## ボリュームマウント

以下のディレクトリがホストとコンテナで共有されます：

- `model_assets/`: 学習済みモデルファイル
- `inputs/`: 入力音声ファイルなど
- `outputs/`: 生成された音声ファイルなど
- `configs/`: 設定ファイル

これにより、コンテナを削除してもデータが保持されます。

## トラブルシューティング

### GPUが認識されない

**症状**: PyTorchがCUDAデバイスを認識しない

**解決策**:
1. `HSA_OVERRIDE_GFX_VERSION` 環境変数を確認・調整
   ```bash
   # コンテナ内で確認
   docker exec style-bert-vits2-rocm python -c "import torch; print(torch.cuda.is_available())"
   ```
2. ROCmデバイスの確認
   ```bash
   rocminfo | grep gfx
   ```
3. デバイスのマウント確認
   ```bash
   docker exec style-bert-vits2-rocm ls -la /dev/kfd /dev/dri
   ```

### パーミッションエラー

**症状**: `/dev/kfd` や `/dev/dri` へのアクセスが拒否される

**解決策**:
```bash
# ユーザーをrender, videoグループに追加
sudo usermod -aG render,video $USER
# 再ログインが必要
```

### ポートが既に使用されている

**症状**: `port is already allocated` エラー

**解決策**:
`docker-compose.yml` または `docker run` コマンドでポート番号を変更：

```yaml
ports:
  - "7861:7860"  # ホスト側のポートを変更
```

### メモリ不足

**症状**: OOM (Out of Memory) エラー

**解決策**:
- Dockerのメモリ制限を増やす（Docker Desktopの場合）
- より小さいバッチサイズで実行
- CPUモードで実行（`--device cpu`）

### 依存関係のインストールエラー

**症状**: `pip install` でエラーが発生する

**解決策**:
1. pipをアップグレード
   ```bash
   docker exec style-bert-vits2-rocm pip install --upgrade pip
   ```
2. ベースイメージのPythonバージョンを確認（Python 3.12）

## パフォーマンスの最適化

### GPU認識の確認

```bash
docker exec style-bert-vits2-rocm python -c "
import torch
print(f'PyTorch: {torch.__version__}')
print(f'CUDA available: {torch.cuda.is_available()}')
print(f'Device count: {torch.cuda.device_count() if torch.cuda.is_available() else 0}')
if torch.cuda.is_available():
    print(f'Device name: {torch.cuda.get_device_name(0)}')
"
```

### 環境変数の調整

特定のGPUアーキテクチャでは `HSA_OVERRIDE_GFX_VERSION` の値を調整する必要があります：

```bash
# docker-compose.yml または docker run で変更
-e HSA_OVERRIDE_GFX_VERSION=11.0.0  # gfx1151の場合など
```

サポートされている値は、使用しているGPUアーキテクチャに依存します。

## 参考情報

- [ROCm Docker対応差分メモ](ROCm_Docker_DIFF.md)
- [ROCm公式ドキュメント](https://rocm.docs.amd.com/)
- [Style-Bert-VITS2 メインREADME](README.md)

