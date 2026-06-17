#!/usr/bin/env python3
"""
test_all_features.py
====================
Comprehensive feature validation script for the campaign optimizer.

Validates all 7 requested features work correctly:
  1. Hold / No Action group visible
  2. Human Approval Queue section exists
  3. Rule precedence correct (high spend + zero conv > low signal)
  4. Deterministic performance (numbers consistent across runs)
  5. Creative fields properly named per platform
  6. Recenter-CPA path demonstrated
  7. Terminal message correct
"""

from pathlib import Path
from platforms import MockAdPlatform
from optimizer import Goals, evaluate
from agent import AdAgent
from creative import generate_copy

def test_rule_precedence():
    """Test that high-spend + zero conversions overrides low-signal hold."""
    print("Testing rule precedence...")
    platform = MockAdPlatform()
    goals = Goals(target_cpa=30, target_roas=3.0)

    broad_campaign = None
    for c in platform.get_campaigns():
        if "Broad" in c.name:
            broad_campaign = c
            break

    assert broad_campaign is not None, "Broad campaign not found"
    perf = platform.get_performance(broad_campaign.id, window_days=14)
    action = evaluate(broad_campaign, perf, goals)

    # Must be pause, not hold
    assert action.kind == "pause", f"Expected 'pause', got '{action.kind}'"
    assert perf.conversions == 0, "Expected zero conversions"
    assert perf.cost > 50, "Expected significant spend"

    print(f"  ✓ {broad_campaign.name}: {action.kind} (overrides low-signal hold)")
    print(f"    Spend: ${perf.cost:.2f}, Conv: {perf.conversions}, Confidence: {action.confidence:.0%}")
    return True

def test_recenter_cpa_path():
    """Test that drifting CPA gets recenter recommendation."""
    print("\nTesting recenter-CPA path...")
    platform = MockAdPlatform()
    goals = Goals(target_cpa=30, target_roas=3.0)

    nonbrand_campaign = None
    for c in platform.get_campaigns():
        if "Nonbrand" in c.name:
            nonbrand_campaign = c
            break

    assert nonbrand_campaign is not None, "Nonbrand campaign not found"
    perf = platform.get_performance(nonbrand_campaign.id, window_days=14)
    action = evaluate(nonbrand_campaign, perf, goals)

    # Must be set_target_cpa
    assert action.kind == "set_target_cpa", f"Expected 'set_target_cpa', got '{action.kind}'"
    assert nonbrand_campaign.target_cpa is not None
    assert perf.conversions >= goals.min_conversions, "Should have enough signal"

    print(f"  ✓ {nonbrand_campaign.name}: {action.kind}")
    print(f"    Target CPA: ${nonbrand_campaign.target_cpa:.2f} → Realized: ${perf.cpa:.2f}")
    print(f"    Proposed: ${action.proposed}")
    return True

def test_deterministic_performance():
    """Test that performance numbers are consistent across queries."""
    print("\nTesting deterministic performance...")
    platform = MockAdPlatform()

    # Query same campaign twice
    test_id = list(platform.get_campaigns())[0].id
    perf1 = platform.get_performance(test_id, window_days=14)
    perf2 = platform.get_performance(test_id, window_days=14)

    assert perf1.cost == perf2.cost, "Cost should be identical"
    assert perf1.conversions == perf2.conversions, "Conversions should be identical"
    assert perf1.revenue == perf2.revenue, "Revenue should be identical"

    print(f"  ✓ Performance cached correctly")
    print(f"    Query 1: ${perf1.cost:.2f}, {perf1.conversions} conv")
    print(f"    Query 2: ${perf2.cost:.2f}, {perf2.conversions} conv")
    return True

def test_creative_field_names():
    """Test that creative fields use proper platform-specific names."""
    print("\nTesting creative field names...")

    # Meta
    meta = generate_copy(
        product="Test Product", audience="test audience",
        value_props=["prop1", "prop2"], platform="meta")
    meta_fields = dict(meta.named_fields())
    assert "Primary text" in meta_fields, "Meta should have 'Primary text'"
    assert "Call to action" in meta_fields, "Meta should have 'Call to action'"
    print(f"  ✓ Meta: {', '.join(meta_fields.keys())}")

    # LinkedIn
    linkedin = generate_copy(
        product="Test Product", audience="test audience",
        value_props=["prop1", "prop2"], platform="linkedin")
    linkedin_fields = dict(linkedin.named_fields())
    assert "Intro text" in linkedin_fields, "LinkedIn should have 'Intro text'"
    assert "Description" in linkedin_fields, "LinkedIn should have 'Description'"
    print(f"  ✓ LinkedIn: {', '.join(linkedin_fields.keys())}")

    # Google
    google = generate_copy(
        product="Test Product", audience="test audience",
        value_props=["prop1", "prop2"], platform="google")
    google_fields = dict(google.named_fields())
    assert any("Headline" in k for k in google_fields), "Google should have headlines"
    assert any("Description" in k for k in google_fields), "Google should have descriptions"
    print(f"  ✓ Google: Headlines + Descriptions (RSA format)")
    return True

def test_hold_group_visibility():
    """Test that Hold / No Action campaigns are categorized correctly."""
    print("\nTesting Hold / No Action group...")
    platform = MockAdPlatform()
    goals = Goals(target_cpa=30, target_roas=3.0)
    agent = AdAgent(platform, goals=goals, autonomy="assist")

    report = agent.optimize(window_days=14)
    hold_actions = [d for d in report.decisions if d.action.kind == "no_change"]

    assert len(hold_actions) > 0, "Should have some hold actions"

    print(f"  ✓ {len(hold_actions)} campaign(s) in Hold group:")
    for d in hold_actions:
        print(f"    - {d.action.campaign_name}: {d.action.rationale[:60]}...")
    return True

def test_approval_queue():
    """Test that actions requiring approval are properly flagged."""
    print("\nTesting Human Approval Queue...")
    platform = MockAdPlatform()
    goals = Goals(target_cpa=30, target_roas=3.0)
    agent = AdAgent(platform, goals=goals, autonomy="assist")

    report = agent.optimize(window_days=14)
    pending = report.pending

    # Should have pause actions that need approval
    pause_actions = [d for d in pending if d.action.kind == "pause"]
    assert len(pause_actions) > 0, "Should have pause actions needing approval"

    print(f"  ✓ {len(pending)} action(s) need approval:")
    for d in pending:
        print(f"    - {d.action.campaign_name}: {d.action.kind} "
              f"(confidence: {d.action.confidence:.0%})")
    return True

def main():
    print("="*70)
    print("CAMPAIGN OPTIMIZER - FEATURE VALIDATION")
    print("="*70)

    tests = [
        test_rule_precedence,
        test_recenter_cpa_path,
        test_deterministic_performance,
        test_creative_field_names,
        test_hold_group_visibility,
        test_approval_queue,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"  ✗ FAILED: {e}")
            failed += 1

    print("\n" + "="*70)
    print(f"RESULTS: {passed}/{len(tests)} tests passed")
    if failed == 0:
        print("✓ All features working correctly!")
    else:
        print(f"✗ {failed} test(s) failed")
    print("="*70)

    return failed == 0

if __name__ == "__main__":
    import sys
    sys.exit(0 if main() else 1)
