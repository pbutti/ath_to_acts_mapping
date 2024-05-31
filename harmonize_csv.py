#!/usr/bin/env python3

import csv
import argparse

def harmonize_csv_separators(input_path, output_path):
    with open(input_path, 'r') as input_file:
        content = input_file.readlines()
        
    harmonized_content = []
    
    for line in content:
        harmonized_line = line.replace(';', ',')
        harmonized_content.append(harmonized_line)
    
    with open(output_path, 'w', newline='') as output_file:
        writer = csv.writer(output_file)
        for line in harmonized_content:
            writer.writerow(line.strip().split(','))

def main():
    parser = argparse.ArgumentParser(description="Harmonize CSV file separators from ';' to ','.")
    parser.add_argument('--input_file', help="Path to the input CSV file")
    parser.add_argument('--output_file', help="Path to the output CSV file")

    args = parser.parse_args()

    harmonize_csv_separators(args.input_file, args.output_file)

if __name__ == '__main__':
    main()
