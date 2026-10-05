import csv
import io


def quote(value):
    escaped = (
        value.replace("\\", "\\\\")
        .replace("'", "\\'")
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )
    return "'" + escaped + "'"


def arff_writer(dataset):
    header = [f"@relation {quote(dataset.relation)}", ""]
    for attr in dataset.attributes:
        kind = attr.type.upper()
        if attr.type == "nominal":
            kind = "{" + ",".join(quote(v) for v in attr.values) + "}"
        elif attr.type == "date":
            kind = 'DATE "' + attr.date_format + '"'
        header.append(f"@attribute {quote(attr.name)} {kind}")
    header += ["", "@data"]
    rows = [
        ",".join(
            "?" if v is None else v if a.type == "numeric" else quote(v)
            for a, v in zip(dataset.attributes, row)
        )
        for row in dataset.rows
    ]
    return "\n".join(header + rows) + "\n", "\n".join(header + rows[:20]) + "\n"


def csv_writer(dataset, delimiter=",", quotechar='"'):
    output = io.StringIO(newline="")
    writer = csv.writer(output, delimiter=delimiter, quotechar=quotechar, lineterminator="\r\n")
    writer.writerow([a.name for a in dataset.attributes])
    preview = output.getvalue()
    for i, row in enumerate(dataset.rows):
        writer.writerow(["" if v is None else v for v in row])
        if i < 20:
            preview = output.getvalue()
    return output.getvalue(), preview
