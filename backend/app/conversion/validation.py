import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

from .types import ConversionError

DATE_FORMATS = {
    "yyyy-MM-dd": "%Y-%m-%d",
    "yyyy-MM-dd'T'HH:mm:ss": "%Y-%m-%dT%H:%M:%S",
    "yyyy-MM-dd HH:mm:ss": "%Y-%m-%d %H:%M:%S",
    "yyyy-MM-dd'T'HH:mm:ss.SSS": "%Y-%m-%dT%H:%M:%S.%f",
    "yyyy-MM-dd'T'HH:mm:ssXXX": "%Y-%m-%dT%H:%M:%S%z",
    "MM/dd/yyyy": "%m/%d/%Y",
    "dd/MM/yyyy": "%d/%m/%Y",
}


def is_numeric(value):
    if not re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", value):
        return False
    try:
        return Decimal(value).is_finite()
    except InvalidOperation:
        return False


def is_date(value, date_format):
    try:
        datetime.strptime(value, DATE_FORMATS[date_format])
        return True
    except (ValueError, KeyError):
        return False


def validate(dataset):
    names = [a.name for a in dataset.attributes]
    if not names or any(not n.strip() for n in names):
        raise ConversionError("Attribute names cannot be empty.")
    if len(set(names)) != len(names):
        raise ConversionError("Duplicate attribute names are not allowed.")
    for attr in dataset.attributes:
        if attr.type not in {"numeric", "nominal", "date", "string"}:
            raise ConversionError("Unsupported attribute type.", attribute=attr.name)
        if attr.type == "date" and attr.date_format not in DATE_FORMATS:
            raise ConversionError(
                "Unsupported date pattern. Select a supported date format or use string.",
                attribute=attr.name,
            )
        if attr.type == "nominal" and (
            not attr.values or len(set(attr.values)) != len(attr.values)
        ):
            raise ConversionError(
                "Nominal attributes need a nonempty, unique value set.",
                attribute=attr.name,
            )
    for row, line in zip(dataset.rows, dataset.lines):
        if len(row) != len(names):
            raise ConversionError(f"Expected {len(names)} fields, found {len(row)}.", line)
        for attr, value in zip(dataset.attributes, row):
            if value is None:
                continue
            valid = (
                attr.type == "string"
                or attr.type == "numeric"
                and is_numeric(value)
                or attr.type == "nominal"
                and value in attr.values
                or attr.type == "date"
                and is_date(value, attr.date_format)
            )
            if not valid:
                raise ConversionError(
                    f"Value does not match the {attr.type} attribute.", line, attr.name
                )
