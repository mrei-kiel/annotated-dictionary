#!/usr/bin/env python3
"""Tests for the derivative list order rule."""

from __future__ import annotations

import unittest
from pathlib import Path

from validate_dictionary import check_derivatives, headword_keys, walk


HEADWORDS = r"""
\Headword{txaw}{\B{txaw}}{\I{[t'aw]} \emph{adj.} raw.}
\Headword{txawew}{\B{txa\-wew}}{\I{["t'a.wEw]} \emph{n.} hunt.}
\Headword{tsun}{\B{tsun}}{\I{[tsun]} \emph{vin.} can.}
\Headword{kxu}{\B{kxu}}{\I{[k'u]} \emph{n.} harm.}
"""


def errors(derivatives: str) -> list[str]:
    source = HEADWORDS + r"\Headword{ta}{\B{ta}}{\I{[ta]} from." + derivatives + "}\n"
    macros = [
        macro
        for macro in walk(source, Path("t.tex"), 0, len(source))
        if macro.complete
    ]
    return [message for _, message in check_derivatives(macros, headword_keys(macros))]


def items(*anchors: str) -> str:
    return "".join(rf"\Derivative{{{anchor}}}{{{anchor}}}{{gloss}}" for anchor in anchors)


class DerivativeOrderTests(unittest.TestCase):
    def test_list_in_grapheme_order_passes(self) -> None:
        self.assertEqual(errors(r"\Derivatives{" + items("kxu", "tsun") + "}"), [])

    def test_list_out_of_order_is_an_error(self) -> None:
        messages = errors(r"\Derivatives{" + items("tsun", "kxu") + "}")
        self.assertEqual(len(messages), 1)
        self.assertIn("'kxu'", messages[0])
        self.assertIn("'tsun'", messages[0])

    def test_ipa_settles_diphthongs(self) -> None:
        self.assertEqual(errors(r"\Derivatives{" + items("txawew", "txaw") + "}"), [])
        self.assertEqual(
            len(errors(r"\Derivatives{" + items("txaw", "txawew") + "}")), 1
        )

    def test_unsorted_list_keeps_its_order(self) -> None:
        self.assertEqual(
            errors(r"\Derivatives[unsorted]{" + items("tsun", "kxu") + "}"), []
        )

    def test_unsorted_mark_on_a_sorted_list_passes(self) -> None:
        self.assertEqual(
            errors(r"\Derivatives[unsorted]{" + items("kxu", "tsun") + "}"), []
        )

    def test_unknown_option_is_an_error(self) -> None:
        messages = errors(r"\Derivatives[sorted]{" + items("kxu", "tsun") + "}")
        self.assertEqual(len(messages), 1)
        self.assertIn("'sorted'", messages[0])


if __name__ == "__main__":
    unittest.main()
