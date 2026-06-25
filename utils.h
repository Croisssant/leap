#ifndef UTILS_H
#define UTILS_H

#include <iostream>
#include <fstream>
#include <sstream>
#include <vector>
#include <string>
#include <stdexcept>

/**
 * @brief Reads the entire content of a text file
 * @param filepath Path to the text file
 * @return String containing the full text content
 * @throws std::runtime_error if file cannot be opened
 */
std::string read_text_from_file(const std::string& filepath) {
    std::ifstream file(filepath);
    
    if (!file.is_open()) {
        throw std::runtime_error("Failed to open text file: " + filepath);
    }
    
    std::stringstream buffer;
    buffer << file.rdbuf();
    file.close();
    
    std::string content = buffer.str();
    
    if (content.empty()) {
        throw std::runtime_error("Text file is empty: " + filepath);
    }
    
    return content;
}

/**
 * @brief Reads patterns from a file (one pattern per line)
 * @param filepath Path to the patterns file
 * @return Vector of pattern strings
 * @throws std::runtime_error if file cannot be opened or patterns have different lengths
 */
std::vector<std::string> read_patterns_from_file(const std::string& filepath) {
    std::ifstream file(filepath);
    
    if (!file.is_open()) {
        throw std::runtime_error("Failed to open patterns file: " + filepath);
    }
    
    std::vector<std::string> patterns;
    std::string line;
    
    while (std::getline(file, line)) {
        // Trim whitespace and skip empty lines
        line.erase(0, line.find_first_not_of(" \t\r\n"));
        line.erase(line.find_last_not_of(" \t\r\n") + 1);
        
        if (!line.empty()) {
            patterns.push_back(line);
        }
    }
    
    file.close();
    
    if (patterns.empty()) {
        throw std::runtime_error("No patterns found in file: " + filepath);
    }
    
    // Check that all patterns have the same length
    size_t pattern_length = patterns[0].length();
    
    for (size_t i = 1; i < patterns.size(); ++i) {
        if (patterns[i].length() != pattern_length) {
            std::stringstream error_msg;
            error_msg << "Pattern length mismatch in file: " << filepath << "\n"
                      << "  Pattern 1 (\"" << patterns[0] << "\"): " << pattern_length << " characters\n"
                      << "  Pattern " << (i + 1) << " (\"" << patterns[i] << "\"): " 
                      << patterns[i].length() << " characters\n"
                      << "All patterns must have the same length!";
            throw std::runtime_error(error_msg.str());
        }
    }
    
    return patterns;
}

/**
 * @brief Structure to hold parsed command line arguments
 */
struct ProgramArgs {
    std::string text_file;
    std::string patterns_file;
};

/**
 * @brief Prints usage information for the program
 * @param program_name Name of the executable
 */
void print_usage(const char* program_name) {
    std::cout << "Usage: " << program_name << " --text <text_file> --pattern <patterns_file>\n\n"
              << "Arguments:\n"
              << "  --text <file>      Path to file containing the text to search in\n"
              << "  --pattern <file>   Path to file containing patterns (one per line)\n\n"
              << "Example:\n"
              << "  " << program_name << " --text text.txt --pattern patterns.txt\n"
              << std::endl;
}

/**
 * @brief Parses command line arguments
 * @param argc Number of arguments
 * @param argv Array of argument strings
 * @return ProgramArgs structure with parsed file paths
 * @throws std::runtime_error if arguments are invalid
 */
ProgramArgs parse_arguments(int argc, char* argv[]) {
    ProgramArgs args;
    
    if (argc != 5) {
        throw std::runtime_error("Invalid number of arguments");
    }
    
    // Parse flags and their values
    for (int i = 1; i < argc; i += 2) {
        std::string flag = argv[i];
        
        if (i + 1 >= argc) {
            throw std::runtime_error("Missing value for flag: " + flag);
        }
        
        std::string value = argv[i + 1];
        
        if (flag == "--text") {
            args.text_file = value;
        } else if (flag == "--pattern") {
            args.patterns_file = value;
        } else {
            throw std::runtime_error("Unknown flag: " + flag);
        }
    }
    
    // Validate that both required flags were provided
    if (args.text_file.empty()) {
        throw std::runtime_error("Missing required flag: --text");
    }
    if (args.patterns_file.empty()) {
        throw std::runtime_error("Missing required flag: --pattern");
    }
    
    return args;
}

#endif // UTILS_H
