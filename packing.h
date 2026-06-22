#ifndef PACKING_H
#define PACKING_H

#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <cstdint>

/**
 * @brief Prints a vector of bits as a readable string
 * @param bits Vector of bits (0 or 1) to convert to characters
 * @param bit_length Number of bits per character (typically 8)
 */
void print_bits_as_string(const std::vector<uint64_t>& bits, size_t bit_length) {
    // A character requires a full chunk of bit_length bits
    if (bits.size() < bit_length) {
        std::cout << "[Error: Vector has fewer than "<< bit_length << " bits]\n";
        return;
    }
    
    // Process the vector in chunks of bit_length bits
    for (size_t i = 0; i < bits.size(); i += bit_length) {
        char character = 0;
        
        // Rebuild the character from MSB to LSB
        for (size_t j = 0; j < bit_length; ++j) {
            // Check if we accidentally run out of bits at the end of the vector
            if (i + j >= bits.size()) break; 
            
            // Shift existing bits left and add the new bit at the LSB position
            character = (character << 1) | (bits[i + j] & 1);
        }
        
        std::cout << character;
    }
    std::cout << "\n";
}

/**
 * @brief Converts a text string into a vector of bits
 * @param text Input string to convert
 * @param bit_length Number of bits per character (typically 8)
 * @return Vector of bits representing the text
 */
std::vector<uint64_t> convert_text_to_bits(const std::string& text, int bit_length) {
    int text_length = text.size();
    std::vector<uint64_t> text_in_bits;
    text_in_bits.reserve(bit_length * text_length);

    for (char c : text) {
        // i goes from (bit_length-1) (MSB) down to 0 (LSB)
        for (int i = bit_length - 1; i >= 0; --i) {
            uint64_t bit = (c >> i) & 1;
            text_in_bits.push_back(bit);
        }
    }

    return text_in_bits;
}

/**
 * @brief Performs rotation on bits and creates windows for pattern matching
 * @param text_in_bits Input vector of bits (will be modified)
 * @param bit_length Number of bits per character
 * @param pattern_length Number of rotation windows to create
 * @param verbose If true, prints each rotation window
 * @return Vector containing all rotation windows concatenated
 */
std::vector<uint64_t> rotate_bits(std::vector<uint64_t>& text_in_bits, 
                                   int bit_length, 
                                   int pattern_length,
                                   bool verbose = true) {
    int text_length = text_in_bits.size() / bit_length;
    std::vector<uint64_t> base_plaintext;
    base_plaintext.reserve(bit_length * text_length * pattern_length);

    if (verbose) {
        std::cout << "\n=== Rotation Start ===\n";
    }

    for (int i = 0; i < pattern_length; i++) {
        // Print the window for visual check
        if (verbose) {
            std::cout << "Window " << (i + 1) << " -> ";
            print_bits_as_string(text_in_bits, bit_length);
        }
        
        // 1. Append the current state of text_in_bits to base_plaintext
        base_plaintext.insert(base_plaintext.end(), text_in_bits.begin(), text_in_bits.end());

        // 2. Rotate the bits in-place for the next window iteration
        // std::rotate shifts elements left so that text_in_bits.begin() + bit_length becomes the new start.
        std::rotate(text_in_bits.begin(), text_in_bits.begin() + bit_length, text_in_bits.end());
    }

    return base_plaintext;
}

/**
 * @brief Packs base plaintext into a full-size vector with zero-padding
 * @param base_plaintext Input plaintext to pack
 * @param poly_modulus_degree Target size for the output vector
 * @param verbose If true, prints packing statistics
 * @return Packed vector of specified size with zero-padding
 */
std::vector<uint64_t> pack_and_pad(const std::vector<uint64_t>& base_plaintext,
                                    size_t poly_modulus_degree,
                                    bool verbose = true) {
    std::vector<uint64_t> full_plaintext(poly_modulus_degree, 0);
    size_t base_plaintext_size = base_plaintext.size(); 
    
    size_t num_copies = 0;
    size_t total_filled_elements = 0;
    size_t zeroes_left_at_end = poly_modulus_degree;

    if (base_plaintext_size > 0) {
        num_copies = poly_modulus_degree / base_plaintext_size;
        total_filled_elements = num_copies * base_plaintext_size;
        zeroes_left_at_end = poly_modulus_degree - total_filled_elements;
        
        auto destination = full_plaintext.begin();
        for (size_t i = 0; i < num_copies; ++i) {
            std::copy(base_plaintext.begin(), base_plaintext.end(), destination);
            destination += base_plaintext_size;
        }
    }

    // Print out the structural tracking metrics
    if (verbose) {
        std::cout << "\n=== Allocation Statistics ===\n";
        std::cout << "Base plaintext size:     " << base_plaintext_size << " bits\n";
        std::cout << "Full copies generated:   " << num_copies << "\n";
        std::cout << "Total bits filled:       " << total_filled_elements << " / " << poly_modulus_degree << "\n";
        std::cout << "Trailing zeroes left:    " << zeroes_left_at_end << " bits\n";
    }

    return full_plaintext;
}

#endif // PACKING_H
