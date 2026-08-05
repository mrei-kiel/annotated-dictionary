#!/usr/bin/env python3
"""Check that dictionary entries use Na'vi grapheme collation order.

The four vowel sequences aw, ay, ew, and ey are single graphemes only when
they form a diphthong.  The first (main) IPA spelling of a headword is used to
distinguish a diphthong (for example ``aw``) from a syllable boundary (``a.w``).
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path


ENTRY_PATTERN = re.compile(r"\\(?P<command>Headword|Redirect)\s*")
IPA_PATTERN = re.compile(r"\\I\s*")

# This is also the order used by the chapter files.  Diphthongs are separate
# graphemes; ejectives, ng, and ts must likewise not be sorted letter-by-letter.
GRAPHEME_ORDER = (
    "'", "a", "aw", "ay", "ä", "e", "ew", "ey", "f", "h", "i", "ì",
    "k", "kx", "l", "ll", "m", "n", "ng", "o", "p", "px", "r", "rr", "s",
    "t", "tx", "ts", "u", "v", "w", "y", "z",
)
GRAPHEME_RANK = {grapheme: rank for rank, grapheme in enumerate(GRAPHEME_ORDER)}
MULTIGRAPHS = tuple(
    sorted(("kx", "px", "tx", "ts", "ng", "ll", "rr"), key=len, reverse=True)
)
DIPHTHONG_IPA_END = {"aw": "w", "ay": "j", "ew": "w", "ey": "j"}


@dataclass(frozen=True)
class Entry:
    command: str
    word: str
    ipa: str | None
    path: Path
    line: int


def strip_comments(source: str) -> str:
    """Remove unescaped LaTeX comments while preserving line numbers."""
    cleaned_lines: list[str] = []
    for line in source.splitlines(keepends=True):
        comment_at: int | None = None
        for index, character in enumerate(line):
            if character != "%":
                continue
            preceding_backslashes = 0
            cursor = index - 1
            while cursor >= 0 and line[cursor] == "\\":
                preceding_backslashes += 1
                cursor -= 1
            if preceding_backslashes % 2 == 0:
                comment_at = index
                break
        if comment_at is None:
            cleaned_lines.append(line)
        else:
            newline = "\n" if line.endswith("\n") else ""
            cleaned_lines.append(line[:comment_at] + newline)
    return "".join(cleaned_lines)


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
    match = re.search(rf"\\{re.escape(command)}\s*", source)
    if match is None:
        return None
    argument = braced_argument(source, match.end())
    return argument[0] if argument is not None else None


def latex_text(source: str) -> str:
    """Extract the plain text needed from a small dictionary display argument."""
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
    """Decode hyperlink target substitutions, retaining real capitals.

    Target names use ``A`` and ``I`` for ä and ì, but proper names can also
    contain genuine capital A and I.  The typeset headword disambiguates them.
    """
    display_letters = [character.casefold() for character in display if character.isalpha()]
    source_letter_index = 0
    decoded: list[str] = []
    for character in source.strip():
        displayed = (
            display_letters[source_letter_index]
            if source_letter_index < len(display_letters) and character.isalpha()
            else None
        )
        if character == "A":
            decoded.append("ä" if displayed == "ä" else "a")
        elif character == "I":
            decoded.append("ì" if displayed == "ì" else "i")
        else:
            decoded.append(character.lower())
        if character.isalpha():
            source_letter_index += 1
    return "".join(decoded)


def main_ipa(source: str) -> str | None:
    match = IPA_PATTERN.search(source)
    if match is None:
        return None
    argument = braced_argument(source, match.end())
    return argument[0] if argument is not None else None


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
    spellings = [match.group(0) for match in re.finditer(r"aw|ay|ew|ey", word)]
    if not spellings or ipa is None:
        return [True] * len(spellings)

    ipa_sequences = [
        (match.group(1) + {"w": "w", "j": "y"}[match.group(3)], not match.group(2))
        for match in re.finditer(r"([ae])(\.?)([wj])", normalized_ipa(ipa))
    ]
    if [sequence for sequence, _ in ipa_sequences] != spellings:
        # Missing or unusually typeset IPA should not make the checker unstable.
        # Treat the spelling as diphthongs; authors can add conventional main IPA
        # when a sequence actually crosses a syllable boundary.
        return [True] * len(spellings)
    return [is_diphthong for _, is_diphthong in ipa_sequences]


def graphemes(entry: Entry) -> tuple[str, ...]:
    # These marks distinguish affixes, productive forms, abbreviations, and
    # homonyms in the source.  They are not part of Na'vi alphabetical order.
    word = entry.word.casefold()
    # ``tì-us`` denotes the construction tì- + ‹us› and is intentionally
    # collated directly after the tì- prefix, rather than as a lexical word.
    if entry.ipa is None and re.fullmatch(r"tì-us", word):
        word = "tì"
    word = re.sub(r"[-+.\d]", "", word)
    flags = iter(diphthong_flags(word, entry.ipa))
    result: list[str] = []
    index = 0
    while index < len(word):
        character = word[index]
        if character.isspace():
            result.append(" ")
            index += 1
            continue

        pair = word[index:index + 2]
        if pair in DIPHTHONG_IPA_END:
            if next(flags):
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


def collation_key(entry: Entry) -> tuple[tuple[int, int | str], ...]:
    key: list[tuple[int, int | str]] = []
    for grapheme in graphemes(entry):
        if grapheme == " ":
            key.append((0, 0))
        elif grapheme in GRAPHEME_RANK:
            key.append((1, GRAPHEME_RANK[grapheme]))
        else:
            # Keep uncommon authoring punctuation deterministic and after letters.
            key.append((2, grapheme))
    return tuple(key)


def find_entries(path: Path, repository: Path) -> list[Entry]:
    source = strip_comments(path.read_text(encoding="utf-8"))
    entries: list[Entry] = []
    for match in ENTRY_PATTERN.finditer(source):
        first = braced_argument(source, match.end())
        if first is None:
            continue
        command = match.group("command")
        if command == "Headword":
            second = braced_argument(source, first[1])
            third = braced_argument(source, second[1]) if second is not None else None
            display_source = second[0] if second is not None else ""
            bold_display = first_command_argument(display_source, "B")
            display = latex_text(bold_display or display_source)
            word = target_text(first[0], display)
            ipa_source = third[0] if third is not None else ""
        else:
            word = latex_text(first[0]).casefold()
            ipa_source = first[0]
        entries.append(
            Entry(
                command=command,
                word=word,
                ipa=main_ipa(ipa_source),
                path=path.relative_to(repository),
                line=source.count("\n", 0, match.start()) + 1,
            )
        )
    return entries


def annotation_escape(value: str, *, property_value: bool = False) -> str:
    value = value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    if property_value:
        value = value.replace(":", "%3A").replace(",", "%2C")
    return value


def report_error(entry: Entry, previous: Entry) -> None:
    relative_path = entry.path.as_posix()
    message = (
        f"entry {entry.word!r} is out of Na'vi collation order; "
        f"it should appear before {previous.word!r} (line {previous.line}); "
        f"graphemes: {' · '.join(graphemes(entry))}"
    )
    print(f"{relative_path}:{entry.line}: error: {message}")
    if os.environ.get("GITHUB_ACTIONS") == "true":
        file_property = annotation_escape(relative_path, property_value=True)
        print(
            f"::error file={file_property},line={entry.line}::"
            f"{annotation_escape(message)}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "files",
        nargs="*",
        type=Path,
        help="chapter .tex files to check (default: all numbered dictionary chapters)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repository = Path(__file__).resolve().parents[1]
    paths = args.files or sorted(repository.glob("[0-3][0-9]_*.tex"))
    paths = [path if path.is_absolute() else repository / path for path in paths]

    errors = 0
    entry_count = 0
    for path in paths:
        entries = find_entries(path, repository)
        entry_count += len(entries)
        previous = entries[0] if entries else None
        for entry in entries[1:]:
            if previous is not None and collation_key(entry) < collation_key(previous):
                report_error(entry, previous)
                errors += 1
            previous = entry

    if errors:
        print(f"Dictionary ordering check failed with {errors} error(s).")
        return 1
    print(f"Dictionary ordering check passed: {entry_count} entries across {len(paths)} files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
