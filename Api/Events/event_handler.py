from abc import ABC, abstractmethod
from trade_event import TradeEvent


class EventHandler(ABC):
    '''Base class for event handlers'''
    def __init__(self, event: TradeEvent):
        self.event = event

    @abstractmethod
    def handle_content(self):
        '''Handle the content of the event'''
        
        pass
    