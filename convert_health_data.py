#!/usr/bin/env python3

# Convert Apple Health export.xml and export_cda.xml files into a consolidated CSV file.

import csv
import os
import glob
import xml.etree.ElementTree as ET
from datetime import datetime

TARGET_TYPES = {
    # Activity
    'HKQuantityTypeIdentifierStepCount',
    'HKQuantityTypeIdentifierActiveEnergyBurned',
    # Heart
    'HKQuantityTypeIdentifierHeartRate',
    'HKQuantityTypeIdentifierRestingHeartRate',
    'HKQuantityTypeIdentifierHeartRateVariabilitySDNN',
    # Sleep
    'HKCategoryTypeIdentifierSleepAnalysis',
    # Body Metrics
    'HKQuantityTypeIdentifierBodyMass',
    'HKQuantityTypeIdentifierBodyFatPercentage',
    # Performance & Recovery
    'HKQuantityTypeIdentifierVO2Max',
    'HKQuantityTypeIdentifierRespiratoryRate',
    # Sedentary Monitor
    'HKCategoryTypeIdentifierAppleStandHour',
}

def parse_export_xml(filepath, records, seen_keys):
    """Parse export.xml using iterparse for memory efficiency."""
    print(f"Processing: {filepath}")
    count = 0
    local_count = 0
    workout_count = 0
    
    context = ET.iterparse(filepath, events=('end',))
    
    for event, elem in context:
        if elem.tag == 'Record':
            record_type = elem.get('type')
            if record_type in TARGET_TYPES:
                creation_date = elem.get('creationDate', '')
                start_date = elem.get('startDate', '')
                end_date = elem.get('endDate', '')
                value = elem.get('value', '')
                
                key = (creation_date, start_date, end_date, record_type, value)
                if key not in seen_keys:
                    seen_keys.add(key)
                    records.append({
                        'creationDate': creation_date,
                        'startDate': start_date,
                        'endDate': end_date,
                        'type': record_type,
                        'value': value
                    })
                    local_count += 1
                    count += 1
                    
                    if count % 50000 == 0:
                        print(f"  Progress: {count:,} records extracted...")
            
            elem.clear()
        
        elif elem.tag == 'Workout':
            workout_type = elem.get('workoutActivityType', '')
            creation_date = elem.get('creationDate', '')
            start_date = elem.get('startDate', '')
            end_date = elem.get('endDate', '')
            duration = elem.get('duration', '')
            duration_unit = elem.get('durationUnit', 'min')
            total_energy = elem.get('totalEnergyBurned', '')
            energy_unit = elem.get('totalEnergyBurnedUnit', 'Cal')
            
            value_parts = []
            if duration:
                value_parts.append(f"duration:{duration} {duration_unit}")
            if total_energy:
                value_parts.append(f"calories:{total_energy} {energy_unit}")
            value = '; '.join(value_parts) if value_parts else ''
            
            key = (creation_date, start_date, end_date, workout_type, value)
            if key not in seen_keys:
                seen_keys.add(key)
                records.append({
                    'creationDate': creation_date,
                    'startDate': start_date,
                    'endDate': end_date,
                    'type': workout_type,
                    'value': value
                })
                workout_count += 1
                count += 1
                
                if count % 50000 == 0:
                    print(f"  Progress: {count:,} records extracted...")
            
            elem.clear()
    
    print(f"  Extracted {local_count:,} records + {workout_count:,} workouts from {os.path.basename(filepath)}")
    return count

def parse_export_cda_xml(filepath, records, seen_keys):
    """Parse export_cda.xml (HL7 CDA format) using iterparse."""
    print(f"Processing: {filepath}")
    count = 0
    local_count = 0
    total_count = len(records)
    
    ns = {'cda': 'urn:hl7-org:v3'}
    
    try:
        context = ET.iterparse(filepath, events=('end',))
        
        for event, elem in context:
            if elem.tag == '{urn:hl7-org:v3}observation':
                text_elem = elem.find('cda:text', ns)
                if text_elem is not None:
                    type_elem = text_elem.find('cda:type', ns)
                    if type_elem is not None and type_elem.text in TARGET_TYPES:
                        record_type = type_elem.text
                        
                        value_elem = text_elem.find('cda:value', ns)
                        value = value_elem.text if value_elem is not None else ''
                        
                        effective_time = elem.find('cda:effectiveTime', ns)
                        start_date = ''
                        end_date = ''
                        creation_date = ''
                        
                        if effective_time is not None:
                            low = effective_time.find('cda:low', ns)
                            high = effective_time.find('cda:high', ns)
                            if low is not None:
                                start_date = format_cda_date(low.get('value', ''))
                            if high is not None:
                                end_date = format_cda_date(high.get('value', ''))
                        
                        creation_date = start_date
                        
                        key = (creation_date, start_date, end_date, record_type, value)
                        if key not in seen_keys:
                            seen_keys.add(key)
                            records.append({
                                'creationDate': creation_date,
                                'startDate': start_date,
                                'endDate': end_date,
                                'type': record_type,
                                'value': value
                            })
                            local_count += 1
                            count += 1
                            
                            if (total_count + count) % 50000 == 0:
                                print(f"  Progress: {total_count + count:,} records extracted...")
                
                elem.clear()
    except ET.ParseError as e:
        print(f"  Warning: CDA file has malformed XML, skipping. Error: {e}")
        print(f"  (export.xml likely contains the same data)")
    
    print(f"  Extracted {local_count:,} new records from {os.path.basename(filepath)}")
    return count

def format_cda_date(date_str):
    """Convert CDA date format (YYYYMMDDHHMMSS+ZZZZ) to readable format."""
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

def parse_ecg_files(ecg_dir, records, seen_keys):
    """Parse ECG CSV files and extract metadata."""
    print(f"Processing ECG files from: {ecg_dir}")
    count = 0
    total_count = len(records)
    
    ecg_files = glob.glob(os.path.join(ecg_dir, 'ecg_*.csv'))
    
    for filepath in ecg_files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = []
                for i, line in enumerate(f):
                    lines.append(line.strip())
                    if i >= 10:
                        break
                
                metadata = {}
                for line in lines:
                    if ',' in line:
                        parts = line.split(',', 1)
                        if len(parts) == 2:
                            key, value = parts[0].strip(), parts[1].strip().strip('"')
                            metadata[key] = value
                
                recorded_date = metadata.get('Recorded Date', '')
                classification = metadata.get('Classification', '')
                
                if recorded_date:
                    record_key = (recorded_date, recorded_date, recorded_date, 'ECG', classification)
                    if record_key not in seen_keys:
                        seen_keys.add(record_key)
                        records.append({
                            'creationDate': recorded_date,
                            'startDate': recorded_date,
                            'endDate': recorded_date,
                            'type': 'ECG',
                            'value': classification
                        })
                        count += 1
                        
                        if (total_count + count) % 50000 == 0:
                            print(f"  Progress: {total_count + count:,} records extracted...")
        except Exception as e:
            print(f"  Warning: Could not parse {filepath}: {e}")
    
    print(f"  Extracted {count} ECG records")
    return count

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    export_xml = os.path.join(base_dir, 'export.xml')
    export_cda_xml = os.path.join(base_dir, 'export_cda.xml')
    ecg_dir = os.path.join(base_dir, 'electrocardiograms')
    output_csv = os.path.join(base_dir, 'full_health_data.csv')
    
    records = []
    seen_keys = set()
    total_count = 0
    
    print("=" * 60)
    print("Apple Health Data Converter")
    print("=" * 60)
    print(f"Target types: {', '.join(sorted(TARGET_TYPES))}")
    print()
    
    if os.path.exists(export_xml):
        total_count += parse_export_xml(export_xml, records, seen_keys)
    else:
        print(f"Warning: {export_xml} not found")
    
    if os.path.exists(export_cda_xml):
        total_count += parse_export_cda_xml(export_cda_xml, records, seen_keys)
    else:
        print(f"Warning: {export_cda_xml} not found")
    
    if os.path.exists(ecg_dir):
        total_count += parse_ecg_files(ecg_dir, records, seen_keys)
    else:
        print(f"Warning: {ecg_dir} not found")
    
    print()
    print(f"Sorting {len(records):,} records by startDate...")
    records.sort(key=lambda x: x['startDate'])
    
    print(f"Writing to {output_csv}...")
    with open(output_csv, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['creationDate', 'startDate', 'endDate', 'type', 'value']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)
    
    print()
    print("=" * 60)
    print("COMPLETE")
    print("=" * 60)
    print(f"Total records written: {len(records):,}")
    print(f"Output file: {output_csv}")
    
    type_counts = {}
    for r in records:
        t = r['type']
        type_counts[t] = type_counts.get(t, 0) + 1
    
    print("\nRecords by type:")
    for t in sorted(type_counts.keys()):
        print(f"  {t}: {type_counts[t]:,}")

if __name__ == '__main__':
    main()

