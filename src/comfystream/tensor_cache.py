import asyncio
import torch
from queue import Queue

image_inputs: Queue[torch.Tensor] = Queue()
image_outputs: Queue[asyncio.Future] = Queue()

audio_inputs: Queue[torch.Tensor] = Queue()
audio_outputs: Queue[asyncio.Future] = Queue()
