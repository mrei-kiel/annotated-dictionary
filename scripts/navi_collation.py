"""Na'vi grapheme collation, shared by the dictionary checks.

The four vowel sequences aw, ay, ew and ey are single graphemes only when
they form a diphthong. The main IPA spelling of a headword tells a diphthong
(``aw``) from a syllable boundary (``a.w``).
"""

from __future__ import annotations

import re


# The order of the chapter files. Diphthongs are separate graphemes;
# ejectives, ng and ts must likewise not be sorted letter by letter.
GRAPHEME_ORDER = (
    "'", "a", "aw", "ay", "ä", "e", "ew", "ey", "f", "h", "i", "ì",
    "k", "kx", "l", "ll", "m", "n", "ng", "o", "p", "px", "r", "rr", "s",
    "t", "tx", "ts", "u", "v", "w", "y", "z",
)
GRAPHEME_RANK = {grapheme: rank for rank, grapheme in enumerate(GRAPHEME_ORDER)}
MULTIGRAPHS = ("kx", "px", "tx", "ts", "ng", "ll", "rr")
DIPHTHONGS = ("aw", "ay", "ew", "ey")

CollationKey = tuple[tuple[int, int | str], ...]


def braced_argument(source: str, position: int) -> tuple[str, int] | None:
    while position < len(source) and source[position].isspace():
        position += 1
    if position >= len(source) or source[position] != "{":
        return None

    start = position + 1
    depth = 1
    position += 1
    while position < len(source):
        character = source[position]
        preceding_backslashes = 0
        cursor = position - 1
        while cursor >= 0 and source[cursor] == "\\":
            preceding_backslashes += 1
            cursor -= 1
        if preceding_backslashes % 2 == 0:
            if character == "{":
                depth += 1
            elif character == "}":
                depth -= 1
                if depth == 0:
                    return source[start:position], position + 1
        position += 1
    return None


def first_command_argument(source: str, command: str) -> str | None:
    match = re.search(rf"\\{re.escape(command)}(?![A-Za-z])\s*", source)
    if match is None:
        return None
    argument = braced_argument(source, match.end())
    return argument[0] if argument is not None else None


def latex_text(source: str) -> str:
    """Extract the plain text of a small display argument."""
    source = re.sub(r"\\I\s*\{.*", "", source, count=1, flags=re.DOTALL)
    source = re.sub(r"\\textsuperscript\s*\{.*", "", source, count=1, flags=re.DOTALL)
    previous = None
    while source != previous:
        previous = source
        source = re.sub(r"\\(?:B|cp|mbox)\s*\{([^{}]*)\}", r"\1", source)
    source = source.replace(r"\-", "").replace(r"\hyp{}", "-")
    source = re.sub(r"\\[A-Za-z]+\*?(?:\[[^]]*\])?", "", source)
    return re.sub(r"[{}]", "", source).strip()


def target_text(source: str, display: str = "") -> str:
    """Decode hyperlink target substitutions, keeping real capitals.

    Targets write ä and ì as ``A`` and ``I``, but proper names also hold real
    capital A and I. The typeset headword tells them apart.
    """
    display_letters = [character.casefold() for character in display if character.isalpha()]
    letter_index = 0
    decoded: list[str] = []
    for character in source.strip():
        displayed = (
            display_letters[letter_index]
            if letter_index < len(display_letters) and character.isalpha()
            else None
        )
        if character == "A":
            decoded.append("ä" if displayed == "ä" else "a")
        elif character == "I":
            decoded.append("ì" if displayed == "ì" else "i")
        else:
            decoded.append(character.lower())
        if character.isalpha():
            letter_index += 1
    return "".join(decoded)


def headword_word(anchor: str, display: str) -> str:
    """The word a headword stands for, from its anchor and display text."""
    bold = first_command_argument(display, "B")
    return target_text(anchor, latex_text(bold if bold is not None else display))


def main_ipa(body: str) -> str | None:
    """The first IPA argument of a headword body."""
    return first_command_argument(body, "I")


def normalized_ipa(source: str) -> str:
    source = source.lower().replace(r"\ae{}", "a")
    source = source.replace(r"\textcorner", "")
    source = source.replace(r"\cdot", "")
    previous = None
    while source != previous:
        previous = source
        source = re.sub(r"\\[a-z]+\*?\s*\{([^{}]*)\}", r"\1", source)
    source = re.sub(r"\\[a-z]+", "", source)
    return re.sub(r"[^a-z.]", "", source)


def diphthong_flags(word: str, ipa: str | None) -> list[bool]:
    spellings = [match.group(0) for match in re.finditer("|".join(DIPHTHONGS), word)]
    if not spellings or ipa is None:
        return [True] * len(spellings)

    ipa_sequences = [
        (match.group(1) + {"w": "w", "j": "y"}[match.group(3)], not match.group(2))
        for match in re.finditer(r"([ae])(\.?)([wj])", normalized_ipa(ipa))
    ]
    if [sequence for sequence, _ in ipa_sequences] != spellings:
        # Missing or unusually typeset IPA must not make the order unstable:
        # treat the spelling as diphthongs.
        return [True] * len(spellings)
    return [is_diphthong for _, is_diphthong in ipa_sequences]


def graphemes(word: str, ipa: str | None = None) -> tuple[str, ...]:
    # Affix, productive-form and homonym marks are not part of the order.
    word = word.casefold()
    # ``tì-us`` is the construction tì- + ‹us› and collates right after tì-.
    if ipa is None and word == "tì-us":
        word = "tì"
    word = re.sub(r"[-+.\d]", "", word)
    flags = iter(diphthong_flags(word, ipa))
    result: list[str] = []
    index = 0
    while index < len(word):
        character = word[index]
        if character.isspace():
            result.append(" ")
            index += 1
            continue

        pair = word[index:index + 2]
        if pair in DIPHTHONGS and next(flags):
            result.append(pair)
            index += 2
            continue
        multigraph = next(
            (candidate for candidate in MULTIGRAPHS if word.startswith(candidate, index)),
            None,
        )
        if multigraph is not None:
            result.append(multigraph)
            index += len(multigraph)
            continue
        result.append(character)
        index += 1
    return tuple(result)


def collation_key(word: str, ipa: str | None = None) -> CollationKey:
    key: list[tuple[int, int | str]] = []
    for grapheme in graphemes(word, ipa):
        if grapheme == " ":
            key.append((0, 0))
        elif grapheme in GRAPHEME_RANK:
            key.append((1, GRAPHEME_RANK[grapheme]))
        else:
            # Uncommon punctuation stays deterministic and after the letters.
            key.append((2, grapheme))
    return tuple(key)
