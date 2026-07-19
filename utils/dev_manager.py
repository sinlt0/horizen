import json
import os

class DevManager:

    def __init__(self, file_path='devs.json'):
        self.file_path = file_path
        self.dev_ids = set()
        self.load_devs()

    def load_devs(self):
        if not os.path.exists(self.file_path):
            with open(self.file_path, 'w') as f:
                json.dump({'dev_ids': []}, f)
            return
        try:
            with open(self.file_path, 'r') as f:
                data = json.load(f)
                self.dev_ids = set(data.get('dev_ids', []))
        except Exception as e:
            print(f'Failed to load devs.json: {e}')

    def is_dev(self, user_id: int, bot):
        if user_id == getattr(bot, 'owner_id', None):
            return True
        if user_id in getattr(bot, 'owner_ids', set()):
            return True
        return user_id in self.dev_ids