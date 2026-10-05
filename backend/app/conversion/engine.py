from dataclasses import asdict
from pathlib import Path

from pydantic import BaseModel, Field, model_validator

from .readers import arff_reader, csv_reader
from .types import Attribute, ConversionError
from .validation import DATE_FORMATS, is_date, validate
from .writers import arff_writer, csv_writer


class ParsingOptions(BaseModel):
    delimiter: str = Field(default=",", min_length=1, max_length=1)
    quote: str = Field(default='"', min_length=1, max_length=1)
    header: bool = True
    relation: str = Field(default="", max_length=200)

    @model_validator(mode="after")
    def validate_chars(self):
        if self.delimiter == self.quote or self.delimiter in "\r\n\0" or self.quote in "\r\n\0":
            raise ValueError("Delimiter and quote must be distinct, non-newline characters.")
        if any(c in self.relation for c in "\r\n\0"):
            raise ValueError("Relation must be a single line.")
        return self


def detect(filename, content):
    extension = Path(filename).suffix.lower().lstrip(".")
    if extension not in {"csv", "arff"}:
        raise ConversionError("Only .csv and .arff files are supported.")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise ConversionError("Upload a UTF-8 or ASCII text file.") from error
    if "\0" in text:
        raise ConversionError("Binary content is not supported.")
    leading = next(
        (
            line.strip().lower()
            for line in text.splitlines()
            if line.strip() and not line.lstrip().startswith("%")
        ),
        "",
    )
    return ("arff" if leading.startswith("@relation ") else extension), text


def parse(text, source, options, threshold):
    return arff_reader(text) if source == "arff" else csv_reader(text, options, threshold)


def override(dataset, attributes):
    if len(attributes) != len(dataset.attributes):
        raise ConversionError("Schema must have the original number of attributes.")
    updated = []
    for i, item in enumerate(attributes):
        attr = Attribute(**item)
        values = list(dict.fromkeys(row[i] for row in dataset.rows if row[i] is not None))
        if attr.type == "nominal" and not attr.values:
            attr.values = values
        if attr.type == "date" and not attr.date_format:
            attr.date_format = next(
                (f for f in DATE_FORMATS if values and all(is_date(v, f) for v in values)),
                "yyyy-MM-dd",
            )
        updated.append(attr)
    dataset.attributes = updated
    validate(dataset)
    return dataset


def summary(dataset):
    return {
        "relation": dataset.relation,
        "attributes": [asdict(a) for a in dataset.attributes],
        "rows": dataset.rows[:20],
        "instance_count": len(dataset.rows),
        "attribute_count": len(dataset.attributes),
        "warnings": [],
    }


def convert(dataset, source, options):
    validate(dataset)
    return arff_writer(dataset) if source == "csv" else csv_writer(dataset)
