import pandas as pd


class PandasDict:
    load_methods = {
        "csv": pd.read_csv,
        "xlsx": pd.read_excel,
        "xls": pd.read_excel,
    }


class Excel:
    def __init__(self, filetype):
        self.filetype = filetype
    
    def load(self, filepath):
        _load_method = PandasDict.load_methods[self.filetype]
        df = _load_method(filepath)

        return df.to_dict("records")


class SheetExtractor:
    def __init__(self, cols_dict) -> None:
        self._dict = cols_dict
    
    def run(self, data):
        _result = []

        for row in data:
            _row = {}
            for key, value in row.items():
                if key in self._dict.keys() and value == value and value:
                    _row[self._dict.get(key)] = value
            
            _result.append(_row)

        return _result            
                

