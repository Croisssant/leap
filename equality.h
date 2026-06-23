#ifndef EQUALITY_H
#define EQUALITY_H

#include <vector>
#include <string>
#include <cstdint>
#include "seal/seal.h"

/**
 * @brief Creates a mask vector
 * @param num_ones Number of elements that should be 1s (HL -> H represents num_tracks, L represents bit_length)
 * @param mask_segment_size Size of each mask segment (nL -> n represents text_length, L represents bit_length)
 * @return Vector with first HL elements as 1, rest as 0
 */
std::vector<uint64_t> create_mask_segment(size_t num_ones, size_t mask_segment_size) {
    std::vector<uint64_t> mask_segment(mask_segment_size, 1);
    
    // Fill the remaining vector with 0s
    if (num_ones) {
        std::fill(mask_segment.begin() + num_ones, mask_segment.end(), 0);
    }
    
    return mask_segment;
}

/**
 * @brief Creates repeating mask segments
 * @param num_ones num_ones Number of elements that should be 1s (HL -> H represents num_tracks, L represents bit_length)
 * @param mask_segment_size Size of each mask segment (nL -> n represents text_length, L represents bit_length)
 * @param num_segments Number of mask segments to create (m -> m represents pattern_length)
 * @return Vector with repeating mask pattern (mask|mask|...|mask)
 */
std::vector<uint64_t> create_base_mask(size_t num_ones, size_t mask_segment_size, size_t num_segments) {
    std::vector<uint64_t> mask_segment = create_mask_segment(num_ones, mask_segment_size);
    std::vector<uint64_t> base_mask;
    base_mask.reserve(mask_segment_size * num_segments);
    
    // Repeat the mask pattern num_blocks times
    for (size_t i = 0; i < num_segments; ++i) {
        base_mask.insert(base_mask.end(), base_mask.begin(), base_mask.end());
    }
    
    return base_mask;
}

/**
 * @brief Creates mask to be applied to full ciphertext (Length is poly_modulus_degree)
 * @param num_ones num_ones Number of elements that should be 1s (HL -> H represents num_tracks, L represents bit_length)
 * @param mask_segment_size Size of each mask segment (nL -> n represents text_length, L represents bit_length)
 * @param num_segments Number of mask segments to create (m -> m represents pattern_length)
 * @param poly_modulus_degree Determines the length of the full mask and num_copies to be made
 * @return Vector with repeating mask pattern (mask|mask|...|mask)
 */
std::vector<uint64_t> create_mask(size_t num_ones, size_t mask_segment_size, size_t num_segments, size_t poly_modulus_degree) {

    std::vector<uint64_t> mask(poly_modulus_degree, 0);
    std::vector<uint64_t> base_mask = create_base_mask(num_ones, mask_segment_size, num_segments);

    size_t num_copies = 0;
    size_t total_filled_elements = 0;
    size_t zeroes_left_at_end = poly_modulus_degree;
    size_t base_mask_size = base_mask.size()

    if (base_mask_size > 0) {
        num_copies = poly_modulus_degree / base_mask_size;
        total_filled_elements = num_copies * base_mask_size;
        zeroes_left_at_end = poly_modulus_degree - total_filled_elements;
        
        auto destination = mask.begin();
        for (size_t i = 0; i < num_copies; ++i) {
            std::copy(base_mask.begin(), base_mask.end(), destination);
            destination += base_mask_size;
        }
    }
    
    return mask;
}

#endif // EQUALITY_H
