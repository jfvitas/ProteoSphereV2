from __future__ import annotations

from execution.assets.retention_policy import (
    RetentionAsset,
    build_retention_policy,
)


def test_retention_policy_classifies_preload_cache_and_lazy_assets() -> None:
    policy = build_retention_policy(
        [
            {
                "artifact_kind": "feature",
                "pointer": "cache/features/example.npy",
                "selector": "feature:example",
            },
            {
                "artifact_kind": "structure",
                "pointer": "cache/structures/example.cif",
                "selector": "structure:example",
            },
            {
                "artifact_kind": "other",
                "pointer": "lazy/notes/example.json",
                "selector": "lazy:example",
            },
        ],
        protected_selectors=("package_manifest",),
        notes=("retention smoke",),
    )

    preload, cache, lazy = policy.classify_many(policy.assets)

    assert preload.asset.effective_tier == "preload"
    assert preload.state == "retain"
    assert preload.reason == "preload asset belongs in the hot path"
    assert cache.asset.effective_tier == "cache"
    assert cache.state == "refresh"
    assert lazy.asset.effective_tier == "lazy"
    assert lazy.state == "refresh"
    assert policy.preload_assets[0].pointer == "cache/features/example.npy"
    assert policy.cache_assets[0].pointer == "cache/structures/example.cif"
    assert policy.lazy_assets[0].pointer == "lazy/notes/example.json"


def test_retention_policy_protects_and_pins_assets_against_expiry() -> None:
    policy = build_retention_policy(
        [
            {
                "artifact_kind": "table",
                "pointer": "cache/pinned/table.json",
                "selector": "package_manifest",
                "expires_at": "2000-01-01T00:00:00+00:00",
            },
            {
                "artifact_kind": "table",
                "pointer": "cache/expired/table.json",
                "selector": "normal_table",
                "expires_at": "2000-01-01T00:00:00+00:00",
            },
            RetentionAsset(
                artifact_kind="map",
                pointer="cache/pinned/map.mrc",
                selector="map:pinned",
                pinned=True,
                expires_at="2000-01-01T00:00:00+00:00",
            ),
        ]
    )

    protected, expired, pinned = policy.classify_many(policy.assets)

    assert protected.state == "retain"
    assert protected.expiry_policy == "protected"
    assert "protected artifact" in protected.notes
    assert expired.state == "expire"
    assert expired.expiry_policy == "expiry_window=30d"
    assert pinned.state == "retain"
    assert pinned.expiry_policy == "protected"
    assert policy.protected_assets[0].selector == "package_manifest"


def test_retention_policy_to_dict_is_machine_readable() -> None:
    policy = build_retention_policy(
        [
            {
                "artifact_kind": "other",
                "pointer": "lazy/other/notes.json",
                "selector": "lazy:notes",
                "notes": ["lazy rebuild"],
            }
        ],
        policy_id="retention-policy:test",
        expiry_window_days=14,
    )

    payload = policy.to_dict()

    assert payload["policy_id"] == "retention-policy:test"
    assert payload["asset_count"] == 1
    assert payload["expiry_window_days"] == 14
    assert payload["lazy_assets"][0]["tier"] == "lazy"
    assert payload["lazy_assets"][0]["retention_state"] == "retain"
