"""Tests for the Context Kernel loader module."""

import os
import sys
import textwrap
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

# Ensure src is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from kernel.loader import KernelLoader, KernelData, KERNEL_SECTIONS, MAX_KERNEL_TOKENS


# =====================================================================
# Fixtures — synthetic kernel content
# =====================================================================

VALID_KERNEL = textwrap.dedent("""\
    # CONTEXT KERNEL: Test Kernel
    # Version: 1.0 | Updated: 2026-04-15 | Task: Unit Testing

    ---PROTO---

    ACAL v0.1 reference card (abbreviated for tests).

    ---ROSTER---

    P = Pharos | LC | Lead Coder | Anthropic / Claude

    ---STATE---

    Test kernel: IN PROGRESS

    ---MEMORY---

    [2026-04-15] Created for unit-test suite.

    ---DICT---

    TK = Test Kernel

    ---NEXT_STEPS---

    1. [P] Ensure loader parses this correctly. Status: PENDING
""")


MINIMAL_KERNEL = textwrap.dedent("""\
    # CONTEXT KERNEL: Minimal
    # Version: 0.1 | Updated: 2026-04-15 | Task: Minimal Test

    ---PROTO---
    proto
    ---ROSTER---
    roster
    ---STATE---
    state
    ---MEMORY---
    memory
    ---DICT---
    dict
    ---NEXT_STEPS---
    steps
""")


MISSING_SECTION_KERNEL = textwrap.dedent("""\
    # CONTEXT KERNEL: Broken
    # Version: 0.1 | Updated: 2026-04-15 | Task: Missing Section

    ---PROTO---
    proto
    ---ROSTER---
    roster
    ---STATE---
    state
    ---MEMORY---
    memory
    ---DICT---
    dict
""")

MISSING_HEADER_KERNEL = textwrap.dedent("""\
    # Version: 0.1 | Updated: 2026-04-15 | Task: No Header

    ---PROTO---
    proto
    ---ROSTER---
    roster
    ---STATE---
    state
    ---MEMORY---
    memory
    ---DICT---
    dict
    ---NEXT_STEPS---
    steps
""")


@pytest.fixture
def kernels_dir(tmp_path):
    """Create a temp kernels directory with a valid kernel file."""
    d = tmp_path / "kernels"
    d.mkdir()
    (d / "kernel-test.md").write_text(VALID_KERNEL, encoding="utf-8")
    return d


@pytest.fixture
def loader(kernels_dir):
    return KernelLoader(kernels_dir)


# =====================================================================
# Discovery
# =====================================================================


class TestDiscovery:
    """Test kernel file discovery."""

    def test_list_kernels_finds_valid_files(self, kernels_dir):
        loader = KernelLoader(kernels_dir)
        assert loader.list_kernels() == ["test"]

    def test_list_kernels_ignores_non_kernel_files(self, kernels_dir):
        (kernels_dir / "readme.md").write_text("not a kernel")
        (kernels_dir / "notes.txt").write_text("also not")
        loader = KernelLoader(kernels_dir)
        assert loader.list_kernels() == ["test"]

    def test_list_kernels_multiple(self, kernels_dir):
        (kernels_dir / "kernel-alpha.md").write_text(MINIMAL_KERNEL)
        (kernels_dir / "kernel-beta.md").write_text(MINIMAL_KERNEL)
        loader = KernelLoader(kernels_dir)
        assert loader.list_kernels() == ["alpha", "beta", "test"]

    def test_list_kernels_empty_dir(self, tmp_path):
        d = tmp_path / "empty"
        d.mkdir()
        loader = KernelLoader(d)
        assert loader.list_kernels() == []

    def test_list_kernels_missing_dir(self, tmp_path):
        loader = KernelLoader(tmp_path / "nonexistent")
        assert loader.list_kernels() == []


# =====================================================================
# Loading a valid kernel
# =====================================================================


class TestLoadValid:
    """Test loading and parsing a well-formed kernel."""

    def test_load_returns_kernel_data(self, loader):
        kernel = loader.load("test")
        assert isinstance(kernel, KernelData)

    def test_name(self, loader):
        assert loader.load("test").name == "test"

    def test_label(self, loader):
        assert loader.load("test").label == "Test Kernel"

    def test_version(self, loader):
        assert loader.load("test").version == "1.0"

    def test_updated(self, loader):
        assert loader.load("test").updated == "2026-04-15"

    def test_task(self, loader):
        assert loader.load("test").task == "Unit Testing"

    def test_file_path_set(self, loader):
        k = loader.load("test")
        assert k.file_path.endswith("kernel-test.md")

    def test_loaded_at_is_recent(self, loader):
        k = loader.load("test")
        assert k.loaded_at is not None
        age = (datetime.now(timezone.utc) - k.loaded_at).total_seconds()
        assert age < 5

    def test_token_estimate_positive(self, loader):
        k = loader.load("test")
        assert k.token_estimate > 0

    def test_raw_content_preserved(self, loader):
        k = loader.load("test")
        assert "CONTEXT KERNEL: Test Kernel" in k.raw

    def test_to_prompt_returns_raw(self, loader):
        k = loader.load("test")
        assert k.to_prompt() == k.raw


# =====================================================================
# Section parsing
# =====================================================================


class TestSectionParsing:
    """Test that all six sections are correctly extracted."""

    def test_all_sections_present(self, loader):
        k = loader.load("test")
        for section in KERNEL_SECTIONS:
            assert section in k.sections, f"Missing section: {section}"

    def test_proto_content(self, loader):
        k = loader.load("test")
        assert "ACAL v0.1" in k.proto

    def test_roster_content(self, loader):
        k = loader.load("test")
        assert "Pharos" in k.roster

    def test_state_content(self, loader):
        k = loader.load("test")
        assert "IN PROGRESS" in k.state

    def test_memory_content(self, loader):
        k = loader.load("test")
        assert "2026-04-15" in k.memory

    def test_dict_content(self, loader):
        k = loader.load("test")
        assert "TK" in k.dict_section

    def test_next_steps_content(self, loader):
        k = loader.load("test")
        assert "PENDING" in k.next_steps

    def test_sections_are_stripped(self, loader):
        """Section text should not have leading/trailing blank lines."""
        k = loader.load("test")
        for sec_name, text in k.sections.items():
            assert not text.startswith("\n"), f"{sec_name} starts with newline"
            assert not text.endswith("\n"), f"{sec_name} ends with newline"

    def test_minimal_kernel_parses(self, kernels_dir):
        (kernels_dir / "kernel-mini.md").write_text(MINIMAL_KERNEL)
        loader = KernelLoader(kernels_dir)
        k = loader.load("mini")
        assert k.proto == "proto"
        assert k.roster == "roster"
        assert k.state == "state"


# =====================================================================
# Handling missing / malformed kernels
# =====================================================================


class TestMalformed:
    """Test error handling for bad or missing kernels."""

    def test_missing_file_raises(self, loader):
        with pytest.raises(FileNotFoundError, match="no-such-kernel"):
            loader.load("no-such-kernel")

    def test_missing_section_raises(self, kernels_dir):
        (kernels_dir / "kernel-broken.md").write_text(MISSING_SECTION_KERNEL)
        loader = KernelLoader(kernels_dir)
        with pytest.raises(ValueError, match="NEXT_STEPS"):
            loader.load("broken")

    def test_missing_header_raises(self, kernels_dir):
        (kernels_dir / "kernel-noheader.md").write_text(MISSING_HEADER_KERNEL)
        loader = KernelLoader(kernels_dir)
        with pytest.raises(ValueError, match="header"):
            loader.load("noheader")

    def test_empty_file_raises(self, kernels_dir):
        (kernels_dir / "kernel-empty.md").write_text("")
        loader = KernelLoader(kernels_dir)
        with pytest.raises(ValueError):
            loader.load("empty")


# =====================================================================
# Staleness detection
# =====================================================================


class TestStaleness:
    """Test kernel age tracking and staleness."""

    def test_freshly_loaded_not_stale(self, loader):
        k = loader.load("test")
        assert not k.is_stale()

    def test_stale_after_threshold(self):
        k = KernelData(
            name="old",
            loaded_at=datetime.now(timezone.utc) - timedelta(seconds=600),
        )
        assert k.is_stale(max_age_seconds=300)

    def test_not_stale_within_threshold(self):
        k = KernelData(
            name="recent",
            loaded_at=datetime.now(timezone.utc) - timedelta(seconds=10),
        )
        assert not k.is_stale(max_age_seconds=300)

    def test_no_loaded_at_is_stale(self):
        k = KernelData(name="never")
        assert k.is_stale()

    def test_age_seconds(self):
        k = KernelData(
            name="timed",
            loaded_at=datetime.now(timezone.utc) - timedelta(seconds=42),
        )
        assert 40 <= k.age_seconds() <= 45


# =====================================================================
# Cache behaviour
# =====================================================================


class TestCache:
    """Test in-memory caching of loaded kernels."""

    def test_second_load_returns_cached(self, loader):
        k1 = loader.load("test")
        k2 = loader.load("test")
        assert k1 is k2  # same object

    def test_force_bypasses_cache(self, loader):
        k1 = loader.load("test")
        k2 = loader.load("test", force=True)
        assert k1 is not k2

    def test_invalidate_clears_single(self, loader):
        loader.load("test")
        loader.invalidate("test")
        assert "test" not in loader._cache

    def test_invalidate_all(self, loader, kernels_dir):
        (kernels_dir / "kernel-other.md").write_text(MINIMAL_KERNEL)
        loader.load("test")
        loader.load("other")
        loader.invalidate_all()
        assert len(loader._cache) == 0


# =====================================================================
# Budget check
# =====================================================================


class TestBudget:
    """Test the token-budget check."""

    def test_small_kernel_within_budget(self, loader):
        k = loader.load("test")
        result = loader.check_budget(k)
        assert result["within_budget"] is True
        assert "warning" not in result

    def test_large_kernel_over_budget(self, kernels_dir):
        # Create a kernel with >8K tokens worth of text (~32K chars)
        big_section = "x " * 20000
        big_kernel = (
            "# CONTEXT KERNEL: Big\n"
            "# Version: 1.0 | Updated: 2026-04-15 | Task: Big Test\n\n"
            "---PROTO---\n" + big_section + "\n"
            "---ROSTER---\nroster\n"
            "---STATE---\nstate\n"
            "---MEMORY---\nmemory\n"
            "---DICT---\ndict\n"
            "---NEXT_STEPS---\nsteps\n"
        )
        (kernels_dir / "kernel-big.md").write_text(big_kernel)
        loader = KernelLoader(kernels_dir)
        k = loader.load("big")
        result = loader.check_budget(k)
        assert result["within_budget"] is False
        assert "warning" in result


# =====================================================================
# Integration — load the real kernel-acal-dev.md if present
# =====================================================================


class TestRealKernel:
    """Smoke test against the actual kernel file in the repo."""

    REAL_KERNELS = Path(__file__).resolve().parent.parent / "kernels"

    @pytest.mark.skipif(
        not (Path(__file__).resolve().parent.parent / "kernels" / "kernel-acal-dev.md").exists(),
        reason="Real kernel file not present",
    )
    def test_load_acal_dev(self):
        loader = KernelLoader(self.REAL_KERNELS)
        k = loader.load("acal-dev")
        assert k.label == "ACAL Development"
        assert k.version == "1.0"
        assert len(k.sections) == 6
        for sec in KERNEL_SECTIONS:
            assert sec in k.sections
        # Should be well within budget
        budget = loader.check_budget(k)
        assert budget["within_budget"] is True
