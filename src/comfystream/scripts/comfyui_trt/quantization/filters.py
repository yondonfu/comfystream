import re

import modelopt.torch.quantization as mtq
import torch
import torch.nn.functional as F

from .attention_plugin import attn_cls, flux_attn_cls


def disable_all(name):
    return True


def filter_func(name):
    pattern = re.compile(
        r".*(emb_layers|time_embed|input_blocks.0.0|out.2|skip_connection|label_emb.0|x_embedder|pos_embed|t_embedder|y_embedder|context_embedder|final_layer.adaLN_modulation|final_layer.linear).*"
    )
    return pattern.match(name) is not None


def skip_connection_filter_func(name):
    pattern = re.compile(r".*(proj_out).*")
    return pattern.match(name) is not None


def quantize_lvl(backbone, quant_level=2.5, linear_only=False, enable_conv_3d=True):
    """
    We should disable the unwanted quantizer when exporting the onnx
    Because in the current modelopt setting, it will load the quantizer amax for all the layers even
    if we didn't add that unwanted layer into the config during the calibration
    """
    for name, module in backbone.named_modules():
        if isinstance(module, torch.nn.Conv2d):
            if linear_only:
                module.input_quantizer.disable()
                module.weight_quantizer.disable()
            else:
                module.input_quantizer.enable()
                module.weight_quantizer.enable()
        elif isinstance(module, torch.nn.Linear):
            if (
                    (quant_level >= 2 and "ff.net" in name)
                    or (quant_level >= 2.5 and ("to_q" in name or "to_k" in name or "to_v" in name))
                    or quant_level >= 3
            ):
                module.input_quantizer.enable()
                module.weight_quantizer.enable()
            else:
                module.input_quantizer.disable()
                module.weight_quantizer.disable()
        elif isinstance(module, torch.nn.Conv3d) and not enable_conv_3d:
            """
                Error: Torch bug, ONNX export failed due to unknown kernel shape in QuantConv3d.
                TRT_FP8QuantizeLinear and TRT_FP8DequantizeLinear operations in UNetSpatioTemporalConditionModel for svd
                cause issues. Inputs on different devices (CUDA vs CPU) may contribute to the problem.
            """
            module.input_quantizer.disable()
            module.weight_quantizer.disable()
        elif isinstance(module, attn_cls):
            # TRT only supports FP8 MHA with head_size % 16 == 0.
            # head_size = int(module.inner_dim / module.heads)
            if hasattr(module, "dim_head"):
                head_size = module.dim_head
            elif hasattr(module, "head_dim"):
                head_size = module.head_dim
            else:
                head_size = int(module.hidden_size / module.num_heads)
            if quant_level >= 4 and head_size % 16 == 0:
                module.q_bmm_quantizer.enable()
                module.k_bmm_quantizer.enable()
                module.v_bmm_quantizer.enable()
                module.softmax_quantizer.enable()
                if isinstance(module, flux_attn_cls):
                    if name.startswith("double_blocks"):
                        module.bmm2_output_quantizer.enable()
                    else:
                        module.bmm2_output_quantizer.disable()
            else:
                module.q_bmm_quantizer.disable()
                module.k_bmm_quantizer.disable()
                module.v_bmm_quantizer.disable()
                module.softmax_quantizer.disable()
                module.bmm2_output_quantizer.disable()


def fp8_mha_disable(backbone, quantized_mha_output: bool = True):
    def mha_filter_func(name):
        pattern = re.compile(
            r".*(q_bmm_quantizer|k_bmm_quantizer|v_bmm_quantizer|softmax_quantizer).*"
            if quantized_mha_output
            else r".*(q_bmm_quantizer|k_bmm_quantizer|v_bmm_quantizer|softmax_quantizer|bmm2_output_quantizer).*"
        )
        return pattern.match(name) is not None

    if hasattr(F, "scaled_dot_product_attention"):
        mtq.disable_quantizer(backbone, mha_filter_func)


def generate_fp8_scales(backbone):
    # temporary solution due to a known bug in torch.onnx._dynamo_export
    for _, module in backbone.named_modules():
        if isinstance(module, (torch.nn.Linear, torch.nn.Conv2d)) and (
                hasattr(module.input_quantizer, "_amax") and module.input_quantizer is not None
        ):
            module.input_quantizer._num_bits = 8
            module.weight_quantizer._num_bits = 8
            module.input_quantizer._amax = module.input_quantizer._amax * (127 / 448.0)
            module.weight_quantizer._amax = module.weight_quantizer._amax * (127 / 448.0)
        elif isinstance(module, attn_cls) and (
                hasattr(module.q_bmm_quantizer, "_amax") and not module.q_bmm_quantizer._disabled
        ):
            module.q_bmm_quantizer._num_bits = 8
            module.q_bmm_quantizer._amax = module.q_bmm_quantizer._amax * (127 / 448.0)
            module.k_bmm_quantizer._num_bits = 8
            module.k_bmm_quantizer._amax = module.k_bmm_quantizer._amax * (127 / 448.0)
            module.v_bmm_quantizer._num_bits = 8
            module.v_bmm_quantizer._amax = module.v_bmm_quantizer._amax * (127 / 448.0)
            module.softmax_quantizer._num_bits = 8
            module.softmax_quantizer._amax = module.softmax_quantizer._amax * (127 / 448.0)
