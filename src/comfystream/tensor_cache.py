import torch
import numpy as np

from queue import Queue
from asyncio import Queue as AsyncQueue

from typing import Union

image_inputs: Queue[Union[torch.Tensor, np.ndarray]] = Queue()
image_outputs: AsyncQueue[Union[torch.Tensor, np.ndarray]] = AsyncQueue()

audio_inputs: Queue[Union[torch.Tensor, np.ndarray]] = Queue()
audio_outputs: AsyncQueue[Union[torch.Tensor, np.ndarray]] = AsyncQueue()
