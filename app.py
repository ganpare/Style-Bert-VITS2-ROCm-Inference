import argparse
from pathlib import Path

import gradio as gr
import torch

try:
    from gradio_client import utils as gradio_client_utils
except Exception:  # pragma: no cover
    gradio_client_utils = None
else:
    _original_get_type = gradio_client_utils.get_type
    _original_json_schema_to_python_type = gradio_client_utils.json_schema_to_python_type

    def _safe_get_type(schema):
        if isinstance(schema, bool):
            return "Any" if schema else "Never"
        if not isinstance(schema, dict):
            return "Any"
        return _original_get_type(schema)

    def _safe_json_schema_to_python_type(schema, defs=None):
        try:
            return _original_json_schema_to_python_type(schema, defs)
        except Exception:
            # API情報の取得に失敗した場合でも、基本構造を返す
            if isinstance(schema, dict) and "type" in schema:
                return schema.get("type", "Any")
            return "Any"

    gradio_client_utils.get_type = _safe_get_type
    gradio_client_utils.json_schema_to_python_type = _safe_json_schema_to_python_type

from config import get_path_config
from gradio_tabs.convert_onnx import create_onnx_app
from gradio_tabs.dataset import create_dataset_app
from gradio_tabs.inference import create_inference_app
from gradio_tabs.merge import create_merge_app
from gradio_tabs.style_vectors import create_style_vectors_app
from gradio_tabs.train import create_train_app
from style_bert_vits2.logging import logger
from style_bert_vits2.constants import GRADIO_THEME, VERSION
from style_bert_vits2.nlp.japanese import pyopenjtalk_worker
from style_bert_vits2.nlp.japanese.user_dict import update_dict
from style_bert_vits2.tts_model import TTSModelHolder
from style_bert_vits2.utils import torch_device_to_onnx_providers


# このプロセスからはワーカーを起動して辞書を使いたいので、ここで初期化
pyopenjtalk_worker.initialize_worker()

# dict_data/ 以下の辞書データを pyopenjtalk に適用
update_dict()


parser = argparse.ArgumentParser()
parser.add_argument("--device", type=str, default="cuda")
parser.add_argument("--host", type=str, default="0.0.0.0")
parser.add_argument("--port", type=int, default=None)
parser.add_argument("--no_autolaunch", action="store_true")
parser.add_argument("--share", action="store_true")
# parser.add_argument("--skip_default_models", action="store_true")

args = parser.parse_args()
device = args.device
if device == "cuda" and not torch.cuda.is_available():
    device = "cpu"

# if not args.skip_default_models:
#     download_default_models()

path_config = get_path_config()
model_holder = TTSModelHolder(
    Path(path_config.assets_root),
    device,
    torch_device_to_onnx_providers(device),
    ignore_onnx=True,
)

with gr.Blocks(theme=GRADIO_THEME) as app:
    gr.Markdown(f"# Style-Bert-VITS2 WebUI (version {VERSION})")
    with gr.Tabs():
        with gr.Tab("音声合成"):
            create_inference_app(model_holder=model_holder)
        with gr.Tab("データセット作成"):
            create_dataset_app()
        with gr.Tab("学習"):
            create_train_app()
        with gr.Tab("スタイル作成"):
            create_style_vectors_app()
        with gr.Tab("マージ"):
            create_merge_app(model_holder=model_holder)
        with gr.Tab("ONNX変換"):
            create_onnx_app(model_holder=model_holder)


_original_get_api_info = getattr(app, "get_api_info", None)


def _safe_get_api_info():
    if _original_get_api_info is None:
        return {}
    try:
        return _original_get_api_info()
    except Exception as exc:  # pragma: no cover
        logger.warning("Failed to build Gradio API schema: %s", exc)
        return {}


app.get_api_info = _safe_get_api_info

app.launch(
    server_name=args.host,
    server_port=args.port,
    inbrowser=not args.no_autolaunch,
    share=args.share,
)
