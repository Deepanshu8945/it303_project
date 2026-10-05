import csv
import io
import subprocess
from pathlib import Path

from backend.app.conversion.engine import ParsingOptions, convert, parse

jar = Path(".runtime/weka-3.8.6.jar")
if not jar.exists():
    raise SystemExit(
        "Place the official weka-stable-3.8.6.jar in .runtime first; see docs/TESTING.md."
    )
buffer = io.StringIO(newline="")
csv.writer(buffer).writerows(
    [
        ["measurement", "text", "observed_on"],
        ["12345678901234567890.123456789", "comma, quote\" apostrophe' slash\\", "2026-09-01"],
        ["1e-20", "line\r\nbreak", "2026-09-02"],
        [None, "?", None],
        ["-0.0", "  accented é and %  ", "2026-09-03"],
    ]
)
options = ParsingOptions(relation="WEKA compatibility")
data = parse(buffer.getvalue(), "csv", options, 2)
generated = Path(".runtime/weka-edge-cases.arff")
generated.write_text(convert(data, "csv", options)[0], encoding="utf-8")
subprocess.run(
    ["java", "-cp", str(jar), "scripts/WekaCheck.java", str(generated), "samples/weather.arff"],
    check=True,
)
