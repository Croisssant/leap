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
        base_mask.insert(base_mask.end(), mask_segment.begin(), mask_segment.end());
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
std::vector<uint64_t> create_mask(size_t num_ones, size_t mask_segment_size, size_t num_segments, size_t poly_modulus_degree, bool verbose) {

    std::vector<uint64_t> mask(poly_modulus_degree, 0);
    std::vector<uint64_t> base_mask = create_base_mask(num_ones, mask_segment_size, num_segments);

    size_t num_copies = 0;
    size_t total_filled_elements = 0;
    size_t zeroes_left_at_end = poly_modulus_degree;
    size_t base_mask_size = base_mask.size();

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

    if (verbose) {
        std::cout << "\n=== Mask Creation Statistics ===\n";
        std::cout << "Mask segment structure:\n";
        std::cout << "  - Ones (HL):           " << num_ones << " bits\n";
        std::cout << "  - Zeros:               " << (mask_segment_size - num_ones) << " bits\n";
        std::cout << "  - Segment size:        " << mask_segment_size << " bits\n";
        std::cout << "  - Number of segments:  " << num_segments << "\n";
        std::cout << "Base mask size:          " << base_mask_size << " bits\n";
        std::cout << "Full copies generated:   " << num_copies << "\n";
        std::cout << "Total bits filled:       " << total_filled_elements << " / " << poly_modulus_degree << "\n";
        std::cout << "Trailing zeroes:         " << zeroes_left_at_end << " bits\n";
    }
    
    return mask;
}

/**
 * @brief Performs homomorphic XNOR operation: ct × pt + (1-ct) × (1-pt)
 * This checks bit equality in encrypted domain
 * @param context SEAL context
 * @param batch_encoder Batch encoder for encoding plaintext
 * @param evaluator Evaluator for homomorphic operations
 * @param ciphertext Input ciphertext (ct)
 * @param pattern_vector Pattern vector (pt)
 * @return Ciphertext containing equality results (1 where bits match, 0 otherwise)
 */
seal::Ciphertext xnor(seal::SEALContext& context,
                                   seal::BatchEncoder& batch_encoder,
                                   seal::Evaluator& evaluator,
                                   const seal::Ciphertext& ciphertext,
                                   const std::vector<uint64_t>& pattern_vector) {
    // Encode pattern vector as plaintext
    seal::Plaintext pt_plain;
    batch_encoder.encode(pattern_vector, pt_plain);
    
    // Create plaintext for 1 (all ones)
    std::vector<uint64_t> ones(pattern_vector.size(), 1);
    seal::Plaintext ones_plain;
    batch_encoder.encode(ones, ones_plain);
    
    // Compute (1 - ct)
    seal::Ciphertext ones_minus_ct;
    evaluator.negate(ciphertext, ones_minus_ct);
    evaluator.add_plain_inplace(ones_minus_ct, ones_plain);
    
    // Compute (1 - pt)
    seal::Plaintext ones_minus_pt;
    std::vector<uint64_t> one_minus_pt(pattern_vector.size());
    for (size_t i = 0; i < pattern_vector.size(); ++i) {
        one_minus_pt[i] = 1 - pattern_vector[i];
    }
    batch_encoder.encode(one_minus_pt, ones_minus_pt);
    
    // Compute (1-ct) × (1-pt)
    seal::Ciphertext ones_minus_ct_times_ones_minus_pt;
    evaluator.multiply_plain(ones_minus_ct, ones_minus_pt, ones_minus_ct_times_ones_minus_pt);

    // Compute ct × pt
    seal::Ciphertext ct_times_pt;
    evaluator.multiply_plain(ciphertext, pt_plain, ct_times_pt);
    
    // Result = ct × pt + (1-ct) × (1-pt)
    seal::Ciphertext result;
    evaluator.add(ct_times_pt, ones_minus_ct_times_ones_minus_pt, result);
    
    return result;
}


seal::Ciphertext one_minus_ct(seal::SEALContext& context,
                              seal::BatchEncoder& batch_encoder,
                              seal::Evaluator& evaluator,
                              const seal::Ciphertext& ciphertext,
                              const size_t poly_modulus_degree) {


    // Create plaintext for 1 (all ones)
    std::vector<uint64_t> ones(poly_modulus_degree, 1);
    seal::Plaintext ones_plain;
    batch_encoder.encode(ones, ones_plain);

    // Compute (1 - ct)
    seal::Ciphertext result_ct;
    evaluator.negate(ciphertext, result_ct);
    evaluator.add_plain_inplace(result_ct, ones_plain);

    return result_ct;
}

#endif // EQUALITY_H
