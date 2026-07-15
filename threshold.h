#include "seal/seal.h"
#include <vector>
#include <numeric>
#include <cmath>

using namespace std;
using namespace seal;

uint64_t add_mod(uint64_t a, uint64_t b, uint64_t q) {
    return (a + b) % q;
}

uint64_t mul_mod(uint64_t a, uint64_t b, uint64_t q) {
    return static_cast<uint64_t>((static_cast<unsigned __int128>(a) * b) % q);
}

uint64_t sub_mod(uint64_t a, uint64_t b, uint64_t q) {
    return (a + q - (b % q)) % q;
}

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
 * @brief Builds monomial coefficients for f_t(x) over domain {0, ..., m}.
 * @return coefficients c where f_t(x) = c[0] + c[1]x + ... + c[m]x^m mod q
 */
vector<uint64_t> interpolate_threshold_coefficients(int t, int m, uint64_t q) {
    vector<uint64_t> coefficients(m + 1, 0);

    for (int a = t; a <= m; ++a) {
        vector<uint64_t> basis(1, 1);
        uint64_t denominator_product = 1;

        for (int b = 0; b <= m; ++b) {
            if (b == a) continue;

            vector<uint64_t> next_basis(basis.size() + 1, 0);
            uint64_t negative_b = (q - static_cast<uint64_t>(b)) % q;
            for (size_t degree = 0; degree < basis.size(); ++degree) {
                next_basis[degree] = add_mod(
                    next_basis[degree],
                    mul_mod(basis[degree], negative_b, q),
                    q
                );
                next_basis[degree + 1] = add_mod(next_basis[degree + 1], basis[degree], q);
            }
            basis = move(next_basis);

            int64_t diff = static_cast<int64_t>(a) - static_cast<int64_t>(b);
            uint64_t positive_diff = (diff % static_cast<int64_t>(q) + q) % q;
            denominator_product = mul_mod(denominator_product, positive_diff, q);
        }

        uint64_t denominator_inverse = modular_inverse(denominator_product, q);
        for (size_t degree = 0; degree < basis.size(); ++degree) {
            coefficients[degree] = add_mod(
                coefficients[degree],
                mul_mod(basis[degree], denominator_inverse, q),
                q
            );
        }
    }

    return coefficients;
}

Plaintext encode_constant(uint64_t value, BatchEncoder& batch_encoder) {
    vector<uint64_t> values(batch_encoder.slot_count(), value);
    Plaintext plain;
    batch_encoder.encode(values, plain);
    return plain;
}

void add_plain_constant_inplace(Ciphertext& encrypted, uint64_t value, BatchEncoder& batch_encoder, Evaluator& evaluator) {
    if (value == 0) return;
    Plaintext plain = encode_constant(value, batch_encoder);
    evaluator.add_plain_inplace(encrypted, plain);
}

Ciphertext multiply_by_plain_constant(
    const Ciphertext& encrypted,
    uint64_t value,
    BatchEncoder& batch_encoder,
    Evaluator& evaluator) {
    Ciphertext result;
    if (value == 0) {
        Plaintext zero = encode_constant(0, batch_encoder);
        evaluator.multiply_plain(encrypted, zero, result);
        return result;
    }

    Plaintext plain = encode_constant(value, batch_encoder);
    evaluator.multiply_plain(encrypted, plain, result);
    return result;
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

/**
 * @brief Computes homomorphic threshold function using monomial interpolation
 *        and Paterson-Stockmeyer polynomial evaluation.
 */
Ciphertext compute_homomorphic_threshold_paterson_stockmeyer(
    const Ciphertext& encrypted_x,
    int t,
    int m,
    uint64_t q,
    Evaluator& evaluator,
    BatchEncoder& batch_encoder,
    const RelinKeys& relin_keys)
{
    vector<uint64_t> coefficients = interpolate_threshold_coefficients(t, m, q);
    int degree = m;
    while (degree > 0 && coefficients[degree] == 0) {
        degree--;
    }

    if (degree == 0) {
        Plaintext constant_plain = encode_constant(coefficients[0], batch_encoder);
        Ciphertext result;
        evaluator.multiply_plain(encrypted_x, encode_constant(0, batch_encoder), result);
        evaluator.add_plain_inplace(result, constant_plain);
        return result;
    }

    int baby_step = static_cast<int>(ceil(sqrt(static_cast<double>(degree + 1))));
    int giant_count = (degree + baby_step) / baby_step;

    vector<Ciphertext> x_powers(baby_step);
    x_powers[0] = encrypted_x;
    for (int power = 2; power <= baby_step; ++power) {
        evaluator.multiply(x_powers[power - 2], encrypted_x, x_powers[power - 1]);
        evaluator.relinearize_inplace(x_powers[power - 1], relin_keys);
    }

    Ciphertext x_to_baby = x_powers[baby_step - 1];
    vector<Ciphertext> giant_powers(giant_count);
    if (giant_count > 1) {
        giant_powers[0] = x_to_baby;
        for (int giant = 2; giant < giant_count; ++giant) {
            evaluator.multiply(giant_powers[giant - 2], x_to_baby, giant_powers[giant - 1]);
            evaluator.relinearize_inplace(giant_powers[giant - 1], relin_keys);
        }
    }

    Ciphertext result;
    bool result_initialized = false;

    for (int giant = 0; giant < giant_count; ++giant) {
        int start_degree = giant * baby_step;
        if (start_degree > degree) break;

        Ciphertext baby_value;
        bool baby_initialized = false;
        uint64_t constant_coeff = coefficients[start_degree];

        for (int offset = 1; offset < baby_step && start_degree + offset <= degree; ++offset) {
            uint64_t coeff = coefficients[start_degree + offset];
            if (coeff == 0) continue;

            Ciphertext term = multiply_by_plain_constant(
                x_powers[offset - 1],
                coeff,
                batch_encoder,
                evaluator
            );

            if (!baby_initialized) {
                baby_value = move(term);
                baby_initialized = true;
            } else {
                evaluator.add_inplace(baby_value, term);
            }
        }

        if (baby_initialized) {
            add_plain_constant_inplace(baby_value, constant_coeff, batch_encoder, evaluator);
        } else {
            baby_value = multiply_by_plain_constant(encrypted_x, 0, batch_encoder, evaluator);
            add_plain_constant_inplace(baby_value, constant_coeff, batch_encoder, evaluator);
        }

        Ciphertext group_value;
        if (giant == 0) {
            group_value = move(baby_value);
        } else {
            evaluator.multiply(baby_value, giant_powers[giant - 1], group_value);
            evaluator.relinearize_inplace(group_value, relin_keys);
        }

        if (!result_initialized) {
            result = move(group_value);
            result_initialized = true;
        } else {
            evaluator.add_inplace(result, group_value);
        }
    }

    return result;
}
