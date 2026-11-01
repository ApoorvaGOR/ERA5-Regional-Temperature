"""Inspect GRIB edition 1 message headers without decoding data values.

This audit identifies reference timestamps and parameter/time-range codes;
it does not substitute for ecCodes interpretation of a GRIB product.
"""
import argparse
from collections import Counter
from datetime import datetime
import json
from pathlib import Path


def inspect(path):
    counts = Counter()
    months = Counter()
    first = None
    last = None
    previous = None
    intervals = Counter()
    records = 0
    with path.open('rb') as f:
        while True:
            start = f.tell()
            header = f.read(8)
            if not header:
                break
            if header[:4] != b'GRIB' or header[7] != 1:
                raise ValueError(f'Expected GRIB1 at byte {start}')
            size = int.from_bytes(header[4:7], 'big')
            n = int.from_bytes(f.read(3), 'big')
            f.seek(start + 8)
            pds = f.read(n)
            year = (pds[24] - 1) * 100 + pds[12]
            stamp = datetime(year, pds[13], pds[14], pds[15], pds[16])
            counts[(pds[3], pds[4], pds[8], pds[9], pds[15], pds[16], pds[17], pds[18], pds[19], pds[20])] += 1
            months[stamp.strftime('%Y-%m')] += 1
            first = min(first, stamp) if first else stamp
            last = max(last, stamp) if last else stamp
            if previous is not None:
                intervals[(stamp-previous).total_seconds()/3600] += 1
            previous = stamp
            f.seek(start + size - 4)
            if f.read(4) != b'7777':
                raise ValueError(f'GRIB end marker missing at {start}')
            records += 1
    return dict(edition=1, messages=records, first_reference_time=first.isoformat(),
                last_reference_time=last.isoformat(),
                header_code_fields=['table_version', 'centre', 'parameter', 'level_type',
                                    'hour', 'minute', 'time_unit', 'P1', 'P2', 'time_range_indicator'],
                header_code_counts=[dict(codes=list(k), count=v) for k,v in counts.items()],
                consecutive_reference_time_intervals_hours={str(k):v for k,v in intervals.items()},
                messages_per_month=dict(sorted(months.items())))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('source', type=Path)
    p.add_argument('output', type=Path)
    args = p.parse_args()
    result = inspect(args.source)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k:v for k,v in result.items() if k != 'messages_per_month'}, indent=2))
