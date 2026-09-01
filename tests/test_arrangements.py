from itertools import permutations

import pytest

from ucs_contracts import ContractValidationError
from ucs_contracts.arrangements import (
    validate_target_positions,
)


@pytest.mark.parametrize(
    "positions",
    permutations(("front_left", "front_center", "front_right")),
)
def test_all_six_target_arrangements_are_accepted(
    positions: tuple[str, str, str],
) -> None:
    payload = dict(zip(("E", "B", "H"), positions))

    arrangement = validate_target_positions(payload)

    assert arrangement.model_dump(mode="json") == payload


def test_duplicate_target_position_is_rejected() -> None:
    payload = {
        "E": "front_left",
        "B": "front_left",
        "H": "front_right",
    }

    with pytest.raises(ContractValidationError):
        validate_target_positions(payload)


@pytest.mark.parametrize(
    "payload",
    [
        {"E": "front_left", "B": "front_center"},
        {
            "E": "front_left",
            "B": "front_center",
            "H": "front_right",
            "L": "front_left",
        },
        {
            "E": "back_left",
            "B": "front_center",
            "H": "front_right",
        },
    ],
    ids=["missing-animal", "unknown-animal", "internal-position"],
)
def test_invalid_target_mappings_are_rejected(
    payload: dict[str, str],
) -> None:
    with pytest.raises(ContractValidationError):
        validate_target_positions(payload)
