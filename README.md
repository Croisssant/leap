# Bit Encoding Approximate Pattern Matching in BFV

A homomorphic encryption-based pattern matching system using Microsoft SEAL's BFV scheme. This implementation supports **exact matching**, **wildcard matching**, and **approximate matching** with configurable thresholds, all performed on encrypted data.

## Overview

This project implements a privacy-preserving pattern matching algorithm that:
- Encrypts text data using the BFV (Brakerski-Fan-Vercauteren) homomorphic encryption scheme
- Performs pattern matching operations entirely on encrypted data
- Supports three matching modes:
  - **Exact matching**: Finds patterns that match exactly
  - **Wildcard matching**: Supports `*` as a wildcard character that matches any character
  - **Approximate matching**: Finds patterns within a specified Hamming distance threshold
- Returns encrypted results that can only be decrypted by the key holder

### Algorithm Features

- **Bit-level encoding**: Characters are encoded as 8-bit representations for fine-grained matching
- **Sliding window approach**: Creates rotation windows to check all possible pattern positions
- **Batch processing**: Efficiently processes multiple patterns simultaneously
- **Optimized polynomial evaluation**: Uses Paterson-Stockmeyer algorithm for threshold computation
- **Noise budget management**: Dynamically adjusts encryption parameters based on input size and matching mode

---

## Prerequisites

Before building this project, ensure you have:

- **CMake** (version 3.13 or higher)
- **C++ Compiler** with C++17 support (GCC 8+, Clang 7+, or MSVC 2019+)
- **Git** for cloning repositories
- **Build tools**: `make` or `ninja`

---

## Installing Microsoft SEAL

### 1. Clone the SEAL Repository

```bash
git clone https://github.com/microsoft/SEAL.git
cd SEAL
```

### 2. Configure and Build SEAL

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DSEAL_BUILD_EXAMPLES=ON -DSEAL_USE_INTEL_HEXL=ON
cmake --build build -j$(nproc)
```

**Note**: The `-j$(nproc)` flag uses all available CPU cores for faster compilation. On Windows, use `-j%NUMBER_OF_PROCESSORS%` instead.

### 3. Install SEAL to a Custom Location

```bash
cmake --install build --prefix /path/to/seal_install
```

Replace `/path/to/seal_install` with your desired installation directory. For example:

- Linux/Mac: `/usr/local/seal` or `$HOME/seal_install`
- Windows: `C:\seal_install`

---

## Building This Project

### 1. Navigate to Project Directory

```bash
cd /path/to/bit_encoding_approx_pattern_matching
```

### 2. Configure with CMake

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH=/path/to/seal_install
```

**Important**: Replace `/path/to/seal_install` with the actual path where you installed SEAL in the previous step.

### 3. Build the Project

```bash
cmake --build build -j$(nproc)
```

### 4. The Executable

After successful compilation, the executable will be located at:

- Linux/Mac: `build/pattern_matching`
- Windows: `build\Release\pattern_matching.exe` or `build\Debug\pattern_matching.exe`

---

## Usage

### Command Syntax

```bash
./build/pattern_matching --text <text_file> --pattern <patterns_file> [--threshold <t>] [--quiet]
```

### Arguments

- `--text <file>`: Path to file containing the text to search in
- `--pattern <file>`: Path to file containing patterns (one per line)
- `--threshold <t>`: Optional. Matching threshold for approximate matching (default: pattern length for exact matching)
- `--quiet`: Optional. Suppress verbose debug output and packing details

**Note**: The flags can be provided in any order.

### Input File Requirements

#### Text File Format

- Single line or multi-line text
- Example (`text.txt`):
  ```
  Lorem ipsum dolor sit amet, consectetur adipiscing elit vivamus.
  ```

#### Patterns File Format

- One pattern per line
- **All patterns must have the same length**
- Empty lines are ignored
- Supports wildcard character `*` (matches any character)
- Example (`patterns.txt`):
  ```
  vivamus.
  pattern2
  abcdefgh
  ```

### Matching Modes

The program automatically detects the matching mode based on the pattern and threshold:

1. **Exact Matching** (default when threshold = pattern length):
   ```bash
   ./build/pattern_matching --text inputs/text.txt --pattern exact_patterns.txt
   ```
   Pattern: `vivamus.` matches only exact occurrences

2. **Wildcard Matching** (when pattern contains `*`):
   ```bash
   ./build/pattern_matching --text inputs/text.txt --pattern wildcard_patterns.txt
   ```
   Pattern: `vi*amus.` matches `vivamus.`, `viXamus.`, etc.

3. **Approximate Matching** (when threshold < pattern length):
   ```bash
   ./build/pattern_matching --text inputs/text.txt --pattern approx_patterns.txt --threshold 7
   ```
   Pattern: `vivaaus.` with threshold 7 matches `vivamus.` (1 character difference)

### Example Usage

```bash
# Exact matching with verbose output
./build/pattern_matching --text inputs/text.txt --pattern inputs/pattern.txt

# Approximate matching with threshold (quiet mode)
./build/pattern_matching --text inputs/text.txt --pattern inputs/pattern.txt --threshold 7 --quiet

# Using custom files
./build/pattern_matching --text data/document.txt --pattern data/keywords.txt

# Flags can be in any order
./build/pattern_matching --pattern patterns.txt --text text.txt --quiet
```

---

## Testing

### Test Scripts

Two shell scripts are provided for testing:

1. **test_matching_cases.sh**: Tests all three matching modes with example data
   ```bash
   ./test_matching_cases.sh
   ```

2. **sweep_parameters.sh**: Runs parameter sweeps for performance analysis
   ```bash
   # Default sweep
   ./sweep_parameters.sh
   
   # Custom parameters
   N_VALUES="64" M_VALUES="8" K_VALUES="1" CASE_VALUES="exact" ./sweep_parameters.sh
   ```


## License

This project uses Microsoft SEAL, which is licensed under the MIT License.
