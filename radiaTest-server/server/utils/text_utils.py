# Copyright (c) [2022] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
####################################
# @Author  :
# @email   :
# @Date    :
# @License : Mulan PSL v2
#####################################

from typing import Type, List, Dict
from abc import abstractmethod, ABC
"""
    This module provides a text splitter class TextItemSplitter that splits texts consists of items of numeral tags 
    into a dictionary, along with 3 XxxNumeralRule classes representing the numeral rules which inherit the class 
    AbstractNumeralRule.
"""


class AbstractNumeralRule(ABC):
    """
        The base class of the numeral rule classes.
        Abstract class method:
            def value_of(cls, num_str: str) -> int:
                takes a string representing an integer under a certain serial numeral rule as a parameter,
                and returns the integer value.
                If the string cannot be parsed to an integer under this numeral rule, please BE SURE TO
                    raise ValueError
                This is because the ValueError would be checked in method TextItemSplitter.split_text_items

        Note that this method is a class method, so DO NOT create any instance of this class's subclass.
    """
    @classmethod
    @abstractmethod
    def value_of(cls, num_str: str) -> int:
        pass


class DefaultNumeralRule(AbstractNumeralRule):
    """
        DefaultNumeralRule: Decimal arabic integer. Use standard int().
    """
    @classmethod
    def value_of(cls, num_str: str) -> int:
        if num_str.isdigit():
            return int(num_str)
        else:
            raise ValueError


class AlphabetNumeralRule(AbstractNumeralRule):
    """
        AlphabetNumeralRule: Same as the numeral rule in Excel columns. A~Z: 1~26, AA: 27. Case insensitive.
    """
    @classmethod
    def value_of(cls, num_str: str) -> int:
        if num_str.isascii() and num_str.isalpha():
            num_str = num_str.lower()
            result: int = 0
            multiplier: int = 1
            for each in num_str[::-1]:
                result = result + (ord(each) - ord("a") + 1) * multiplier
                multiplier *= 26
            return result
        else:
            raise ValueError


class RomanNumeralRule(AbstractNumeralRule):
    """
        RomanNumeralRule:
        I: 1, V: 5, X: 10, L: 50, C: 100, D: 500, M: 1000. Case insensitive.
        Smaller number written on the left of larger number means subtraction, otherwise means addition.
    """
    @classmethod
    def value_of(cls, num_str: str) -> int:
        if num_str.isascii() and num_str.isalpha():
            num_str = num_str.lower()
        else:
            raise ValueError
        numeral_dict = {'i': 1, 'v': 5, 'x': 10, 'l': 50, 'c': 100, 'd': 500, 'm': 1000}
        result: int = 0
        len_num_str: int = len(num_str)
        for cnt in range(len_num_str):
            if numeral_dict.get(num_str[cnt]) is None:
                raise ValueError
            elif cnt < len(num_str) - 1 and numeral_dict.get(num_str[cnt]) < numeral_dict.get(num_str[cnt + 1]):
                result -= numeral_dict.get(num_str[cnt])
            else:
                result += numeral_dict.get(num_str[cnt])
        return result


class TextItemSplitter:
    """
        The "Text Item Splitter" class:
        This class's instance splits a text which consists of items with tag numerals to a dictionary,
        using the numeral values as keys and the items as values.

        Member method:
            def split_longtext_items(self, text: str) -> dict[int, str]
                uses the text to be split as a parameter, and returns the dictionary mentioned above.
    """

    _numeral_rules: List[Type[AbstractNumeralRule]]   # The numeral rule type list.
    # When trying to parse a numeral text to an integer value, the rules will be applied in the order of this list.
    _separators: List[str] = [". ", "、"]  # Separators separate the numeral tag and the item text.
    _terminators: List[str] = ["\n"]  # Terminators separate the item text and the NEXT numeral tag.
    # i.e. the struct of the origin text is:
    # numeral seperator item-text terminator numeral seperator item-text terminator ......

    def __init__(self,
                 numeral_rules: List[Type[AbstractNumeralRule]],
                 separators: List[str] = None,
                 terminators: List[str] = None):
        """
            :param: numeral_rules: List[Type[AbstractNumeralRule]]
                The numeral rule type list.
            :param: separators: List[str]
                The separator list. Leave None for [". ", "、"]
            :param: terminators: List[str]
                The terminator list. Leave None for ["\n"]
        """
        if separators is not None:
            self._separators = separators
        if terminators is not None:
            self._terminators = terminators
        self._numeral_rules = numeral_rules

    def split_text_items(self, text: str) -> dict[int, str]:
        """
            :param: text: str
                The text to be split.
            :return: -> dict[int, str]
                The dictionary of the input text, using the numeral's integer values in the input text
                as keys and the item-texts in the input text as values.
        """
        class Occurrence:
            """
                The TextItemSplitter.split_text_items method involves the operation of searching
                symbols(separators, terminators) in the text.
                In order to better represent the occurrence of a symbol in the text, this internal class
                is designed.
                fields:
                    pos: int
                        The position of the symbol in the text
                    symbol: int
                        The symbol
                These two fields should not change after __init__.
            """
            pos: int
            symbol: str

            def __init__(self, pos, symbol):
                self.pos = pos
                self.symbol = symbol

            def __repr__(self):
                return f"({self.pos.__repr__()}, {self.symbol.__repr__()})"

        def find_occurrences(symbol_list: List[str]) -> List[Occurrence]:
            """
                This is an inner function.
                Find each occurrence of the specified symbols in the text to be split (outer variable for this method)
                Returns an Occurrence list, which is sorted according to the position of the symbols in the text.
                :param: symbol_list: List of the specified symbols, actually we only used self._separators and
                self._terminators. This method does not change the content of the input list.
                :return: an Occurrence list, every Occurrence contains a symbol and the position it occurs in the text.
            """
            result_list: List[Occurrence] = []
            for symbol in symbol_list:
                last_pos: int = -1
                while True:
                    last_pos = text.find(symbol, last_pos + 1)
                    if last_pos == -1:
                        break
                    result_list.append(Occurrence(last_pos, symbol))

            result_list = sorted(result_list, key=lambda occurrence: occurrence.pos)
            return result_list

        # The struct of the origin text is:
        # numeral seperator item-text terminator numeral seperator item-text terminator ......
        # Find every terminator and separator.
        # If the text between a terminator and a separator is a numeral, take it as a split point.
        # Find the occurrences of terminators and separators. Add a -1 for the terminator at the beginning of the text.
        terminator_occurrences: List[Occurrence] = [Occurrence(-1, "")] + find_occurrences(self._terminators)
        separator_occurrences: List[Occurrence] = find_occurrences(self._separators)

        # For each terminator, look for the nearest separator after it, and see whether the text between is a numeral.
        # If yes, mark the terminator's occurrence as a split point.
        split_points: List[Occurrence] = []
        numeral_values: List[int] = []  # The integer values parsed from the numerals.
        index_of_separator_occurrences: int = 0  # Indicates the n-th separator occurrence in the text.
        for terminator_occurrence in terminator_occurrences:
            # For each terminator, look for the nearest separator after it.
            while index_of_separator_occurrences < len(separator_occurrences) \
                    and separator_occurrences[index_of_separator_occurrences].pos <= terminator_occurrence.pos:
                index_of_separator_occurrences += 1
            if index_of_separator_occurrences >= len(separator_occurrences):
                break
            # If the terminator indicates the beginning of the text,
            # cut the text from the beginning and try to check whether it is a numeral.
            if terminator_occurrence.pos == -1:
                split_numeral_str = text[0:separator_occurrences[index_of_separator_occurrences].pos]
            else:  # If not, cut the text from the terminator to the separator.
                split_numeral_str = \
                    text[terminator_occurrence.pos:separator_occurrences[index_of_separator_occurrences].pos]
                # Remove the terminator in the front of the cut part.
                split_numeral_str = split_numeral_str.removeprefix(terminator_occurrence.symbol)
            # Use numeral rules in self._numeral_rules in order of the list, try to parse the cut part to an integer.
            # If succeeded, here is the split point of two text-items.
            # Otherwise, the current terminator is not a split point.
            # It is just that a separator and a terminator occur in the same text-item.
            for each_rule in self._numeral_rules:
                try:
                    numeral_value: int = each_rule.value_of(split_numeral_str)
                except ValueError:
                    pass
                else:
                    # If parsing succeeded, mark the parsed integer and the split point.
                    numeral_values.append(numeral_value)
                    split_points.append(terminator_occurrence)
                    break

        # The end position of the original text is also regarded as a split point, with the last terminator occurs.
        # Note that this terminator may not really occur at the end of the text,
        # but if it does, it is convenient to be removed using the removesuffix function.
        # In addition, if there is still some text in front of the first serial number, add a numeral tag 0 for it.
        split_points.append(Occurrence(len(text), terminator_occurrences[-1].symbol))
        if split_points[0].pos != -1:
            split_points = [Occurrence(-1, "")] + split_points
            numeral_values = [0] + numeral_values

        # According to the of split points list, cut out each part of the text,
        # combined with the numeral_value list to form a dictionary to be returned.
        result_dict: Dict[int, str] = dict()
        for cnt in range(1, len(split_points)):
            if cnt == 1:  # First part, from the beginning of the text to this split point.
                text_item = text[0:split_points[cnt].pos]
            else:  # Not the first part, from the last split point to this split point.
                text_item = text[split_points[cnt - 1].pos:split_points[cnt].pos]
                # Not the first part, there is a terminator in the front. Remove it.
                text_item = text_item.removeprefix(split_points[cnt].symbol)
                # In addition, if it is the last part, there may also be a terminator at the end. If there is, remove it
                if cnt == len(split_points) - 1:
                    text_item = text_item.removesuffix(split_points[cnt].symbol)
            # Fill the dictionary to be returned with integer values and text-items
            result_dict[numeral_values[cnt - 1]] = text_item

        return result_dict
