"""OD-011 failing cases for the patching harness and the shard merge.

The harness is exercised on a tiny fake model rather than left untested until
the real run. Two properties matter enough to check arithmetically:

  * a patch written at one row of a batch must not leak into any other row,
    because every construction for a unit shares one batch;
  * a job's replacement values must land at exactly the requested positions.

A leak between rows would silently mix the real construction with its own nulls
and no downstream check could see it.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

torch = pytest.importorskip("torch")

TOOLS = Path(__file__).resolve().parent.parent / "tools"


def load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, TOOLS / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


patch = load("p0_patch", "patch_effect.py")
merge = load("p0_merge", "merge_shards.py")


HIDDEN = 8
VOCAB = 6
SEQ = 5


class Block(torch.nn.Module):
    def __init__(self, bump: float):
        super().__init__()
        self.bump = bump

    def forward(self, hidden, **_):
        return (hidden + self.bump,)


class Inner(torch.nn.Module):
    def __init__(self, n_layers: int):
        super().__init__()
        self.embed_tokens = torch.nn.Embedding(20, HIDDEN)
        self.layers = torch.nn.ModuleList(Block(float(i + 1)) for i in range(n_layers))

    def forward(self, input_ids):
        hidden = self.embed_tokens(input_ids)
        for block in self.layers:
            hidden = block(hidden)[0]
        return hidden


class Tiny(torch.nn.Module):
    """A model with the attribute layout Harness expects and no attention.

    Without attention every position is independent, which is what makes the
    row-isolation and position-targeting assertions exact rather than
    approximate.
    """

    def __init__(self, n_layers: int = 3):
        super().__init__()
        self.model = Inner(n_layers)
        self.head = torch.nn.Linear(HIDDEN, VOCAB, bias=False)

    def forward(self, input_ids):
        hidden = self.model(input_ids)

        class Out:
            pass

        out = Out()
        out.logits = self.head(hidden)
        return out


@pytest.fixture()
def harness():
    torch.manual_seed(0)
    model = Tiny()
    model.eval()
    return patch.Harness(model), model


def test_the_layer_grid_starts_at_the_embedding_output(harness):
    h, _ = harness
    assert h.layers == [-1, 0, 1, 2]
    assert h.n_layers == 3


def test_capture_returns_one_state_per_layer_and_the_last_logit_row(harness):
    h, _ = harness
    ids = torch.arange(SEQ)
    states, last = h.capture(ids)
    assert sorted(states) == [-1, 0, 1, 2]
    for value in states.values():
        assert value.shape == (SEQ, HIDDEN)
    assert last.shape == (VOCAB,)


def test_a_patch_at_one_row_does_not_leak_into_another_row(harness):
    h, _ = harness
    ids = torch.arange(SEQ)
    gather = torch.tensor([0, 1])
    index = torch.tensor([2])
    huge = torch.full((1, HIDDEN), 1000.0)

    jobs = [
        {"layer": -1, "index": index, "values": huge},
        {"layer": -1, "index": index, "values": torch.zeros(1, HIDDEN)},
    ]
    both = h.patched_logit_gap(ids, jobs, gather, 1, batch_size=2)
    apart = h.patched_logit_gap(ids, jobs, gather, 1, batch_size=1)
    assert both == pytest.approx(apart, abs=1e-5)


def test_a_patch_lands_only_at_the_requested_positions(harness):
    h, model = harness
    ids = torch.arange(SEQ)
    seen = {}

    def spy(_module, _inputs, output):
        seen["value"] = output[0].detach().clone()
        return output

    handle = model.model.layers[0].register_forward_hook(spy)
    try:
        h.patched_logit_gap(
            ids,
            [
                {
                    "layer": -1,
                    "index": torch.tensor([1, 3]),
                    "values": torch.full((2, HIDDEN), 7.0),
                }
            ],
            torch.tensor([0, 1]),
            1,
            batch_size=1,
        )
    finally:
        handle.remove()
    # block 0 adds 1.0, so the patched positions must read exactly 8.0
    row = seen["value"][0]
    assert torch.allclose(row[1], torch.full((HIDDEN,), 8.0))
    assert torch.allclose(row[3], torch.full((HIDDEN,), 8.0))
    assert not torch.allclose(row[0], torch.full((HIDDEN,), 8.0))


def test_patching_a_layer_with_its_own_values_changes_nothing(harness):
    h, _ = harness
    ids = torch.arange(SEQ)
    states, last = h.capture(ids)
    gather = torch.tensor([0, 1])
    index = torch.tensor([0, 1, 2])
    baseline = float(last[0] - last[1])
    jobs = [
        {"layer": layer, "index": index, "values": states[layer].index_select(0, index)}
        for layer in h.layers
    ]
    values = h.patched_logit_gap(ids, jobs, gather, 1, batch_size=4)
    for value in values:
        assert value == pytest.approx(baseline, abs=1e-4)


def test_batching_does_not_change_any_result(harness):
    h, _ = harness
    ids = torch.arange(SEQ)
    states, _ = h.capture(ids)
    gather = torch.tensor([0, 1, 2])
    index = torch.tensor([1, 2])
    jobs = [
        {
            "layer": layer,
            "index": index,
            "values": states[layer].index_select(0, index) * scale,
        }
        for layer in h.layers
        for scale in (0.5, 2.0)
    ]
    one = h.patched_logit_gap(ids, jobs, gather, 2, batch_size=1)
    many = h.patched_logit_gap(ids, jobs, gather, 2, batch_size=8)
    assert one == pytest.approx(many, abs=1e-5)


# ------------------------------------------------------------------ seeding


def test_the_seed_does_not_depend_on_python_hash_randomisation():
    # a literal, so a change in stable_seed's definition is visible as a
    # failure rather than absorbed silently
    assert patch.stable_seed("a->b", 0) == patch.stable_seed("a->b", 0)
    assert patch.stable_seed("a->b", 0) != patch.stable_seed("a->b", 1)
    assert patch.stable_seed("a->b", 0) != patch.stable_seed("b->a", 0)
    assert patch.stable_seed("a->b", 0) == 8810281270307266821


def test_the_instrument_under_test_is_not_loaded():
    assert not patch.instrument_under_test_is_loaded()


# -------------------------------------------------------------------- merge


def shard(index, shards=2, **over):
    base = {
        "shard": index,
        "shards": shards,
        "units_file_sha256": "d" * 64,
        "layers": [-1, 0],
        "n_transformer_layers": 1,
        "null_replicates": 5,
        "null_sites": ["CUE", "BRIDGE", "READOUT"],
        "model_dir": "/m",
        "wall_seconds": 10.0 + index,
        "instrument_under_test_imported": False,
        "gpu_uuid_last_twelve": f"gpu{index}",
        "per_unit": [{"unit_id": f"u{index}", "cluster_id": f"c{index}"}],
        "dropped": [],
        "curves": {"REAL": {"BRIDGE": {"0": {f"c{index}": [float(index)]}}}},
    }
    base.update(over)
    return base


def test_merge_concatenates_by_cluster():
    merged = merge.merge([shard(0), shard(1)])
    assert merged["curves"]["REAL"]["BRIDGE"]["0"] == {"c0": [0.0], "c1": [1.0]}
    assert merged["n_units_measured"] == 2
    assert merged["n_clusters"] == 2


def test_merge_refuses_a_frame_digest_mismatch():
    with pytest.raises(merge.MergeError):
        merge.merge([shard(0), shard(1, units_file_sha256="e" * 64)])


def test_merge_refuses_a_layer_grid_mismatch():
    with pytest.raises(merge.MergeError):
        merge.merge([shard(0), shard(1, layers=[-1, 0, 1])])


def test_merge_refuses_a_missing_shard():
    with pytest.raises(merge.MergeError):
        merge.merge([shard(0), shard(0)])


def test_merge_refuses_a_duplicated_unit():
    a = shard(0)
    b = shard(1)
    b["per_unit"] = [{"unit_id": "u0", "cluster_id": "c0"}]
    with pytest.raises(merge.MergeError):
        merge.merge([a, b])


def test_merge_propagates_an_instrument_import_from_any_shard():
    merged = merge.merge([shard(0), shard(1, instrument_under_test_imported=True)])
    assert merged["instrument_under_test_imported"] is True
