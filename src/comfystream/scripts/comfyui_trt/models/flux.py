import torch

from .baseline import TRTModelUtil
from .diffusion_pipe import FluxT2IPipe
from comfyui_trt.quantization import FP8_BF16_FLUX_MMDIT_BMM2_FP8_OUTPUT_CONFIG


class FLuxBase(TRTModelUtil):
    def __init__(
            self,
            context_dim: int,
            input_channels: int,
            y_dim: int,
            hidden_size: int,
            double_blocks: int,
            single_blocks: int,
            *args,
            **kwargs,
    ) -> None:
        super().__init__(context_dim, input_channels, 256, *args, **kwargs)

        self.hidden_size = hidden_size
        self.y_dim = y_dim
        self.single_blocks = single_blocks
        self.double_blocks = double_blocks

        self.extra_input = {
            "guidance": {"batch": "{batch_size}"},
            "y": {"batch": "{batch_size}", "y_dim": y_dim},
        }

        self.input_config.update(self.extra_input)

        if self.use_control:
            self.control = self.get_control()
            self.input_config.update(self.control)

    def to_dict(self):
        return {
            "context_dim": self.context_dim,
            "input_channels": self.input_channels,
            "y_dim": self.y_dim,
            "hidden_size": self.hidden_size,
            "double_blocks": self.double_blocks,
            "single_blocks": self.single_blocks,
            "use_control": self.use_control,
        }

    def get_control(self):
        control_input = {}
        for i in range(self.double_blocks):
            control_input[f"input_control_{i}"] = {
                "batch": "{batch_size}",
                "ids": "({height}*{width}//(8*2)**2)",
                "hidden_size": self.hidden_size,
            }
        for i in range(self.single_blocks):
            control_input[f"output_control_{i}"] = {
                "batch": "{batch_size}",
                "ids": "({height}*{width}//(8*2)**2)",
                "hidden_size": self.hidden_size,
            }
        return control_input

    def get_dtype(self):
        return torch.bfloat16

    @classmethod
    def from_model(cls, model, **kwargs):
        return cls(
            context_dim=model.model.model_config.unet_config["context_in_dim"],
            input_channels=model.model.model_config.unet_config["in_channels"],
            hidden_size=model.model.model_config.unet_config["hidden_size"],
            y_dim=model.model.model_config.unet_config["vec_in_dim"],
            double_blocks=model.model.model_config.unet_config["depth"],
            single_blocks=model.model.model_config.unet_config["depth_single_blocks"],
            **kwargs,
        )

    def get_t2i_pipe(
            self,
            model,
            clip,
            seed,
            batch_size=1,
            width=1024,
            height=1024,
            cfg=3.5,
            sampler_name="euler",
            scheduler="simple",
            denoise=1.0,
            device="cuda",
            *args,
            **kwargs,
    ):
        return FluxT2IPipe(
            model,
            clip,
            batch_size,
            width,
            height,
            seed,
            cfg,
            sampler_name,
            scheduler,
            denoise,
            kwargs.get("max_shift", 1.15),
            kwargs.get("base_shift", 0.5),
            device,
        )

    def get_qconfig(self, precision: str, **kwargs) -> tuple[dict, dict]:
        if precision == "fp8":
            return (FP8_BF16_FLUX_MMDIT_BMM2_FP8_OUTPUT_CONFIG, {"quant_level": 4.0})
        elif precision == "int8":
            return ({}, {"quant_level": 3.0})


class Flux_TRT(FLuxBase):
    def __init__(
            self,
            context_dim=4096,
            input_channels=16,
            y_dim=768,
            hidden_size=3072,
            double_blocks=19,
            single_blocks=28,
            **kwargs,
    ):
        super().__init__(
            context_dim=context_dim,
            input_channels=input_channels,
            y_dim=y_dim,
            hidden_size=hidden_size,
            double_blocks=double_blocks,
            single_blocks=single_blocks,
            **kwargs,
        )

    @classmethod
    def from_model(cls, model, **kwargs):
        return super(Flux_TRT, cls).from_model(model, use_control=True)


class FluxSchnell_TRT(FLuxBase):
    def __init__(
            self,
            context_dim=4096,
            input_channels=16,
            y_dim=768,
            hidden_size=3072,
            double_blocks=19,
            single_blocks=28,
            **kwargs,
    ):
        super().__init__(
            context_dim=context_dim,
            input_channels=input_channels,
            y_dim=y_dim,
            hidden_size=hidden_size,
            double_blocks=double_blocks,
            single_blocks=single_blocks,
            **kwargs,
        )

    @classmethod
    def from_model(cls, model, **kwargs):
        return super(FluxSchnell_TRT, cls).from_model(model, use_control=True)
