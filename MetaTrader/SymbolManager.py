import MetaTrader5 as mt5

class SymbolManager:
    """ Symbol manager class to manage the symbols """
    def __init__(self):
        self.symbols = {}
        self.selected_symbol = None
        
    def get_symbols(self):
        """ Get all available symbols """
        symbols = mt5.symbols_get()
        for symbol in symbols:
            self.symbols[symbol.name] = symbol
        return self.symbols
    
    def get_selected_symbol(self):
        """ Get the selected symbol """
        return self.selected_symbol
    
    def set_selected_symbol(self, symbol):
        """ Set the selected symbol """
        self.selected_symbol = symbol
        return self.selected_symbol
    
    def select_symbol(self, symbol_name):
        """ Select a symbol """
        if symbol_name in self.symbols:
            self.selected_symbol = self.symbols[symbol_name]
            return self.selected_symbol
        else:
            return None
