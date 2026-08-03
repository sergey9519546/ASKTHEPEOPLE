"""Tests for Big Five personality traits and OASIS interop."""

import random

import pytest

from app.services.big_five import (
    TRAITS,
    BigFive,
    adoption_threshold,
    clamp,
    innovativeness,
    loss_aversion_lambda,
    sample_population,
    to_mbti_code,
)


class TestBigFiveValidation:
    def test_defaults_are_population_midpoint(self):
        traits = BigFive()
        for trait in TRAITS:
            assert getattr(traits, trait) == 50.0

    def test_rejects_out_of_range_high(self):
        with pytest.raises(ValueError, match="openness"):
            BigFive(openness=101.0)

    def test_rejects_out_of_range_low(self):
        with pytest.raises(ValueError, match="neuroticism"):
            BigFive(neuroticism=-1.0)

    def test_rejects_non_numeric(self):
        with pytest.raises(TypeError, match="extraversion"):
            BigFive(extraversion="high")

    def test_boundary_values_allowed(self):
        assert BigFive(openness=0.0).openness == 0.0
        assert BigFive(openness=100.0).openness == 100.0

    def test_is_frozen(self):
        traits = BigFive()
        with pytest.raises(Exception):
            traits.openness = 90.0


class TestRoundTrip:
    def test_to_dict_has_all_five_traits(self):
        data = BigFive().to_dict()
        assert set(data) == set(TRAITS)

    def test_round_trip_preserves_values(self):
        original = BigFive(openness=71.5, neuroticism=12.25)
        assert BigFive.from_dict(original.to_dict()) == original

    def test_from_dict_none_and_empty_return_none(self):
        assert BigFive.from_dict(None) is None
        assert BigFive.from_dict({}) is None

    def test_from_dict_ignores_unrelated_keys(self):
        traits = BigFive.from_dict({"openness": 80.0, "mbti": "INTJ", "age": 40})
        assert traits is not None
        assert traits.openness == 80.0
        # Unspecified traits fall back to the population midpoint.
        assert traits.neuroticism == 50.0

    def test_from_dict_all_none_values_returns_none(self):
        assert BigFive.from_dict({t: None for t in TRAITS}) is None


class TestClamp:
    def test_clamps_both_directions(self):
        assert clamp(-20.0) == 0.0
        assert clamp(160.0) == 100.0
        assert clamp(42.0) == 42.0


class TestJitter:
    def test_jitter_stays_in_range_even_at_extremes(self):
        rng = random.Random(1234)
        extreme = BigFive(**{t: 99.0 for t in TRAITS})
        for _ in range(200):
            extreme = extreme.jitter(spread=25.0, rng=rng)
            for trait in TRAITS:
                assert 0.0 <= getattr(extreme, trait) <= 100.0

    def test_jitter_actually_changes_values(self):
        rng = random.Random(7)
        base = BigFive()
        assert base.jitter(spread=10.0, rng=rng) != base

    def test_jitter_is_deterministic_for_seeded_rng(self):
        a = BigFive().jitter(spread=10.0, rng=random.Random(99))
        b = BigFive().jitter(spread=10.0, rng=random.Random(99))
        assert a == b


class TestSamplePopulation:
    def test_sampled_values_always_in_range(self):
        rng = random.Random(2024)
        for _ in range(500):
            traits = sample_population(rng=rng)
            for trait in TRAITS:
                assert 0.0 <= getattr(traits, trait) <= 100.0

    def test_sample_mean_is_near_population_centre(self):
        rng = random.Random(11)
        samples = [sample_population(rng=rng) for _ in range(2000)]
        mean_openness = sum(s.openness for s in samples) / len(samples)
        # Clamping pulls the mean slightly inward; 50 +/- 3 is a fair band.
        assert 47.0 < mean_openness < 53.0

    def test_sampling_produces_variation(self):
        rng = random.Random(5)
        values = {sample_population(rng=rng).openness for _ in range(50)}
        assert len(values) > 40


class TestMbtiInterop:
    """OASIS indexes profile["other_info"]["mbti"] unconditionally, so this must
    always yield a valid 4-letter code."""

    def test_always_four_letters(self):
        rng = random.Random(3)
        for _ in range(300):
            code = to_mbti_code(sample_population(rng=rng))
            assert len(code) == 4

    def test_letters_come_from_valid_alphabet(self):
        rng = random.Random(4)
        for _ in range(300):
            code = to_mbti_code(sample_population(rng=rng))
            assert code[0] in "EI"
            assert code[1] in "NS"
            assert code[2] in "FT"
            assert code[3] in "JP"

    def test_high_traits_map_to_enfj(self):
        high = BigFive(
            openness=90.0,
            conscientiousness=90.0,
            extraversion=90.0,
            agreeableness=90.0,
            neuroticism=50.0,
        )
        assert to_mbti_code(high) == "ENFJ"

    def test_low_traits_map_to_istp(self):
        low = BigFive(
            openness=10.0,
            conscientiousness=10.0,
            extraversion=10.0,
            agreeableness=10.0,
            neuroticism=50.0,
        )
        assert to_mbti_code(low) == "ISTP"

    def test_neuroticism_does_not_affect_code(self):
        """Neuroticism has no MBTI counterpart; the mapping must ignore it."""
        base = dict(
            openness=70.0, conscientiousness=70.0, extraversion=70.0, agreeableness=70.0
        )
        assert to_mbti_code(BigFive(**base, neuroticism=5.0)) == to_mbti_code(
            BigFive(**base, neuroticism=95.0)
        )

    def test_mapping_is_lossy_many_profiles_share_a_code(self):
        a = to_mbti_code(BigFive(openness=99.0, conscientiousness=99.0,
                                 extraversion=99.0, agreeableness=99.0))
        b = to_mbti_code(BigFive(openness=51.0, conscientiousness=51.0,
                                 extraversion=51.0, agreeableness=51.0))
        assert a == b, "distinct trait profiles collapsing to one code demonstrates lossiness"


class TestInnovativeness:
    def test_openness_dominates_extraversion(self):
        open_only = BigFive(openness=100.0, extraversion=0.0)
        extra_only = BigFive(openness=0.0, extraversion=100.0)
        assert innovativeness(open_only) > innovativeness(extra_only)

    def test_monotonic_in_openness(self):
        scores = [innovativeness(BigFive(openness=float(o))) for o in range(0, 101, 10)]
        assert scores == sorted(scores)

    def test_output_within_scale(self):
        rng = random.Random(6)
        for _ in range(200):
            assert 0.0 <= innovativeness(sample_population(rng=rng)) <= 100.0


class TestLossAversion:
    def test_population_average_matches_canonical_estimate(self):
        """Tversky & Kahneman's median lambda is ~2.25."""
        assert loss_aversion_lambda(BigFive()) == pytest.approx(2.25, abs=1e-6)

    def test_higher_neuroticism_increases_loss_aversion(self):
        calm = loss_aversion_lambda(BigFive(neuroticism=10.0))
        anxious = loss_aversion_lambda(BigFive(neuroticism=90.0))
        assert anxious > calm

    def test_stays_in_defensible_band(self):
        lo = loss_aversion_lambda(BigFive(neuroticism=0.0))
        hi = loss_aversion_lambda(BigFive(neuroticism=100.0))
        assert 1.7 <= lo < 2.25 < hi <= 2.8

    def test_only_neuroticism_matters(self):
        a = loss_aversion_lambda(BigFive(neuroticism=60.0, openness=10.0))
        b = loss_aversion_lambda(BigFive(neuroticism=60.0, openness=90.0))
        assert a == b


class TestAdoptionThreshold:
    def test_innovator_needs_almost_no_social_proof(self):
        innovator = BigFive(openness=100.0, extraversion=100.0)
        assert adoption_threshold(innovator) == pytest.approx(0.0, abs=1e-6)

    def test_laggard_needs_near_total_social_proof(self):
        laggard = BigFive(openness=0.0, extraversion=0.0)
        assert adoption_threshold(laggard) == pytest.approx(1.0, abs=1e-6)

    def test_inverse_of_innovativeness(self):
        rng = random.Random(8)
        for _ in range(100):
            traits = sample_population(rng=rng)
            assert adoption_threshold(traits) == pytest.approx(
                1.0 - innovativeness(traits) / 100.0, abs=1e-4
            )

    def test_always_a_valid_fraction(self):
        rng = random.Random(9)
        for _ in range(200):
            assert 0.0 <= adoption_threshold(sample_population(rng=rng)) <= 1.0
