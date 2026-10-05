import csv
import io

import pytest

from backend.app.conversion.engine import (
    ParsingOptions,
    convert,
    detect,
    override,
    parse,
)
from backend.app.conversion.types import ConversionError
from backend.app.conversion.writers import csv_writer


def dataset(text, source="csv", **options):
    return parse(text, source, ParsingOptions(relation="research dataset", **options), 3)


def test_lossless_round_trip():
    rows = [
        ["number", "text", "date"],
        ["12345678901234567890.123456789", "a,b", "2026-01-01"],
        ["1e-20", "line\nbreak", "2026-01-02"],
        [None, "?", "2026-01-03"],
        ["-0.0", "quote' slash\\ é", None],
        ["+001.20", "  spaced  ", "2026-01-04"],
    ]
    source = io.StringIO(newline="")
    csv.writer(source).writerows(rows)
    original = dataset(source.getvalue())
    arff, preview = convert(original, "csv", ParsingOptions())
    reparsed = dataset(arff, "arff")
    assert original.rows == reparsed.rows
    assert [a.name for a in original.attributes] == [a.name for a in reparsed.attributes]
    result, _ = csv_writer(reparsed)
    assert list(csv.reader(io.StringIO(result))) == [[v or "" for v in row] for row in rows]
    assert "@data" in preview


def test_inference_and_missing():
    data = dataset(
        "n,c,d,s\n1,a,2026-01-01,one\n2,b,2026-01-02,two\n3,a,2026-01-03,three\n4,b,2026-01-04,four\n,,,\n"
    )
    assert [a.type for a in data.attributes] == ["numeric", "nominal", "date", "string"]
    assert data.rows[-1] == [None] * 4
    assert data.attributes[1].values == ["a", "b"]


@pytest.mark.parametrize(
    "text,line", [("a,b\n1\n", 2), ("a,a\n1,2\n", 1), ('a,b\n"broken,2', 2), ("", 1)]
)
def test_invalid_csv(text, line):
    with pytest.raises(ConversionError) as error:
        dataset(text)
    assert error.value.errors[0]["line"] == line


def test_csv_options_and_no_header():
    data = dataset("'a;b';4\n'x';5\n", delimiter=";", quote="'", header=False)
    assert data.rows[0] == ["a;b", "4"]
    assert data.attributes[0].name == "attribute_1"


@pytest.mark.parametrize(
    "text",
    [
        "@relation r\n@attribute x numeric\n",
        "@relation r\n@attribute x numeric\n@data\nno\n",
        "@relation r\n@attribute x numeric\n@data\n{0 1}\n",
        "@relation r\n@attribute x {a,b}\n@data\nc\n",
        '@relation r\n@attribute x string\n@data\n"open\n',
        '@relation r\n@attribute x date "yyyy-MM-dd"\n@data\n2026-02-30\n',
        "@relation r\n@attribute x numeric\n@attribute x string\n@data\n1,a\n",
    ],
)
def test_invalid_arff(text):
    with pytest.raises(ConversionError):
        dataset(text, "arff")


def test_arff_comments_quotes_missing_dates():
    data = dataset(
        "% hello\n@RELATION 'r'\n\n@ATTRIBUTE x STRING\n@attribute d date\n@DATA\n% comment\n'?', '2026-01-01T12:30:00'\n?,?\n'a\\nline',?\n",
        "arff",
    )
    assert data.rows == [["?", "2026-01-01T12:30:00"], [None, None], ["a\nline", None]]


def test_override_rejects_inconsistent_type():
    data = dataset("name\nMira\n")
    with pytest.raises(ConversionError):
        override(data, [{"name": "name", "type": "numeric"}])


def test_valid_override():
    data = dataset("name\nMira\n")
    override(data, [{"name": "student", "type": "string"}])
    assert data.attributes[0].name == "student"


def test_detection_and_encoding():
    assert detect("file.csv", b"@relation r\n")[0] == "arff"
    for filename, content in [
        ("file.exe", b"a"),
        ("file.csv", b"\xff"),
        ("file.csv", b"\0"),
    ]:
        with pytest.raises(ConversionError):
            detect(filename, content)


def test_single_column_missing_record_is_preserved():
    data = dataset("name\nMira\n\nArjun\n")
    assert data.rows == [["Mira"], [None], ["Arjun"]]


def test_csv_output_uses_rfc4180_despite_input_options():
    data = dataset("@relation r\n@attribute name string\n@data\n'a,b'\n", "arff")
    output, _ = convert(data, "arff", ParsingOptions(delimiter=";", quote="'"))
    assert output == 'name\r\n"a,b"\r\n'
