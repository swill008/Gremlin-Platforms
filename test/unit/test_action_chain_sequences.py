# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

from xml.etree import ElementTree

from action_plugins.chain import ChainData
from action_plugins.description import DescriptionData
from gremlin.profile import Library
from gremlin.types import InputType


def _reload(chain: ChainData, library: Library) -> ChainData:
    loaded = ChainData(InputType.JoystickButton)
    loaded._from_xml(
        ElementTree.fromstring(ElementTree.tostring(chain._to_xml())), library
    )
    return loaded


def test_empty_sequence_in_the_middle_keeps_its_place() -> None:
    # Reading only filled chain-N entries dropped the empty one and shifted the rest.
    library = Library()
    first, third = DescriptionData(), DescriptionData()
    library.add_action(first)
    library.add_action(third)
    chain = ChainData(InputType.JoystickButton)
    chain.chain_sequences = [[first], [], [third]]
    loaded = _reload(chain, library)
    assert [[a.id for a in seq] for seq in loaded.chain_sequences] == [
        [first.id],
        [],
        [third.id],
    ]


def test_new_chain_keeps_its_empty_sequence() -> None:
    loaded = _reload(ChainData(InputType.JoystickButton), Library())
    assert loaded.chain_sequences == [[]]
