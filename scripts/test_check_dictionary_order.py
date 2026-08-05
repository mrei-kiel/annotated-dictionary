#!/usr/bin/env python3
"""Focused tests for Na'vi dictionary collation."""

from __future__ import annotations

import unittest
from pathlib import Path

from check_dictionary_order import Entry, collation_key, graphemes, target_text


PATH = Path("chapter.tex")


def entry(word: str, ipa: str | None = None) -> Entry:
    return Entry("Headword", word, ipa, PATH, 1)


class CollationTests(unittest.TestCase):
    def test_diphthong_is_one_grapheme(self) -> None:
        self.assertEqual(graphemes(entry("'awve", '"Paw.vE')), ("'", "aw", "v", "e"))

    def test_syllable_boundary_splits_apparent_diphthong(self) -> None:
        self.assertEqual(
            graphemes(entry("txawew", '"t\'a.wEw')),
            ("tx", "a", "w", "ew"),
        )

    def test_split_sequence_sorts_before_diphthong(self) -> None:
        split = entry("txawew", '"t\'a.wEw')
        diphthong = entry("txaw", "t'aw")
        self.assertLess(collation_key(split), collation_key(diphthong))

    def test_diphthongs_are_resolved_in_later_syllables(self) -> None:
        self.assertEqual(
            graphemes(entry("tìtxanew", 'tI."t\'a.nEw')),
            ("t", "ì", "tx", "a", "n", "ew"),
        )
        self.assertLess(
            collation_key(entry("tìtxanew", 'tI."t\'a.nEw')),
            collation_key(entry("tìtxaw", 'tI."t\'aw')),
        )

    def test_consonant_multigraphs_are_indivisible(self) -> None:
        self.assertEqual(
            graphemes(entry("ngaru txantsan ll rr")),
            (
                "ng", "a", "r", "u", " ", "tx", "a", "n", "ts", "a", "n",
                " ", "ll", " ", "rr",
            ),
        )

    def test_authoring_markers_do_not_affect_order(self) -> None:
        self.assertEqual(collation_key(entry("-a+2")), collation_key(entry("a")))

    def test_target_substitutions_do_not_change_real_capitals(self) -> None:
        self.assertEqual(target_text("Aonung", "Aonung"), "aonung")
        self.assertEqual(target_text("sAfpIl", "säfpìl"), "säfpìl")

    def test_meta_construction_collates_with_its_prefix(self) -> None:
        self.assertEqual(collation_key(entry("tì-us")), collation_key(entry("tì")))


if __name__ == "__main__":
    unittest.main()
