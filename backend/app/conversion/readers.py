import csv
import io
import re

import arff

from .inference import infer
from .types import Attribute, ConversionError, Dataset
from .validation import DATE_FORMATS, validate

csv.field_size_limit(50 * 1024 * 1024)


def csv_reader(text, options, threshold):
    reader = csv.reader(
        io.StringIO(text, newline=""),
        delimiter=options.delimiter,
        quotechar=options.quote,
        strict=True,
    )
    rows, lines = [], []
    try:
        for row in reader:
            rows.append([v if v != "" else None for v in row] if row else [None])
            lines.append(reader.line_num)
    except csv.Error as error:
        raise ConversionError(str(error), reader.line_num) from error
    if not rows:
        raise ConversionError("The file is empty.")
    if options.header:
        header_line = lines[0]
        names = [v or "" for v in rows.pop(0)]
        lines.pop(0)
    else:
        header_line = 1
        names = [f"attribute_{i + 1}" for i in range(len(rows[0]))]
    if not all(n.strip() for n in names) or len(set(names)) != len(names):
        raise ConversionError("Header names must be nonempty and unique.", header_line)
    for row, line in zip(rows, lines):
        if len(row) != len(names):
            raise ConversionError(f"Expected {len(names)} fields, found {len(row)}.", line)
    dataset = Dataset(options.relation, infer(names, rows, threshold), rows, lines)
    validate(dataset)
    return dataset


def tokens(line, line_number):
    """Keep numeric lexemes intact and distinguish quoted '?' from missing data."""
    values, pos = [], 0
    while pos < len(line):
        while pos < len(line) and line[pos].isspace():
            pos += 1
        if pos == len(line) or line[pos] == "%":
            break
        quoted = line[pos] in "\"'"
        value = ""
        if quoted:
            quote = line[pos]
            pos += 1
            while pos < len(line) and line[pos] != quote:
                char = line[pos]
                if char == "\\":
                    pos += 1
                    if pos >= len(line):
                        raise ConversionError("Unterminated escape sequence.", line_number)
                    char = {"n": "\n", "r": "\r", "t": "\t"}.get(line[pos], line[pos])
                value += char
                pos += 1
            if pos >= len(line):
                raise ConversionError("Unterminated quoted field.", line_number)
            pos += 1
            while pos < len(line) and line[pos].isspace():
                pos += 1
        else:
            start = pos
            while pos < len(line) and line[pos] not in ",%":
                pos += 1
            value = line[start:pos].strip()
            if not value:
                raise ConversionError("Empty ARFF field; use ? for missing values.", line_number)
        values.append(None if value == "?" and not quoted else value)
        if pos == len(line) or line[pos] == "%":
            break
        if line[pos] != ",":
            raise ConversionError("Expected a comma after the quoted field.", line_number)
        pos += 1
        if not line[pos:].strip() or line[pos:].lstrip().startswith("%"):
            raise ConversionError("Trailing comma creates an empty ARFF field.", line_number)
    return values


def arff_reader(text):
    header, dates, rows, lines = [], {}, [], []
    header_lines, attribute_lines = [], []
    in_data, relation_seen, count = False, False, 0
    for line_number, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("%"):
            continue
        if not in_data:
            header_lines.append(line_number)
            if re.match(r"^@data\s*(?:%.*)?$", line, re.IGNORECASE):
                if not relation_seen or not count:
                    raise ConversionError(
                        "Declare a relation and attributes before @data.", line_number
                    )
                in_data = True
                header.append("@data")
            elif re.match(r"^@relation\s+", line, re.IGNORECASE):
                if relation_seen or count:
                    raise ConversionError(
                        "Declare exactly one relation before the attributes.",
                        line_number,
                    )
                relation_seen = True
                header.append(line)
            elif re.match(r"^@attribute\s+", line, re.IGNORECASE):
                attribute_lines.append(line_number)
                date_match = re.match(
                    r"""^(@attribute\s+(?:'[^'\\]*(?:\\.[^'\\]*)*'|"[^"\\]*(?:\\.[^"\\]*)*"|\S+)\s+)date(?:\s+(['"])(.*?)\2)?\s*$""",
                    line,
                    re.IGNORECASE,
                )
                if date_match:
                    dates[count] = date_match[3] or "yyyy-MM-dd'T'HH:mm:ss"
                    line = date_match[1] + "STRING"
                count += 1
                header.append(line)
            else:
                raise ConversionError("Expected @relation, @attribute, or @data.", line_number)
        else:
            if line.startswith("{"):
                raise ConversionError("Sparse ARFF is outside this version’s scope.", line_number)
            rows.append(tokens(line, line_number))
            lines.append(line_number)
    if not in_data:
        raise ConversionError("ARFF file has no @data section.", max(1, len(text.splitlines())))
    try:
        parsed = arff.loads("\n".join(header) + "\n")
    except (ValueError, arff.ArffException) as error:
        library_line = getattr(error, "line", 1) or 1
        source_line = header_lines[min(max(library_line - 1, 0), len(header_lines) - 1)]
        raise ConversionError("Invalid ARFF header: " + str(error), source_line) from error
    attributes = []
    names = set()
    for i, (name, kind) in enumerate(parsed["attributes"]):
        if name in names or not name.strip():
            raise ConversionError(
                "Attribute names must be nonempty and unique.", attribute_lines[i]
            )
        names.add(name)
        if i in dates:
            if dates[i] not in DATE_FORMATS:
                raise ConversionError(
                    "Unsupported date pattern. Use a supported date format.",
                    attribute_lines[i],
                    name,
                )
            attr = Attribute(name, "date", date_format=dates[i])
        elif isinstance(kind, list):
            attr = Attribute(name, "nominal", kind)
        else:
            attr = Attribute(
                name,
                "numeric" if kind.upper() in {"NUMERIC", "REAL", "INTEGER"} else kind.lower(),
            )
        attributes.append(attr)
    dataset = Dataset(parsed["relation"], attributes, rows, lines)
    validate(dataset)
    return dataset
