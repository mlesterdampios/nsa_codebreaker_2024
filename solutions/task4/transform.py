import sys
import re

# Precompile the regular expression for CSI (Control Sequence Introducer) sequences
CSI_PATTERN = re.compile(r'\x1b\[(.*?)([@-~])')

def process_line(line, history):
    # Try to decode the escaped sequences to actual control characters
    try:
        line_decoded = bytes(line, "utf-8").decode("unicode_escape")
    except UnicodeDecodeError:
        # If decoding fails, return the line as-is
        return line.strip()
    
    buffer = []
    cursor = 0
    i = 0
    interrupted = False  # Flag to indicate if Ctrl+C was pressed
    history_index = len(history)  # Start at the end of history (no history navigation)
    while i < len(line_decoded):
        c = line_decoded[i]
        # Handle control characters and escape sequences
        if c == '\x03':  # Ctrl+C (Interrupt)
            # Indicate that Ctrl+C was pressed
            interrupted = True
            i += 1
            break  # Stop processing the current line
        elif c == '\x1b':  # Escape character
            # Check if it's a CSI sequence
            if i + 1 < len(line_decoded) and line_decoded[i + 1] == '[':
                # Try to match CSI sequence
                m = CSI_PATTERN.match(line_decoded, i)
                if m:
                    full_seq = m.group(0)
                    params = m.group(1)
                    final_byte = m.group(2)
                    seq_length = len(full_seq)
                    # Now process known CSI sequences
                    if full_seq == '\x1b[H':  # Cursor to Home
                        cursor = 0
                    elif full_seq == '\x1b[2J':  # Clear Screen
                        buffer = []
                        cursor = 0
                    elif full_seq == '\x1b[3~':  # Delete key
                        if cursor < len(buffer):
                            del buffer[cursor]
                    elif full_seq == '\x1b[D':  # Left Arrow
                        if cursor > 0:
                            cursor -= 1
                    elif full_seq == '\x1b[C':  # Right Arrow
                        if cursor < len(buffer):
                            cursor += 1
                    elif full_seq == '\x1b[A':  # Up Arrow (Previous Command)
                        if history:
                            history_index = max(history_index - 1, 0)
                            buffer = list(history[history_index])
                            cursor = len(buffer)
                    elif full_seq == '\x1b[B':  # Down Arrow (Next Command)
                        if history:
                            history_index = min(history_index + 1, len(history))
                            if history_index < len(history):
                                buffer = list(history[history_index])
                                cursor = len(buffer)
                            else:
                                # If beyond the latest command, clear buffer
                                buffer = []
                                cursor = 0
                    else:
                        # For unhandled CSI sequences, leave them escaped
                        buffer.insert(cursor, full_seq)
                        cursor += len(full_seq)
                    # Advance index by length of the sequence
                    i += seq_length
                    continue
                else:
                    # Unrecognized CSI sequence, leave it escaped
                    escaped_seq = line_decoded[i].encode('unicode_escape').decode()
                    buffer.insert(cursor, escaped_seq)
                    cursor += len(escaped_seq)
                    i += 1
            else:
                # Not a CSI sequence, leave it escaped
                escaped_seq = line_decoded[i].encode('unicode_escape').decode()
                buffer.insert(cursor, escaped_seq)
                cursor += len(escaped_seq)
                i += 1
        elif c == '\x08':  # Backspace
            if cursor > 0:
                del buffer[cursor - 1]
                cursor -= 1
            i += 1
        elif c == '\x01':  # Ctrl+A (Home)
            cursor = 0
            i += 1
        elif c == '\x05':  # Ctrl+E (End)
            cursor = len(buffer)
            i += 1
        elif c == '\x0d' or c == '\x0a':  # Carriage Return (Enter) or Line Feed (Newline)
            # End of command; break if needed
            i += 1
            break  # Stop processing the current line
        else:
            # Insert character at cursor position
            buffer.insert(cursor, c)
            cursor += 1
            i += 1
    command = ''.join(buffer).strip()
    if interrupted:
        command += ' [Ctrl+C pressed]'
    return command

def parse_file_content(input_file):
    commands = []
    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        i = 0
        while i < len(lines):
            line = lines[i].rstrip('\n')
            # Pass the command history to process_line
            processed_command = process_line(line, commands)
            if processed_command:
                commands.append(processed_command)
            i += 1
    return commands

def main():
    if len(sys.argv) != 3:
        print("Usage: python transform.py <input_file> <output_file>")
        sys.exit(1)
    input_file = sys.argv[1]
    output_file = sys.argv[2]

    # Parse the content and write the commands to the output file
    parsed_commands = parse_file_content(input_file)
    with open(output_file, 'w', encoding='utf-8') as f:
        for cmd in parsed_commands:
            f.write(cmd + '\n')

if __name__ == "__main__":
    main()
