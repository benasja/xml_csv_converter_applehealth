#!/usr/bin/env python3

"""Convert Apple Health export into flat and coaching-ready CSV outputs."""

import csv
import glob
import os
import xml.etree.ElementTree as ET
from datetime import datetime

from health_coaching import (
    COACHING_RECORD_TYPES,
    ExportData,
    iter_export_xml,
    records_to_legacy_rows,
    write_coaching_outputs,
)


def format_cda_date(date_str: str) -> str:
    if not date_str:
        return ''
    try:
        if len(date_str) >= 14:
            base = date_str[:14]
            tz = date_str[14:] if len(date_str) > 14 else ''
            dt = datetime.strptime(base, '%Y%m%d%H%M%S')
            formatted = dt.strftime('%Y-%m-%d %H:%M:%S')
            if tz:
                formatted += f' {tz}'
            return formatted
    except ValueError:
        pass
    return date_str


def parse_export_cda_into_data(filepath: str, data: ExportData) -> int:
    """Parse export_cda.xml (HL7 CDA) and merge matching records into data."""
    print(f"Processing: {filepath}")
    count = 0
    ns = {'cda': 'urn:hl7-org:v3'}

    try:
        context = ET.iterparse(filepath, events=('end',))
        for _event, elem in context:
            if elem.tag != '{urn:hl7-org:v3}observation':
                continue
            text_elem = elem.find('cda:text', ns)
            if text_elem is None:
                elem.clear()
                continue
            type_elem = text_elem.find('cda:type', ns)
            if type_elem is None or type_elem.text not in COACHING_RECORD_TYPES:
                elem.clear()
                continue

            record_type = type_elem.text
            data.type_counts[record_type] += 1

            value_elem = text_elem.find('cda:value', ns)
            value_raw = value_elem.text if value_elem is not None else ''

            effective_time = elem.find('cda:effectiveTime', ns)
            start_date = ''
            end_date = ''
            if effective_time is not None:
                low = effective_time.find('cda:low', ns)
                high = effective_time.find('cda:high', ns)
                if low is not None:
                    start_date = format_cda_date(low.get('value', ''))
                if high is not None:
                    end_date = format_cda_date(high.get('value', ''))

            creation_date = start_date
            key = (creation_date, start_date, end_date, record_type, value_raw, 'cda')
            if key in data.seen_record_keys:
                elem.clear()
                continue
            data.seen_record_keys.add(key)

            from health_coaching import HealthRecord, parse_float, parse_health_datetime

            start_dt = parse_health_datetime(start_date)
            end_dt = parse_health_datetime(end_date)
            if start_dt and end_dt:
                numeric = parse_float(value_raw)
                data.records.append(
                    HealthRecord(
                        type=record_type,
                        value=numeric,
                        category_value=value_raw if numeric is None else '',
                        unit='',
                        source_name='cda',
                        start=start_dt,
                        end=end_dt,
                        creation=creation_date,
                        start_raw=start_date,
                        end_raw=end_date,
                    )
                )
                count += 1
            elem.clear()
    except ET.ParseError as e:
        print(f"  Warning: CDA file has malformed XML, skipping. Error: {e}")

    print(f"  Extracted {count:,} new records from {os.path.basename(filepath)}")
    return count


def parse_ecg_legacy(ecg_dir: str, legacy_rows: list, seen_keys: set) -> int:
    print(f"Processing ECG files from: {ecg_dir}")
    count = 0
    ecg_files = glob.glob(os.path.join(ecg_dir, 'ecg_*.csv'))

    for filepath in ecg_files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = [line.strip() for i, line in enumerate(f) if i <= 10]
            metadata = {}
            for line in lines:
                if ',' in line:
                    parts = line.split(',', 1)
                    if len(parts) == 2:
                        key, value = parts[0].strip(), parts[1].strip().strip('"')
                        metadata[key] = value

            recorded_date = metadata.get('Recorded Date', '')
            classification = metadata.get('Classification', '')
            if not recorded_date:
                continue
            record_key = (recorded_date, recorded_date, recorded_date, 'ECG', classification)
            if record_key in seen_keys:
                continue
            seen_keys.add(record_key)
            legacy_rows.append(
                {
                    'creationDate': recorded_date,
                    'startDate': recorded_date,
                    'endDate': recorded_date,
                    'type': 'ECG',
                    'value': classification,
                }
            )
            count += 1
        except OSError as e:
            print(f"  Warning: Could not parse {filepath}: {e}")

    print(f"  Extracted {count} ECG records")
    return count


def main() -> None:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    export_xml = os.path.join(base_dir, 'export.xml')
    export_cda_xml = os.path.join(base_dir, 'export_cda.xml')
    ecg_dir = os.path.join(base_dir, 'electrocardiograms')
    output_csv = os.path.join(base_dir, 'full_health_data.csv')

    data = ExportData()

    print('=' * 60)
    print('Apple Health Data Converter')
    print('=' * 60)

    if os.path.exists(export_xml):
        iter_export_xml(export_xml, data)
    else:
        print(f"Warning: {export_xml} not found")

    if os.path.exists(export_cda_xml):
        parse_export_cda_into_data(export_cda_xml, data)
    else:
        print(f"Warning: {export_cda_xml} not found")

    legacy_rows = records_to_legacy_rows(data)
    ecg_seen = {(r['creationDate'], r['startDate'], r['endDate'], r['type'], r['value']) for r in legacy_rows}
    if os.path.exists(ecg_dir):
        parse_ecg_legacy(ecg_dir, legacy_rows, ecg_seen)
    else:
        print(f"Warning: {ecg_dir} not found")

    legacy_rows.sort(key=lambda x: x['startDate'])
    print(f"\nWriting legacy export: {output_csv}")
    with open(output_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['creationDate', 'startDate', 'endDate', 'type', 'value'])
        writer.writeheader()
        writer.writerows(legacy_rows)

    print('\nBuilding coaching-ready outputs...')
    coaching_paths = write_coaching_outputs(base_dir, data)

    print()
    print('=' * 60)
    print('COMPLETE')
    print('=' * 60)
    print(f"Legacy rows: {len(legacy_rows):,} -> {output_csv}")
    for name, path in coaching_paths.items():
        print(f"  {name}: {path}")
    print(f"\nSee {coaching_paths['data_quality_report']} for type coverage and missingness.")


if __name__ == '__main__':
    main()
