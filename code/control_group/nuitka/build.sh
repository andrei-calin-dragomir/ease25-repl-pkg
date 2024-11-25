#!/bin/bash

# Check if Nuitka is installed
if ! command -v nuitka &> /dev/null
then
    echo "Nuitka could not be found. Please install it using 'pip install nuitka'."
    exit 1
fi

# Directory containing Python files
SOURCE_DIR="../python" 
OUTPUT_DIR="./build"

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

# Compile each .py file in the source directory
for py_file in "$SOURCE_DIR"/*.py; do
    if [ -f "$py_file" ]; then
        # Get the base name of the file without the extension
        base_name=$(basename "$py_file" .py)

        echo "Compiling $py_file to standalone executable..."

        # Compile the Python file to a standalone executable
        nuitka --standalone --onefile --output-dir="$OUTPUT_DIR" "$py_file"

        if [ $? -eq 0 ]; then
            echo "Successfully compiled $base_name to $OUTPUT_DIR/$base_name.bin"
        else
            echo "Failed to compile $base_name."
        fi
    fi
done

echo "Compilation process completed."
