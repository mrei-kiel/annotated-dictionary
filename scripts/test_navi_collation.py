#!/usr/bin/env python3
"""Focused tests for Na'vi grapheme collation."""

from __future__ import annotations

import unittest

from navi_collation import collation_key, graphemes, headword_word, main_ipa


class CollationTests(unittest.TestCase):
    def test_diphthong_is_one_grapheme(self) -> None:
        self.assertEqual(graphemes("'awve", '"Paw.vE'), ("'", "aw", "v", "e"))

    def test_syllable_boundary_splits_apparent_diphthong(self) -> None:
        self.assertEqual(graphemes("txawew", '"t\'a.wEw'), ("tx", "a", "w", "ew"))

    def test_split_sequence_sorts_before_diphthong(self) -> None:
        self.assertLess(
            collation_key("txawew", '"t\'a.wEw'), collation_key("txaw", "t'aw")
        )

    def test_diphthongs_are_resolved_in_later_syllables(self) -> None:
        self.assertEqual(
            graphemes("tìtxanew", 'tI."t\'a.nEw'),
            ("t", "ì", "tx", "a", "n", "ew"),
        )
        self.assertLess(
            collation_key("tìtxanew", 'tI."t\'a.nEw'),
            collation_key("tìtxaw", 'tI."t\'aw'),
        )

    def test_consonant_multigraphs_are_indivisible(self) -> None:
        self.assertEqual(
            graphemes("ngaru txantsan ll rr"),
            (
                "ng", "a", "r", "u", " ", "tx", "a", "n", "ts", "a", "n",
                " ", "ll", " ", "rr",
            ),
        )

    def test_authoring_markers_do_not_affect_order(self) -> None:
        self.assertEqual(collation_key("-a+2"), collation_key("a"))

    def test_meta_construction_collates_with_its_prefix(self) -> None:
        self.assertEqual(collation_key("tì-us"), collation_key("tì"))


class HeadwordTests(unittest.TestCase):
    def test_target_substitutions_are_decoded_from_the_display(self) -> None:
        self.assertEqual(headword_word("sAfpIl", r"\B{säf\-pìl}"), "säfpìl")

    def test_real_capitals_are_kept_as_letters(self) -> None:
        self.assertEqual(headword_word("Aonung", r"\B{A\-o\-nung}"), "aonung")

    def test_affix_markers_outside_the_bold_text_are_ignored(self) -> None:
        self.assertEqual(headword_word("ay+", r"\B{ay}\texttt{+}"), "ay+")

    def test_main_ipa_is_the_first_ipa_argument(self) -> None:
        self.assertEqual(
            main_ipa(r"""\I{["t'a.wEw]} \emph{n.} or \I{[t'aw]}"""), "[\"t'a.wEw]"
        )

    def test_body_without_ipa_has_none(self) -> None:
        self.assertIsNone(main_ipa(r"\emph{n.} cf. \Ipsum"))


if __name__ == "__main__":
    unittest.main()
