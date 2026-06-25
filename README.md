# Bit Encoding Approx Pattern Matching in BFV

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
cd /path/to/this/project
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
./build/pattern_matching --text <text_file> --pattern <patterns_file>
```

### Arguments

- `--text <file>`: Path to file containing the text to search in
- `--pattern <file>`: Path to file containing patterns (one per line)

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
- Example (`patterns.txt`):
  ```
  vivamus.
  pattern2
  abcdefgh
  ```

### Example Usage

```bash
# Using provided example files
./build/pattern_matching --text text.txt --pattern patterns.txt

# Using custom files
./build/pattern_matching --text ../inputs/document.txt --pattern ../inputs/keywords.txt

# Flags can be in any order
./build/pattern_matching --pattern patterns.txt --text text.txt
```

### Output

The program will output:

- Loading confirmation with file information
- Encryption parameters setup
- Intermediate computation results (if verbose mode is enabled)
- **Final Result**: `Pattern FOUND` or `Pattern NOT FOUND`
