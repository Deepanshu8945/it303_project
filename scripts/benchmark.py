import csv
import io
import json
import time
from pathlib import Path

from backend.app.conversion.engine import ParsingOptions, convert, parse

buffer = io.StringIO(newline="")
writer = csv.writer(buffer)
writer.writerow(["record", "measurement", "group", "notes"])
for index in range(100000):
    writer.writerow(
        [
            index,
            f"{index}.1234567890123456789",
            "control" if index % 2 else "sample",
            "Observation " + "x" * 70,
        ]
    )
text = buffer.getvalue()
started = time.perf_counter()
options = ParsingOptions(relation="benchmark")
dataset = parse(text, "csv", options, 20)
output, _ = convert(dataset, "csv", options)
elapsed = time.perf_counter() - started
result = {
    "instances": len(dataset.rows),
    "input_bytes": len(text.encode()),
    "output_bytes": len(output.encode()),
    "parse_and_convert_seconds": round(elapsed, 3),
}
Path("docs/benchmark.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
print(json.dumps(result))
