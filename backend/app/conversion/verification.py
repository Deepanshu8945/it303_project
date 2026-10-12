"""Verify complete generated output before publishing it for download."""

import base64
import csv
import io
import subprocess
import tempfile
from pathlib import Path

from .readers import arff_reader
from .types import ConversionError

ROOT = Path(__file__).resolve().parents[3]


class VerificationUnavailable(ConversionError):
    pass


def encoded(value):
    return base64.b64encode(value.encode("utf-8")).decode("ascii")


def expected_manifest(dataset):
    lines = [encoded(dataset.relation), str(len(dataset.attributes))]
    for attr in dataset.attributes:
        lines.append(
            "\t".join(
                [
                    encoded(attr.name),
                    attr.type,
                    encoded(attr.date_format or ""),
                    *[encoded(v) for v in attr.values],
                ]
            )
        )
    lines.append(str(len(dataset.rows)))
    lines.extend(
        "\t".join("N" if v is None else "V" + encoded(v) for v in row) for row in dataset.rows
    )
    return "\n".join(lines) + "\n"


def verify_output(dataset, output, target, *, java="java", jar=None, timeout=30):
    warnings = []
    if target == "csv":
        try:
            rows = list(csv.reader(io.StringIO(output, newline=""), strict=True))
        except csv.Error as error:
            raise ConversionError("Output verification failed: invalid CSV.") from error
        expected = [[a.name for a in dataset.attributes]] + [
            ["" if v is None else v for v in row] for row in dataset.rows
        ]
        if rows != expected:
            raise ConversionError("Output verification failed: CSV data or columns changed.")
        if any(v == "" for row in dataset.rows for v in row):
            warnings.append("CSV represents empty strings and missing values as empty fields.")
        tool = "Python CSV reader"
    elif target == "arff":
        # Preserve exact numeric lexemes as well as checking WEKA's parsed values.
        restored = arff_reader(output)
        if (
            restored.relation != dataset.relation
            or restored.attributes != dataset.attributes
            or restored.rows != dataset.rows
        ):
            raise ConversionError("Output verification failed: ARFF schema or data changed.")
        jar = Path(jar) if jar else ROOT / ".runtime/weka-3.8.6.jar"
        if not jar.is_file():
            raise VerificationUnavailable(
                "Output verification unavailable: install the WEKA JAR configured by WEKA_JAR."
            )
        with tempfile.TemporaryDirectory(prefix="converter-verification-") as directory:
            candidate = Path(directory) / "output.arff"
            expected_file = Path(directory) / "expected.txt"
            candidate.write_bytes(output.encode("utf-8"))
            expected_file.write_text(expected_manifest(dataset), encoding="utf-8")
            try:
                result = subprocess.run(
                    [
                        java,
                        "-Dfile.encoding=UTF-8",
                        "-cp",
                        str(jar.resolve()),
                        str(ROOT / "scripts/WekaCheck.java"),
                        "--verify",
                        str(candidate),
                        str(expected_file),
                    ],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=timeout,
                    check=False,
                )
            except (OSError, subprocess.TimeoutExpired) as error:
                raise VerificationUnavailable(
                    "Output verification unavailable: Java 11+ is required and WEKA must finish within the timeout."
                ) from error
        confirmation = f"VERIFIED\t{len(dataset.rows)}\t{len(dataset.attributes)}"
        if result.returncode != 0 or result.stdout.strip() != confirmation:
            raise ConversionError(
                "Output verification failed: WEKA rejected the generated file or found changed data."
            )
        tool = "WEKA + exact data comparison"
    else:
        raise ConversionError("Output verification failed: unsupported target format.")
    return {
        "status": "passed",
        "tool": tool,
        "instance_count": len(dataset.rows),
        "attribute_count": len(dataset.attributes),
        "warnings": warnings,
    }
