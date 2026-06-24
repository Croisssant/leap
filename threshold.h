#include "seal/seal.h"
#include <vector>
#include <numeric>

using namespace std;
using namespace seal;

/**
 * @brief Computes the modular multiplicative inverse using Extended Euclidean Algorithm
 * @param n The number to find the inverse of
 * @param q The modulus (field size)
 * @return The modular inverse of n mod q, or 1 if not invertible
 * @note Time complexity: O(log q) - significantly faster than brute force O(q)
 */
uint64_t modular_inverse(int64_t n, uint64_t q) {
    int64_t t = 0, new_t = 1;
    int64_t r = static_cast<int64_t>(q);
    int64_t new_r = (n % static_cast<int64_t>(q) + static_cast<int64_t>(q)) % static_cast<int64_t>(q);
    
    while (new_r != 0) {
        int64_t quotient = r / new_r;
        int64_t temp_t = t; t = new_t; new_t = temp_t - quotient * new_t;
        int64_t temp_r = r; r = new_r; new_r = temp_r - quotient * new_r;
    }
    if (r > 1) return 1; 
    if (t < 0) t += static_cast<int64_t>(q);
    return static_cast<uint64_t>(t);
}

/**
 * @brief Multiplies multiple ciphertexts using binary tree structure with pointer optimization
 * @param ciphertexts Vector of ciphertext pointers to multiply
 * @param evaluator SEAL Evaluator for homomorphic operations
 * @param relin_keys Relinearization keys to control ciphertext size after multiplication
 * @return Product of all ciphertexts
 * @note Uses move semantics and pointer-based approach to minimize deep copies
 * @note Multiplicative depth: O(log n) where n is the number of ciphertexts
 */
Ciphertext binary_tree_multiply(const vector<const Ciphertext*>& ciphertexts, Evaluator& evaluator, const RelinKeys& relin_keys) {
    if (ciphertexts.empty()) return Ciphertext();
    if (ciphertexts.size() == 1) return *(ciphertexts[0]);
    
    // Allocate the working level
    vector<Ciphertext> current_level;
    current_level.reserve((ciphertexts.size() + 1) / 2);
    
    // First pass: Multiply pointers to populate our first level of intermediate Ciphertexts
    for (size_t i = 0; i < ciphertexts.size(); i += 2) {
        if (i + 1 < ciphertexts.size()) {
            Ciphertext product;
            evaluator.multiply(*(ciphertexts[i]), *(ciphertexts[i + 1]), product);
            evaluator.relinearize_inplace(product, relin_keys);
            current_level.push_back(move(product)); // Move semantics prevent deep copy
        } else {
            current_level.push_back(*(ciphertexts[i])); // Single leftover requires a copy
        }
    }
    
    // Subsequent passes: Perform tree reduction using move semantics
    while (current_level.size() > 1) {
        vector<Ciphertext> next_level;
        next_level.reserve((current_level.size() + 1) / 2);
        for (size_t i = 0; i < current_level.size(); i += 2) {
            if (i + 1 < current_level.size()) {
                Ciphertext product;
                evaluator.multiply(current_level[i], current_level[i + 1], product);
                evaluator.relinearize_inplace(product, relin_keys);
                next_level.push_back(move(product));
            } else {
                next_level.push_back(move(current_level[i]));
            }
        }
        current_level = move(next_level);
    }
    return current_level[0];
}

/**
 * @brief Computes homomorphic threshold function using Lagrange interpolation
 * @param encrypted_x The encrypted input ciphertext X to evaluate
 * @param t Threshold value - outputs 1 if X >= t, else 0
 * @param m Domain upper bound [0, m] for the polynomial
 * @param q Plaintext modulus (finite field size)
 * @param evaluator SEAL Evaluator for homomorphic operations
 * @param batch_encoder SEAL BatchEncoder for encoding plaintext values
 * @param relin_keys Relinearization keys to manage ciphertext size
 * @return Ciphertext containing result: 1 if encrypted_x >= t, else 0
 * @note Implements f_t(X) = Σ(a=t to m) L_a(X) where L_a are Lagrange basis polynomials
 * @note Multiplicative depth: ⌈log₂ m⌉ + 1
 * @note Uses pointer optimization to minimize ciphertext copying overhead
 */
Ciphertext compute_homomorphic_threshold(
    const Ciphertext& encrypted_x, 
    int t, 
    int m, 
    uint64_t q, 
    Evaluator& evaluator,
    BatchEncoder& batch_encoder,
    const RelinKeys& relin_keys) 
{
    size_t slot_count = batch_encoder.slot_count();
    vector<Ciphertext> zero_to_m_diffs(m + 1);
    
    for (int b = 0; b <= m; ++b) {
        vector<uint64_t> b_vec(slot_count, static_cast<uint64_t>(b));
        Plaintext plain_b;
        batch_encoder.encode(b_vec, plain_b);
        evaluator.sub_plain(encrypted_x, plain_b, zero_to_m_diffs[b]);
    }

    Ciphertext encrypted_final_sum;
    bool is_first_term = true;

    for (int a = t; a <= m; ++a) {
        // Collect pointers to objects instead of copying the heavy objects
        vector<const Ciphertext*> product_terms;
        product_terms.reserve(m);
        
        uint64_t denominator_product = 1;

        for (int b = 0; b <= m; ++b) {
            if (b == a) continue;
            
            product_terms.push_back(&zero_to_m_diffs[b]); // Store reference address

            int64_t diff = static_cast<int64_t>(a) - static_cast<int64_t>(b);
            uint64_t positive_diff = (diff % static_cast<int64_t>(q) + q) % q;
            denominator_product = (denominator_product * positive_diff) % q;
        }

        Ciphertext la_product = binary_tree_multiply(product_terms, evaluator, relin_keys);

        uint64_t inverse_multiplier = modular_inverse(denominator_product, q);
        vector<uint64_t> inv_vec(slot_count, inverse_multiplier);
        Plaintext plain_multiplier;
        batch_encoder.encode(inv_vec, plain_multiplier);

        evaluator.multiply_plain_inplace(la_product, plain_multiplier);

        if (is_first_term) {
            encrypted_final_sum = move(la_product);
            is_first_term = false;
        } else {
            evaluator.add_inplace(encrypted_final_sum, la_product);
        }
    }

    return encrypted_final_sum;
}
