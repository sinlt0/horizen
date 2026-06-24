import os
import importlib.util
from types import SimpleNamespace

class EmojiManager:

    def __init__(self):
        self.e = SimpleNamespace()

    def load_emojis(self, directory='emoji'):
        if not os.path.exists(directory):
            return
        for root, dirs, files in os.walk(directory):
            for filename in files:
                if filename.endswith('.py') and (not filename.startswith('__')):
                    module_name = filename[:-3]
                    file_path = os.path.join(root, filename)
                    spec = importlib.util.spec_from_file_location(module_name, file_path)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    if hasattr(module, 'EMOJIS'):
                        for key, value in module.EMOJIS.items():
                            setattr(self.e, key, value)
                    for key, value in vars(module).items():
                        if not key.startswith('_') and key != 'EMOJIS':
                            setattr(self.e, key, value)

    def get_all(self):
        return self.e