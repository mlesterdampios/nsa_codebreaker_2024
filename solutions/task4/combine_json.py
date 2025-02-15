import json
import glob
import sys
import os

def combine_json_files(input_dir, output_file):
    # Ensure input directory exists
    if not os.path.isdir(input_dir):
        print(f"Error: The directory '{input_dir}' does not exist.")
        return

    # Find all JSON files in the input directory
    json_files = glob.glob(os.path.join(input_dir, '*.json'))

    if not json_files:
        print(f"No JSON files found in directory '{input_dir}'.")
        return

    combined_json = []

    # Read and combine all JSON files
    for file in json_files:
        with open(file, 'r') as f:
            data = json.load(f)
            combined_json.append(data)

    # Save the combined JSON array to the specified output file
    with open(output_file, 'w') as output_file:
        json.dump(combined_json, output_file, indent=4)

    print(f"Combined JSON file created successfully as '{output_file}'.")

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python combine_json.py <input_directory> <output_file>")
        sys.exit(1)
    
    input_directory = sys.argv[1]
    output_filename = sys.argv[2]
    
    combine_json_files(input_directory, output_filename)
