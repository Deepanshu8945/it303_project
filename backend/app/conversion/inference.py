import pandas as pd

from .types import Attribute
from .validation import DATE_FORMATS, is_date, is_numeric


def infer(names, rows, threshold):
    frame = pd.DataFrame(rows, columns=names, dtype=object)
    attributes = []
    for name in names:
        values = list(dict.fromkeys(v for v in frame[name].tolist() if v is not None))
        attr = Attribute(name, "string")
        if values and all(is_numeric(v) for v in values):
            attr.type = "numeric"
        else:
            date_format = next(
                (
                    f
                    for f in list(DATE_FORMATS)[:5]
                    if values and all(is_date(v, f) for v in values)
                ),
                None,
            )
            if date_format:
                attr.type, attr.date_format = "date", date_format
            elif values and len(values) <= threshold:
                attr.type, attr.values = "nominal", values
        attributes.append(attr)
    return attributes
