"""ACAL round-trip verifier.

Compresses an AICP message to ACAL, decompresses it back, and compares
the original against the round-tripped result to detect data loss.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .converter import (
    acal_to_aicp,
    aicp_to_acal,
    _parse_aicp_raw,
    _normalize,
)


@dataclass
class VerificationResult:
    """Result of an ACAL round-trip verification."""

    passed: bool
    original_size: int
    acal_size: int
    reconstructed_size: int
    compression_ratio: float
    field_mismatches: list[dict] = field(default_factory=list)
    acal_text: str = ""
    error: Optional[str] = None

    def to_dict(self) -> dict:
        """Serialize to a JSON-compatible dictionary."""
        return {
            "passed": self.passed,
            "original_size": self.original_size,
            "acal_size": self.acal_size,
            "reconstructed_size": self.reconstructed_size,
            "compression_ratio": round(self.compression_ratio, 4),
            "compression_pct": round((1 - self.compression_ratio) * 100, 1),
            "field_mismatches": self.field_mismatches,
            "acal_text": self.acal_text,
            "error": self.error,
        }


# Fields that carry semantic meaning and must survive the round trip.
_SEMANTIC_FIELDS = [
    "$TYPE", "$ID", "$FROM", "$TO", "$STATUS",
    "$ROLE", "PROJECT",
]

# Fields compared only when present in the original.
_OPTIONAL_FIELDS = ["$REF", "$TASK", "$INTENT", "$PRIORITY", "DOMAIN"]


def verify_roundtrip(aicp_text: str) -> VerificationResult:
    """Verify that an AICP message survives ACAL compression and expansion.

    Steps:
        1. Parse original AICP headers.
        2. Compress to ACAL.
        3. Expand ACAL back to AICP (preserving $SEQ and $TIME).
        4. Parse reconstructed headers.
        5. Compare all semantic fields.

    Args:
        aicp_text: The original AICP message string.

    Returns:
        A VerificationResult with pass/fail, compression ratio, and any
        field-level mismatches.
    """
    original_size = len(aicp_text.encode("utf-8"))

    # Guard against empty input
    if not aicp_text.strip():
        return VerificationResult(
            passed=False,
            original_size=0,
            acal_size=0,
            reconstructed_size=0,
            compression_ratio=1.0,
            error="Empty AICP message",
        )

    try:
        orig_headers, orig_payload, _ = _parse_aicp_raw(aicp_text)
    except Exception as exc:
        return VerificationResult(
            passed=False,
            original_size=original_size,
            acal_size=0,
            reconstructed_size=0,
            compression_ratio=1.0,
            error=f"Failed to parse original AICP: {exc}",
        )

    # Compress
    try:
        acal_text = aicp_to_acal(aicp_text)
    except Exception as exc:
        return VerificationResult(
            passed=False,
            original_size=original_size,
            acal_size=0,
            reconstructed_size=0,
            compression_ratio=1.0,
            error=f"Compression failed: {exc}",
        )

    acal_size = len(acal_text.encode("utf-8"))

    # Expand back, preserving $SEQ and $TIME so they don't cause false diffs
    seq = int(orig_headers.get("$SEQ", 0)) if "$SEQ" in orig_headers else None
    timestamp = orig_headers.get("$TIME")

    try:
        reconstructed = acal_to_aicp(acal_text, seq=seq, timestamp=timestamp)
    except Exception as exc:
        return VerificationResult(
            passed=False,
            original_size=original_size,
            acal_size=acal_size,
            reconstructed_size=0,
            compression_ratio=acal_size / original_size if original_size else 1.0,
            acal_text=acal_text,
            error=f"Expansion failed: {exc}",
        )

    reconstructed_size = len(reconstructed.encode("utf-8"))
    compression_ratio = acal_size / original_size if original_size else 1.0

    # Parse reconstructed
    try:
        recon_headers, recon_payload, _ = _parse_aicp_raw(reconstructed)
    except Exception as exc:
        return VerificationResult(
            passed=False,
            original_size=original_size,
            acal_size=acal_size,
            reconstructed_size=reconstructed_size,
            compression_ratio=compression_ratio,
            acal_text=acal_text,
            error=f"Failed to parse reconstructed AICP: {exc}",
        )

    # Compare fields
    mismatches: list[dict] = []

    for fld in _SEMANTIC_FIELDS:
        orig_val = _normalize(orig_headers.get(fld, ""))
        recon_val = _normalize(recon_headers.get(fld, ""))
        if orig_val != recon_val:
            mismatches.append({
                "field": fld,
                "original": orig_headers.get(fld, ""),
                "reconstructed": recon_headers.get(fld, ""),
            })

    for fld in _OPTIONAL_FIELDS:
        if fld in orig_headers:
            orig_val = orig_headers[fld].strip()
            recon_val = recon_headers.get(fld, "").strip()
            if orig_val != recon_val:
                mismatches.append({
                    "field": fld,
                    "original": orig_val,
                    "reconstructed": recon_val,
                })

    passed = len(mismatches) == 0

    return VerificationResult(
        passed=passed,
        original_size=original_size,
        acal_size=acal_size,
        reconstructed_size=reconstructed_size,
        compression_ratio=compression_ratio,
        field_mismatches=mismatches,
        acal_text=acal_text,
    )
