import warnings
from collections import defaultdict
from typing import Any, Dict, Callable
import gc
import torch


def _clear_model(model):
    gc.collect()
    torch.cuda.empty_cache()
    del model


class ModelCache:
    def __init__(self, clear_func: Callable = _clear_model):
        self._cache_map: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self.clear_func = clear_func

    def add(self, model_name: str, model_size: str, model: Any):
        if model_size in self._cache_map[model_name]:
            raise KeyError(f'{model_name}[{model_size}] is already cached.clear before new cache!')

        self._cache_map[model_name][model_size] = model
        return model

    def get(self, model_name: str, model_size: str) -> Any:
        if model_size not in self._cache_map[model_name]:
            raise KeyError(f'Not Found Model{model_name}][{model_size}]')
        return self._cache_map[model_name][model_size]

    def exist(self, model_name: str, model_size: str) -> bool:
        return model_size in self._cache_map[model_name]

    def remove(self, model_name: str, model_size: str):
        if model_size not in self._cache_map[model_name]:
            warnings.warn(f'Not Found Model{model_name}][{model_size}]')
            return
        model = self._cache_map[model_name].pop(model_size)
        self.clear_func(model)

    def clear(self):
        for k, v in self._cache_map.items():
            for k2, v2 in v.items():
                self.clear_func(v2)
        self._cache_map = defaultdict(dict)
