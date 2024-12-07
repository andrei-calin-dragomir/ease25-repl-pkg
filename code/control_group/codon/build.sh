#!/bin/bash

SOURCE_DIR="./source"
OUTPUT_DIR="./build"

# Create the output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

for py_file in "$SOURCE_DIR"/*.py; do
    # Check if there are any .py files
    echo $py_file
    if [ ! -e "$py_file" ]; then
        echo "No Python files found in $SOURCE_DIR"
        exit 1
    fi

    # Get the base name of the file (without path)
    base_name=$(basename "$py_file" .py)

    # Build the Python file using codon
    echo "Building $py_file..."
    codon build -release -exe $py_file -o "${OUTPUT_DIR}/${base_name}"

    # Check if the build was successful
    if [ $? -eq 0 ]; then
        echo "Successfully built $base_name"
    else
        echo "Failed to build $base_name"
    fi
done

echo "Build process completed."

