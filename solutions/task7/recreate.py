import os

def create_files_from_log(log_file):
    with open(log_file, 'r') as f:
        content = f.read()

    # Split the content into entries separated by '==========='
    entries = content.strip().split('===========\n')
    for entry in entries:
        entry = entry.strip()
        if not entry:
            continue  # Skip empty entries

        lines = entry.split('\n')
        if len(lines) < 4:
            print('Error: Incomplete entry detected.')
            continue

        # Parse Specifier
        specifier_line = lines[0]
        if not specifier_line.startswith('Specifier: '):
            print('Error: Specifier not found in entry.')
            continue
        specifier = specifier_line[len('Specifier: '):].strip()

        # Parse Kind
        kind_line = lines[1]
        if not kind_line.startswith('Kind: '):
            print('Error: Kind not found in entry.')
            continue
        kind = kind_line[len('Kind: '):].strip()

        # Find content between '---' separators
        try:
            first_sep_idx = lines.index('---')
            second_sep_idx = lines.index('---', first_sep_idx + 1)
            content_lines = lines[first_sep_idx + 1:second_sep_idx]
            content_text = '\n'.join(content_lines)
        except ValueError:
            print('Error: Content separators not found in entry.')
            continue

        # Process the specifier to create the folder path
        if specifier.startswith('http://') or specifier.startswith('https://'):
            specifier = specifier.split('://', 1)[1]
        path_parts = specifier.strip('/').split('/')
        file_path = os.path.join(*path_parts)

        # Ensure the directory exists
        dir_path = os.path.dirname(file_path)
        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path)

        # Write the content to the file
        with open(file_path, 'w', encoding='utf-8') as f_out:
            f_out.write(content_text)

        print(f'Created file: {file_path}')

# Replace 'log.txt' with the path to your log file
create_files_from_log('eszip_archive.txt')
