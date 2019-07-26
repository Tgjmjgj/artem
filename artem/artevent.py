import enum

class ArtEventMetaclass(enum.EnumMeta):

    def __getitem__(self, key):
        if isinstance(key, str):
            key = key.upper()
            for item in self:
                if item.name == key:
                    return item
            return None
        elif isinstance(key, ArtEvent):
            return key
        else:
            return None

class ArtEvent(enum.Enum, metaclass=ArtEventMetaclass):
    """Enumeration of the available events
    
    """
    START = 1
    JOIN = 2
    MESSAGE = 3
    POSTPROC = 4
    TIME = 5
    IDLE = 6
    SILENCE = 7