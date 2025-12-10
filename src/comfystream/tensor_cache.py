from asyncio import Queue as AsyncQueue
from queue import Queue
from typing import Union

import numpy as np
import torch

# TODO: improve eviction policy fifo might not be the best, skip alternate frames instead
image_inputs: Queue[Union[torch.Tensor, np.ndarray]] = Queue(maxsize=1)
image_outputs: AsyncQueue[Union[torch.Tensor, np.ndarray]] = AsyncQueue()

audio_inputs: Queue[Union[torch.Tensor, np.ndarray]] = Queue()
audio_outputs: AsyncQueue[Union[torch.Tensor, np.ndarray]] = AsyncQueue()

text_outputs: AsyncQueue[str] = AsyncQueue()
