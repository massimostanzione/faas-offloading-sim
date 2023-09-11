
class KeyLocator:
    
    def __init__ (self):
        self.mapping = {}

    def update_key_location (self, key, node):
        self.mapping[key] = node

key_locator = KeyLocator()
