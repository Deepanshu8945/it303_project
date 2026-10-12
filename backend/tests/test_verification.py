import csv
import io
import subprocess
from dataclasses import asdict

import pytest

from backend.app.conversion.engine import ParsingOptions, convert, parse
from backend.app.conversion.types import Attribute, ConversionError, Dataset
from backend.app.conversion.verification import VerificationUnavailable, verify_output


def edge_dataset():
    return Dataset(
        "research é",
        [
            Attribute("number", "numeric"),
            Attribute("text", "string"),
            Attribute("category", "nominal", ["?", "", "a,b"]),
            Attribute("observed", "date", date_format="yyyy-MM-dd"),
        ],
        [
            [
                "12345678901234567890.123456789",
                "comma, apostrophe' quote\" slash\\ é",
                "?",
                "2026-10-11",
            ],
            ["1e-20", "line\r\nbreak\ttab", "", None],
            ["-0.0", "  spaced %  ", "a,b", "2026-01-01"],
            ["+001.20", "?", None, None],
            [None, "", None, None],
        ],
        [1, 2, 3, 4, 5],
    )


def test_real_weka_and_csv_verification():
    data = edge_dataset()
    arff, _ = convert(data, "csv", ParsingOptions())
    result = verify_output(data, arff, "arff")
    assert result["status"] == "passed" and "WEKA" in result["tool"]
    assert result["instance_count"] == 5
    csv_output, _ = convert(data, "arff", ParsingOptions())
    result = verify_output(data, csv_output, "csv")
    assert result["status"] == "passed" and result["warnings"]
    assert list(csv.reader(io.StringIO(csv_output, newline="")))[1][0] == data.rows[0][0]


@pytest.mark.parametrize(
    "pattern,value",
    [
        ("yyyy-MM-dd", "2026-10-11"),
        ("yyyy-MM-dd'T'HH:mm:ss", "2026-10-11T12:34:56"),
        ("yyyy-MM-dd HH:mm:ss", "2026-10-11 12:34:56"),
        ("yyyy-MM-dd'T'HH:mm:ss.SSS", "2026-10-11T12:34:56.123"),
        ("yyyy-MM-dd'T'HH:mm:ssXXX", "2026-10-11T12:34:56+05:30"),
        ("MM/dd/yyyy", "10/11/2026"),
        ("dd/MM/yyyy", "11/10/2026"),
    ],
)
def test_weka_date_formats(pattern, value):
    data = Dataset("dates", [Attribute("date", "date", date_format=pattern)], [[value]], [1])
    output, _ = convert(data, "csv", ParsingOptions())
    assert verify_output(data, output, "arff")["status"] == "passed"


@pytest.mark.parametrize("target", ["csv", "arff"])
@pytest.mark.parametrize("defect", ["value", "name", "order", "missing", "rows"])
def test_changed_output_is_rejected(target, defect):
    data = parse("a,b\n1,x\n2,y\n", "csv", ParsingOptions(relation="r"), 20)
    modified = Dataset(
        data.relation,
        [Attribute(**asdict(a)) for a in data.attributes],
        [list(row) for row in data.rows],
        list(data.lines),
    )
    if defect == "value":
        modified.rows[0][0] = "3"
    elif defect == "name":
        modified.attributes[0].name = "changed"
    elif defect == "order":
        modified.rows.reverse()
    elif defect == "missing":
        modified.rows[0][0] = None
    else:
        modified.rows.pop()
    output, _ = convert(modified, "csv" if target == "arff" else "arff", ParsingOptions())
    with pytest.raises(ConversionError, match="verification failed"):
        verify_output(data, output, target)


def test_malformed_csv_rejected():
    with pytest.raises(ConversionError, match="invalid CSV"):
        verify_output(edge_dataset(), '"unterminated', "csv")


def test_missing_jar_is_not_success(tmp_path):
    data = edge_dataset()
    output, _ = convert(data, "csv", ParsingOptions())
    with pytest.raises(VerificationUnavailable, match="WEKA JAR"):
        verify_output(data, output, "arff", jar=tmp_path / "missing.jar")


@pytest.mark.parametrize("failure", [FileNotFoundError(), subprocess.TimeoutExpired("java", 1)])
def test_java_unavailable_or_timeout(monkeypatch, failure):
    data = edge_dataset()
    output, _ = convert(data, "csv", ParsingOptions())

    def fail(*args, **kwargs):
        raise failure

    monkeypatch.setattr(subprocess, "run", fail)
    with pytest.raises(VerificationUnavailable):
        verify_output(data, output, "arff")


@pytest.mark.parametrize("code,stdout", [(1, ""), (0, "VERIFIED\t999\t4"), (0, "")])
def test_weka_rejection_or_wrong_confirmation(monkeypatch, code, stdout):
    data = edge_dataset()
    output, _ = convert(data, "csv", ParsingOptions())
    monkeypatch.setattr(
        subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a, code, stdout, "")
    )
    with pytest.raises(ConversionError, match="WEKA rejected"):
        verify_output(data, output, "arff")


def test_header_only_outputs():
    data = Dataset("empty", [Attribute("text", "string")], [], [])
    for source, target in [("csv", "arff"), ("arff", "csv")]:
        output, _ = convert(data, source, ParsingOptions())
        assert verify_output(data, output, target)["instance_count"] == 0


def test_verifies_entire_output_beyond_preview():
    data = Dataset(
        "large", [Attribute("number", "numeric")], [[str(i)] for i in range(25)], list(range(25))
    )
    output, preview = convert(data, "csv", ParsingOptions())
    assert "\n24\n" not in preview
    assert verify_output(data, output, "arff")["instance_count"] == 25
    with pytest.raises(ConversionError):
        verify_output(data, output.replace("\n24\n", "\n99\n"), "arff")


def test_weka_independently_detects_changed_value(monkeypatch):
    from backend.app.conversion import verification

    data = Dataset("r", [Attribute("n", "numeric")], [["1"]], [1])
    output, _ = convert(data, "csv", ParsingOptions())
    # Isolate WEKA's comparison from the supplementary lexical check.
    monkeypatch.setattr(verification, "arff_reader", lambda text: data)
    with pytest.raises(ConversionError, match="WEKA rejected"):
        verify_output(data, output.replace("\n1\n", "\n2\n"), "arff")


def test_weka_rejects_numeric_overflow():
    data = Dataset("r", [Attribute("n", "numeric")], [["1e999"]], [1])
    output, _ = convert(data, "csv", ParsingOptions())
    with pytest.raises(ConversionError, match="WEKA rejected"):
        verify_output(data, output, "arff")
