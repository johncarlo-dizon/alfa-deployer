#!/bin/bash
# combine_files.sh
# Combines all files in the current directory into one text file,
# each preceded by its filename.
#
# Usage:
#   ./combine_files.sh                 -> outputs to combined_output.txt
#   ./combine_files.sh output.txt      -> outputs to output.txt

OUTPUT_FILE="${1:-combined_output.txt}"

# Remove old output file if it exists (so it doesn't include itself)
rm -f "$OUTPUT_FILE"

# Loop over all files (not directories) in the current directory
for file in *; do
    # Skip if it's not a regular file
    [ -f "$file" ] || continue

    # Skip the script itself and the output file
    [ "$file" == "$(basename "$0")" ] && continue
    [ "$file" == "$OUTPUT_FILE" ] && continue

    {
        echo "$file"
        cat "$file"
        echo ""   # blank line for spacing between files
    } >> "$OUTPUT_FILE"
done

echo "Done! Combined files into $OUTPUT_FILE"