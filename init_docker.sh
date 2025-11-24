#!/bin/bash
# Docker環境でのモデル初期化スクリプト
# 推論用の最小限のモデルをダウンロードします

set -e

IMAGE_NAME="style-bert-vits2-rocm:7.1"
CONTAINER_NAME="style-bert-vits2-rocm-init"

# オプション解析
ONLY_INFER=true
SKIP_DEFAULT=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --full)
            ONLY_INFER=false
            shift
            ;;
        --skip-default)
            SKIP_DEFAULT=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--full] [--skip-default]"
            echo "  --full: 学習用モデルも含めてダウンロード"
            echo "  --skip-default: デフォルトモデルのダウンロードをスキップ"
            exit 1
            ;;
    esac
done

# イメージが存在しない場合はビルド
if ! docker image inspect "$IMAGE_NAME" &>/dev/null; then
    echo "Dockerイメージが見つかりません。ビルドを開始します..."
    docker build -t "$IMAGE_NAME" .
fi

# ボリュームマウント（モデルやデータを永続化）
MODEL_VOLUME="${PWD}/model_assets:/app/Style-Bert-VITS2/model_assets"
BERT_VOLUME="${PWD}/bert:/app/Style-Bert-VITS2/bert"
CONFIGS_VOLUME="${PWD}/configs:/app/Style-Bert-VITS2/configs"

# 必要なディレクトリを作成
mkdir -p model_assets bert configs

echo "=== Docker環境でのモデル初期化を開始します ==="
echo "モード: $([ "$ONLY_INFER" = true ] && echo '推論のみ' || echo 'フル（学習含む）')"
echo "デフォルトモデル: $([ "$SKIP_DEFAULT" = true ] && echo 'スキップ' || echo 'ダウンロード')"
echo ""

# 初期化コマンドの構築
INIT_CMD="python initialize.py"
if [ "$ONLY_INFER" = true ]; then
    INIT_CMD="$INIT_CMD --only_infer"
fi
if [ "$SKIP_DEFAULT" = true ]; then
    INIT_CMD="$INIT_CMD --skip_default_models"
fi

# Dockerコンテナで初期化を実行
echo "コンテナ内で初期化スクリプトを実行中..."
docker run --rm \
    --name "$CONTAINER_NAME" \
    -v "$MODEL_VOLUME" \
    -v "$BERT_VOLUME" \
    -v "$CONFIGS_VOLUME" \
    -v "${PWD}/slm:/app/Style-Bert-VITS2/slm" \
    -v "${PWD}/pretrained:/app/Style-Bert-VITS2/pretrained" \
    -v "${PWD}/pretrained_jp_extra:/app/Style-Bert-VITS2/pretrained_jp_extra" \
    "$IMAGE_NAME" \
    bash -c "$INIT_CMD"

echo ""
echo "=== 初期化が完了しました ==="
echo "ダウンロードされたモデル:"
echo "  - model_assets/: 推論用モデル"
echo "  - bert/: BERTモデル"
if [ "$ONLY_INFER" = false ]; then
    echo "  - slm/: 学習用SLMモデル"
    echo "  - pretrained/: 事前学習済みモデル"
    echo "  - pretrained_jp_extra/: JP-Extra事前学習済みモデル"
fi
echo ""
echo "次のステップ: 推論サーバーを起動してください"
echo "  ./run_rocm_docker.sh app.py"

