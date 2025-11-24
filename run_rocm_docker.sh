#!/bin/bash
# ROCm Docker環境でStyle-Bert-VITS2を実行するスクリプト
# 使用方法: ./run_rocm_docker.sh [app.py|server_editor.py|server_fastapi.py]

set -e

IMAGE_NAME="style-bert-vits2-rocm:7.1"
CONTAINER_NAME="style-bert-vits2-rocm"

# 実行するコマンド（デフォルトはapp.py）
SCRIPT=${1:-app.py}

# ROCmデバイスのパス（通常は/dev/kfdと/dev/dri）
KFD_DEVICE="/dev/kfd"
DRI_DEVICES="/dev/dri"

# ボリュームマウント（モデルやデータを永続化）
MODEL_VOLUME="${PWD}/model_assets:/app/Style-Bert-VITS2/model_assets"
BERT_VOLUME="${PWD}/bert:/app/Style-Bert-VITS2/bert"
INPUTS_VOLUME="${PWD}/inputs:/app/Style-Bert-VITS2/inputs"
OUTPUTS_VOLUME="${PWD}/outputs:/app/Style-Bert-VITS2/outputs"
CONFIGS_VOLUME="${PWD}/configs:/app/Style-Bert-VITS2/configs"

# イメージが存在しない場合はビルド
if ! docker image inspect "$IMAGE_NAME" &>/dev/null; then
    echo "Dockerイメージが見つかりません。ビルドを開始します..."
    docker build -t "$IMAGE_NAME" .
fi

# 既存のコンテナがあれば停止・削除
if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "既存のコンテナを停止・削除します..."
    docker stop "$CONTAINER_NAME" 2>/dev/null || true
    docker rm "$CONTAINER_NAME" 2>/dev/null || true
fi

# 環境変数（ROCm関連）
export HSA_OVERRIDE_GFX_VERSION=11.0.0

# Dockerコンテナを起動
echo "Dockerコンテナを起動します..."
echo "実行スクリプト: $SCRIPT"

docker run -it --rm \
    --name "$CONTAINER_NAME" \
    --device="$KFD_DEVICE" \
    --device-cgroup-rule='c 226:* rmw' \
    --security-opt seccomp=unconfined \
    -e HSA_OVERRIDE_GFX_VERSION=11.0.0 \
    -e ROCM_VISIBLE_DEVICES=all \
    -v "$MODEL_VOLUME" \
    -v "$BERT_VOLUME" \
    -v "$INPUTS_VOLUME" \
    -v "$OUTPUTS_VOLUME" \
    -v "$CONFIGS_VOLUME" \
    -v "${PWD}/slm:/app/Style-Bert-VITS2/slm" \
    -v "${PWD}/pretrained:/app/Style-Bert-VITS2/pretrained" \
    -v "${PWD}/pretrained_jp_extra:/app/Style-Bert-VITS2/pretrained_jp_extra" \
    -p 7860:7860 \
    -p 8000:8000 \
    "$IMAGE_NAME" \
    python "$SCRIPT" ${@:2}

