#include <iostream>
#include <bitset>
#include <vector>
#include <string>
#include <iomanip>
#include <algorithm>
#include "seal/seal.h"
#include "packing.h"
#include "equality.h"
#include "threshold.h"

using namespace seal;
using namespace std;


int main() {
    // ==========================================
    // SET UP ENCRYPTION PARAMETERS
    // ==========================================
    EncryptionParameters parms(scheme_type::bfv);
    size_t poly_modulus_degree = 32768;
    parms.set_poly_modulus_degree(poly_modulus_degree);
    parms.set_coeff_modulus(CoeffModulus::BFVDefault(poly_modulus_degree));
    parms.set_plain_modulus(PlainModulus::Batching(poly_modulus_degree, 20));

    SEALContext context(parms);
    Evaluator evaluator(context);

    KeyGenerator keygen(context);
    SecretKey secret_key = keygen.secret_key();
    PublicKey public_key;
    keygen.create_public_key(public_key);

    Encryptor encryptor(context, public_key);
    BatchEncoder batch_encoder(context); 

    GaloisKeys galois_keys;
    keygen.create_galois_keys(galois_keys);

    RelinKeys relin_keys;
    keygen.create_relin_keys(relin_keys);

    Decryptor decryptor(context, secret_key);

    // ==========================================
    // Variable Definitions
    // ==========================================
    string text = "Lorem ipsum dolor sit amet, consectetur adipiscing elit vivamus.";
    string pattern = "vivamus.";
    int text_length = text.length(); // n
    int pattern_length = pattern.length(); // m
    int bit_length = 8; // L: To represent to 8 bit of each char
    int num_tracks = text_length - pattern_length + 1; // H
    int num_copies = poly_modulus_degree / (bit_length * text_length * pattern_length); // d
    bool verbose = true;

    if (verbose) {
        cout << "=== Variables ===" << endl;
        cout << left << setw(19) << "Text (String)"     << ": " << "\"" << text << "\"" << endl;
        cout << left << setw(19) << "Pattern (String)"  << ": " << "\"" << pattern << "\"" << endl;
        cout << left << setw(19) << "Text Length (m)"   << ": " << text_length << endl;
        cout << left << setw(19) << "Pattern Length (n)"<< ": " << pattern_length << endl;
        cout << left << setw(19) << "Bit Length (L)"    << ": " << bit_length << endl;
        cout << left << setw(19) << "Num Tracks (H)"    << ": " << num_tracks << endl;
        cout << "\n";
    }

    // ==========================================
    // Text Packing
    // ==========================================
    vector<uint64_t> text_in_bits = convert_text_to_bits(text, bit_length);

    // Double Checking if texts match
    if (verbose) {
        cout << "=== Text to Bit Conversion Check ===" << endl;
        cout << left << setw(19) << "Original Text    " << ": " << text << "\n";
        cout << left << setw(19) << "text_in_bits Text" << ": ";
        print_bits_as_string(text_in_bits, bit_length);
    }
 

    vector<uint64_t> base_plaintext = rotate_bits(text_in_bits, bit_length, pattern_length, verbose);

    // Final Verification
    if (verbose) {
        cout << "\n=== Rotation End Result ===\n";
        print_bits_as_string(base_plaintext, bit_length);
    }

    // Packing & Zero-Padding
    vector<uint64_t> full_plaintext = pack_and_pad(base_plaintext, poly_modulus_degree, verbose);

    Plaintext plaintext;
    Ciphertext ciphertext;

    batch_encoder.encode(full_plaintext, plaintext);
    encryptor.encrypt(plaintext, ciphertext);

    // ==========================================
    // 1. Mask + Bit Equality
    // ==========================================

    // Applying Mask
    Plaintext encoded_mask;
    vector<uint64_t> mask = create_mask(num_tracks * bit_length, text_length * bit_length, pattern_length, poly_modulus_degree, verbose);
    batch_encoder.encode(mask, encoded_mask);
    evaluator.multiply_plain_inplace(ciphertext, encoded_mask);

    // Bit Equality
    std::vector<std::vector<uint64_t>> all_patterns = { create_base_pattern(pattern, bit_length, num_tracks, text_length) }; // Expand in the future to loop multi patterns
    std::vector<uint64_t> packed_patterns = pack_patterns(all_patterns, poly_modulus_degree, verbose);
    Ciphertext bit_equality_ciphertext = xnor(context, batch_encoder, evaluator, ciphertext, packed_patterns);


    // ==========================================
    // 2. Character Equality
    // ==========================================
    
    // Multiply with rotation by L/2 = 4
    Ciphertext rotated_L_over_2_ct;
    evaluator.rotate_rows(bit_equality_ciphertext, bit_length / 2, galois_keys, rotated_L_over_2_ct);
    evaluator.multiply_inplace(bit_equality_ciphertext, rotated_L_over_2_ct);
    evaluator.relinearize_inplace(bit_equality_ciphertext, relin_keys);

    // Multiply with rotation by L/4 = 2
    Ciphertext rotated_L_over_4_ct;
    evaluator.rotate_rows(bit_equality_ciphertext, bit_length / 4, galois_keys, rotated_L_over_4_ct);
    evaluator.multiply_inplace(bit_equality_ciphertext, rotated_L_over_4_ct);
    evaluator.relinearize_inplace(bit_equality_ciphertext, relin_keys);

    // Multiply with rotation by L/8 = 1
    Ciphertext rotated_L_over_8_ct;
    evaluator.rotate_rows(bit_equality_ciphertext, bit_length / 8, galois_keys, rotated_L_over_8_ct);
    evaluator.multiply_inplace(bit_equality_ciphertext, rotated_L_over_8_ct);
    evaluator.relinearize_inplace(bit_equality_ciphertext, relin_keys);

    if (verbose) {
        Plaintext debug_plain;
        decryptor.decrypt(bit_equality_ciphertext, debug_plain);
        std::vector<uint64_t> debug_vec;
        batch_encoder.decode(debug_plain, debug_vec);
        cout << "\n=== After Character Equality ===\n";
        cout << "Track matches (1 = all bits matched for this char): ";
        for (size_t track = 0; track < num_tracks; track++) {
            cout << debug_vec[track * bit_length] << " ";
        }
        cout << "\n";
    }

    // ==========================================
    // 3. Summation and Threshold Comparison
    // ==========================================
    
    // Rotation + Summation
    // index = RnL/2, RnL/4, ..., nL
    // Where R=1, n=text_length, L=bit_length
    // We need to sum across all m pattern windows for each track
    // So we rotate from (pattern_length * text_length * bit_length)/2 down to (text_length * bit_length)
    for (size_t i = (pattern_length * text_length * bit_length) / 2; i >= (text_length * bit_length) ; i = i / 2) {
        Ciphertext rotated_ct;
        evaluator.rotate_rows(bit_equality_ciphertext, i, galois_keys, rotated_ct);
        evaluator.add_inplace(bit_equality_ciphertext, rotated_ct);
    }

    
    if (verbose) {
        Plaintext debug_plain;
        decryptor.decrypt(bit_equality_ciphertext, debug_plain);
        std::vector<uint64_t> debug_vec;
        batch_encoder.decode(debug_plain, debug_vec);
        cout << "\n=== After Summation (before threshold) ===\n";
        cout << "Character match count per track: ";
        for (size_t track = 0; track < num_tracks; track++) {
            cout << debug_vec[track * bit_length] << " ";
        }
        cout << "\n";
    }
    
    // Thresholding
    // Get plaintext modulus for threshold function
    uint64_t plain_modulus = parms.plain_modulus().value();
    
    // Apply threshold function: GE(x, t) where t = pattern_length
    // This outputs 1 if x >= pattern_length (full match), 0 otherwise
    // IMPORTANT: domain m must be > threshold t for proper polynomial interpolation
    Ciphertext threshold_result = compute_homomorphic_threshold(
        bit_equality_ciphertext,
        pattern_length,          // threshold t = 8
        2 * pattern_length,      // domain m = 16 (must be > t)
        plain_modulus,           // field size q
        evaluator,
        batch_encoder,
        relin_keys
    );

    if (verbose) {
        Plaintext debug_plain;
        decryptor.decrypt(threshold_result, debug_plain);
        std::vector<uint64_t> debug_vec;
        batch_encoder.decode(debug_plain, debug_vec);
        cout << "\n=== After Threshold ===\n";
        cout << "Pattern match per track (1 = full match): ";
        for (size_t track = 0; track < num_tracks; track++) {
            cout << debug_vec[track * bit_length] << " ";
        }
        cout << "\n";
    }

    // ==========================================
    // 4. Aggregation Across Patterns
    // ==========================================
    // Aggregate threshold results across all K patterns using rotation
    // Each pattern's results are stored in different copies (d copies total)
    // Rotation indices: (d*m*n*L)/2, (d*m*n*L)/4, ..., down to m*n*L
    // This sums all K pattern results using binary tree aggregation
    // Only execute when K > 1 (multiple patterns to aggregate)
    
    size_t num_patterns = all_patterns.size();
    
    if (num_patterns > 1) {
        for (size_t i = (num_copies * pattern_length * text_length * bit_length) / 2; 
             i >= (pattern_length * text_length * bit_length); i = i / 2) {
            Ciphertext rotated_ct;
            evaluator.rotate_rows(threshold_result, i, galois_keys, rotated_ct);
            evaluator.add_inplace(threshold_result, rotated_ct);
        }
    }
    
    if (verbose) {
        Plaintext debug_plain;
        decryptor.decrypt(threshold_result, debug_plain);
        std::vector<uint64_t> debug_vec;
        batch_encoder.decode(debug_plain, debug_vec);
        cout << "\n=== After Pattern Aggregation (Step 4) ===\n";
        cout << "Aggregated matches per track (any pattern): ";
        for (size_t track = 0; track < num_tracks; track++) {
            cout << debug_vec[track * bit_length] << " ";
        }
        cout << "\n";
    }

    // ==========================================
    // 5. OR Evaluation Over Tracks
    // ==========================================

    Ciphertext minus_ct = one_minus_ct(context, batch_encoder, evaluator, threshold_result, poly_modulus_degree);

     for (size_t i = (text_length * bit_length) / 2; i >= bit_length ; i = i / 2) {
        Ciphertext rotated_ct;
        evaluator.rotate_rows(minus_ct, i, galois_keys, rotated_ct);
        evaluator.multiply_inplace(minus_ct, rotated_ct);
        evaluator.relinearize_inplace(minus_ct, relin_keys);
    }
    
    Ciphertext result_ct = one_minus_ct(context, batch_encoder, evaluator, minus_ct, poly_modulus_degree);

    Plaintext decrypted_result;
    decryptor.decrypt(result_ct, decrypted_result);

    std::vector<uint64_t> result_vector;
    batch_encoder.decode(decrypted_result, result_vector);

    if (verbose) {
        cout << "\n=== Final Result ===\n";
        if (result_vector[0] == 1) {
            cout << "Pattern FOUND: result_vector[0] = " << result_vector[0] << "\n";
        } else {
            cout << "Pattern NOT FOUND: result_vector[0] = " << result_vector[0] << "\n";
        }
    }

    return 0;
}
 