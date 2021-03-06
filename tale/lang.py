# coding=utf-8
"""
Language processing related operations.

'Tale' mud driver, mudlib and interactive fiction framework
Copyright by Irmen de Jong (irmen@razorvine.net)
"""

from __future__ import absolute_import, print_function, division, unicode_literals
import re
import bisect
import collections
from .tio import vfs

# genders are m,f,n
SUBJECTIVE = {"m": "he", "f": "she", "n": "it"}
POSSESSIVE = {"m": "his", "f": "her", "n": "its"}
OBJECTIVE = {"m": "him", "f": "her", "n": "it"}
GENDERS = {"m": "male", "f": "female", "n": "neuter"}


class OrderedCounter(collections.Counter, collections.OrderedDict):
    pass


def join(words, conj="and", group_multi=True):
    """
    Join a list of words to 'a,b,c, and e'
    If a word occurs multiple times (and group_multi=True),
    show 'thing and thing' as 'two things' instead.
    """
    def apply_amount(count, word):
        prefix, _, rest = word.partition(' ')
        if rest and prefix in __articles:
            # remove the article when we're dealing with multiple occurrences
            word = rest
        return spell_number(count) + " " + pluralize(word)
    if not words:
        return ""
    words = list(words)
    if len(words) == 1:
        return words[0]
    if group_multi and len(set(words)) == 1:
        return apply_amount(len(words), words[0])  # all words are the same
    if len(words) == 2:
        return "%s %s %s" % (words[0], conj, words[1])
    if group_multi:
        counts = OrderedCounter(words)
        words = []
        for word, count in counts.items():
            if count == 1:
                words.append(word)
            else:
                words.append(apply_amount(count, word))
        return join(words, conj, group_multi=False)
    return "%s, %s %s" % (", ".join(words[:-1]), conj, words[-1])


__a_exceptions = {
    "universe": "a",
    "university": "a",
    "user": "a",
    "hour": "an"
    # probably more, but these will have to do for now
}

__articles = {"the", "a", "an"}


def a(word):
    """a or an? simplistic version: if the word starts with aeiou, returns an, otherwise a"""
    if not word:
        return ""
    if word.startswith(("a ", "an ")):
        return word
    firstword = word.split(None, 1)[0]
    exception = __a_exceptions.get(firstword.lower(), None)
    if exception:
        return exception + " " + word
    elif word.startswith(('a', 'e', 'i', 'o', 'u')):
        return "an " + word
    return "a " + word


def reg_a_exceptions(exceptions):
    __a_exceptions.update(exceptions)


def fullstop(sentence, punct="."):
    """adds a fullstop to the end of a sentence if needed"""
    sentence = sentence.rstrip()
    if sentence.endswith(('!', '?', '.', ';', ':', '-', '=')):
        return sentence
    return sentence + punct


# adverbs are stored in a datafile next to this module
ADVERB_LIST = sorted(vfs.internal_resources["soul_adverbs.txt"].data.splitlines())   # keep the list for prefix search
ADVERBS = frozenset(ADVERB_LIST)


def adverb_by_prefix(prefix, amount=5):
    """
    Return a list of adverbs starting with the given prefix, up to the given amount
    Uses binary search in the sorted adverbs list, O(log n)
    """
    i = bisect.bisect_left(ADVERB_LIST, prefix)
    if i >= len(ADVERB_LIST):
        return []
    elif ADVERB_LIST[i].startswith(prefix):
        j = i + 1
        amount = min(amount, len(ADVERB_LIST) - i)   # avoid reading past the end of the list
        while amount > 1 and ADVERB_LIST[j].startswith(prefix):
            j += 1
            amount -= 1
        return ADVERB_LIST[i:j]
    else:
        return []


def possessive_letter(name):
    if not name:
        return ""
    if name[-1] in ('s', 'z', 'x'):
        return "'s"        # tess's foot
    elif name.endswith(" own"):
        return ""         # your own...
    else:
        return "'s"        # mark's foot


def possessive(name):
    return name + possessive_letter(name)


def capital(string):
    # cannot use string.capitalize because that lowercases the rest
    if string:
        string = string[0].upper() + string[1:]
    return string


def fullverb(verb):
    """return the full verb: shoot->shooting, poke->poking"""
    if verb[-1] == "e":
        return verb[:-1] + "ing"
    return verb + "ing"


def split(string):
    """
    Split a string on whitespace, but keeps words enclosed in quotes (' or ") together.
    The quotes themselves are stripped out.
    """
    def removequotes(word):
        if word.startswith(('"', "'")) and word.endswith(('"', "'")):
            return word[1:-1].strip()
        return word
    return [removequotes(p) for p in re.split("( |\\\".*?\\\"|'.*?')", string) if p.strip()]


__number_words = [
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
    "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen", "twenty"
]
__tens_words = [
    None, None, "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"
]


def spell_number(number):
    """
    Return a spelling of the number. Supports positive and negative ints,
    floats, and recognises popular fractions such as 0.5 and 0.25.
    Numbers that are very near a whole number are also returned as "about N".
    Any fraction that can not be spelled out (or is larger than +/- 100) will
    not be spelled out in words, but returned in numerical form.
    """
    def spell_positive_int(n):
        if n <= 20:
            return __number_words[n]
        tens, ones = divmod(n, 10)
        if tens <= 9:
            if ones > 0:
                return __tens_words[tens] + " " + __number_words[ones]
            return __tens_words[tens]
        return str(n)
    sign = ""
    orig_number = number
    if number < 0:
        sign = "minus "
        number = -number
    whole, fraction = divmod(number, 1)
    whole = int(whole)
    if fraction == 0.0:
        return sign + spell_positive_int(whole)
    elif fraction == 0.5:
        return sign + spell_positive_int(whole) + " and a half"
    elif fraction == 0.25:
        return sign + spell_positive_int(whole) + " and a quarter"
    elif fraction == 0.75:
        return sign + spell_positive_int(whole) + " and three quarters"
    elif fraction > 0.995:
        return "about " + sign + spell_positive_int(whole + 1)
    elif fraction < 0.005:
        return "about " + sign + spell_positive_int(whole)
    return str(orig_number)  # can't spell other fractions


__plural_irregularities = {
    "mouse": "mice",
    "child": "children",
    "person": "people",
    "man": "men",
    "woman": "women",
    "foot": "feet",
    "goose": "geese",
    "tooth": "teeth",
    "aircraft": "aircraft",
    "fish": "fish",
    "headquarters": "headquarters",
    "sheep": "sheep",
    "species": "species",
    "cattle": "cattle",
    "scissors": "scissors",
    "trousers": "trousers",
    "pants": "pants",
    "tweezers": "tweezers",
    "congratulations": "congratulations",
    "pyjamas": "pyjamas",
    "photo": "photos",
    "piano": "pianos",
    # probably more, but these will have to do for now
}


def pluralize(word, amount=2):
    if amount == 1:
        return word
    if word in __plural_irregularities:
        return __plural_irregularities[word]
    if word.endswith("is"):
        return word[:-2] + "es"
    if word.endswith("z"):
        return word + "zes"
    if word.endswith("s") or word.endswith("ch") or word.endswith("x") or word.endswith("sh"):
        return word + "es"
    if word.endswith("y"):
        if len(word) > 1 and word[-2] in "aeiou":
            return word + "s"
        return word[:-1] + "ies"
    if word.endswith("f"):
        return word[:-1] + "ves"
    if word.endswith("fe"):
        return word[:-2] + "ves"
    if word.endswith("o") and len(word) > 1 and word[-2] not in "aeiouy":
        return word + "es"
    return word + "s"


def yesno(value):
    value = value.lower() if value else ""
    if value in {"y", "yes", "sure", "yep", "yeah", "yessir", "sure thing"}:
        return True
    if value in {"n", "no", "nope", "no way", "hell no"}:
        return False
    raise ValueError("That is not an understood yes or no.")


def validate_gender(value):
    value = value.lower() if value else ""
    if value in GENDERS:
        return value
    if len(value) > 1:
        if value[0] in GENDERS and GENDERS[value[0]] == value:
            return value
    raise ValueError("That is not a valid gender.")
