"""
Unit tests for the Synthetic Workplace Log Generator.
"""

from src.synthetic_generator import SyntheticWorkplaceLogGenerator
from src.schemas import ChannelType


def test_synthetic_generator_dataset_composition():
    gen = SyntheticWorkplaceLogGenerator(seed=123)
    dataset = gen.generate_full_dataset(samples_per_dept=10)

    assert len(dataset) == 40

    departments = set(m.department for m in dataset)
    expected_depts = {
        "Engineering-Core",
        "Port-Logistics",
        "AI-Research-Labs",
        "Customer-Operations"
    }
    assert departments == expected_depts

    # Check channels used
    channels = set(m.channel for m in dataset)
    assert ChannelType.SLACK in channels
    assert ChannelType.TEAMS in channels

    # Check non-empty contents
    for m in dataset:
        assert len(m.text_content.strip()) > 10
        assert m.sender_id
        assert m.timestamp
