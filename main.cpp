#include <iostream>
#include <bitset>
#include <vector>
#include <string>
#include <iomanip>
#include <algorithm>
#include <chrono>
#include <cmath>
#include <numeric>
#include <stdexcept>
#include "seal/seal.h"
#include "packing.h"
#include "equality.h"
#include "threshold.h"
#include "utils.h"

using namespace seal;
using namespace std;

using Clock = std::chrono::steady_clock;

struct StepStats {
    size_t rot_count = 0;
    double elapsed_ms = 0.0;
    int noise_budget_bits = -1;
};

double elapsed_ms_since(const Clock::time_point& start_time) {
    return std::chrono::duration<double, std::milli>(Clock::now() - start_time).count();
}

void print_step_stats(const std::string& step_name, const StepStats& stats) {
    cout << "\n=== " << step_name << " Metrics ===\n";
    cout << "rot_count: " << stats.rot_count << "\n";
    cout << "time_ms:   " << fixed << setprecision(3) << stats.elapsed_ms << "\n";
    cout << "noise_budget_bits: ";
    if (stats.noise_budget_bits >= 0) {
        cout << stats.noise_budget_bits << "\n";
    } else {
        cout << "N/A\n";
    }
}

void print_memory_cost(const std::string& name, std::size_t bytes) {
    double kib = static_cast<double>(bytes) / 1024.0;
    double mib = kib / 1024.0;

    cout << "\n=== " << name << " Memory Cost ===\n";
    cout << "bytes: " << bytes << "\n";
    cout << "KiB:   " << fixed << setprecision(3) << kib << "\n";
    cout << "MiB:   " << fixed << setprecision(3) << mib << "\n";
}

void print_time_cost_summary(
    const std::string& matching_case,
    const StepStats& text_encode_encrypt_stats,
    const StepStats& mask_bit_equality_stats,
    const StepStats& char_equality_stats,
    const StepStats& summation_stats,
    const StepStats& threshold_stats,
    const StepStats& aggregation_stats,
    const StepStats& or_stats,
    const StepStats& final_decrypt_stats) {
    cout << "\n=== Time Cost Summary (" << matching_case << ") ===\n";
    cout << fixed << setprecision(3);
    cout << left << setw(34) << "Input Encode + Encrypt" << ": "
         << text_encode_encrypt_stats.elapsed_ms << " ms\n";
    cout << left << setw(34) << "Step 1 Mask + Bit Equality" << ": "
         << mask_bit_equality_stats.elapsed_ms << " ms\n";
    cout << left << setw(34) << "Step 2 Character Equality" << ": "
         << char_equality_stats.elapsed_ms << " ms\n";

    if (threshold_stats.elapsed_ms > 0.0) {
        cout << left << setw(34) << "Step 3a Summation" << ": "
             << summation_stats.elapsed_ms << " ms\n";
        cout << left << setw(34) << "Step 3b Threshold" << ": "
             << threshold_stats.elapsed_ms << " ms\n";
    } else {
        cout << left << setw(34) << "Step 3 Exact/Wildcard Product" << ": "
             << summation_stats.elapsed_ms << " ms\n";
    }

    cout << left << setw(34) << "Step 4 Pattern Aggregation" << ": "
         << aggregation_stats.elapsed_ms << " ms\n";
    cout << left << setw(34) << "Step 5 OR Evaluation" << ": "
         << or_stats.elapsed_ms << " ms\n";
    cout << left << setw(34) << "Final Decrypt + Decode" << ": "
         << final_decrypt_stats.elapsed_ms << " ms\n";
}

std::vector<int> coeff_modulus_bits_for_mode(const std::string& matching_case) {
    if (matching_case == "exact" || matching_case == "wildcard") {
        return {60, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 60};
    }

    return {60, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 60};
}

std::vector<int> coeff_modulus_bits_for_case(
    const std::string& matching_case,
    size_t poly_modulus_degree,
    size_t num_batches,
    int text_length) {
    int target_bits = (matching_case == "exact" || matching_case == "wildcard") ? 620 : 670;
    int track_levels = static_cast<int>(std::ceil(std::log2(static_cast<double>(text_length))));
    target_bits += std::max(0, track_levels - 6) * 110;

    std::vector<int> bit_sizes;
    int remaining = target_bits;
    while (remaining > 0) {
        if (remaining >= 60) {
            bit_sizes.push_back(60);
            remaining -= 60;
        } else {
            bit_sizes.push_back(std::max(30, remaining));
            remaining = 0;
        }
    }

    if (bit_sizes.size() > 1 && bit_sizes.back() < 50) {
        int spill = bit_sizes.back();
        bit_sizes.pop_back();
        bit_sizes.back() += spill;
        if (bit_sizes.back() > 60) {
            bit_sizes.back() -= spill;
            bit_sizes.push_back(spill);
        }
    }

    return bit_sizes;
}

size_t next_power_of_two(size_t value) {
    size_t result = 1;
    while (result < value) {
        result <<= 1;
    }
    return result;
}

size_t choose_poly_modulus_degree(int text_length, int pattern_length, int bit_length, int num_patterns) {
    size_t base_slots = static_cast<size_t>(text_length) * pattern_length * bit_length;
    size_t degree = 32768;

    if (base_slots > degree) {
        throw std::runtime_error(
            "Requested n and m do not fit in poly_modulus_degree=32768. "
            "Need n * m * 8 <= 32768."
        );
    }

    return degree;
}

int total_coeff_modulus_bits(const std::vector<int>& bit_sizes) {
    return std::accumulate(bit_sizes.begin(), bit_sizes.end(), 0);
}

void rotate_slots(
    const Ciphertext& input,
    size_t steps,
    size_t poly_modulus_degree,
    Evaluator& evaluator,
    const GaloisKeys& galois_keys,
    Ciphertext& destination) {
    size_t slot_count = poly_modulus_degree;
    size_t row_size = slot_count / 2;
    steps %= slot_count;

    if (steps == 0) {
        destination = input;
        return;
    }

    if (steps < row_size) {
        evaluator.rotate_rows(input, static_cast<int>(steps), galois_keys, destination);
        return;
    }

    Ciphertext column_rotated;
    evaluator.rotate_columns(input, galois_keys, column_rotated);
    size_t row_steps = steps - row_size;
    if (row_steps == 0) {
        destination = std::move(column_rotated);
    } else {
        evaluator.rotate_rows(column_rotated, static_cast<int>(row_steps), galois_keys, destination);
    }
}

int main(int argc, char* argv[]) {
    // ==========================================
    // PARSE COMMAND LINE ARGUMENTS
    // ==========================================
    StepStats input_stats;
    auto step_start_time = Clock::now();

    ProgramArgs args;
    
    try {
        args = parse_arguments(argc, argv);
    } catch (const std::exception& e) {
        cerr << "Error: " << e.what() << "\n\n";
        print_usage(argv[0]);
        return 1;
    }
    
    // Read text and patterns from files
    string text;
    vector<string> pattern_strings;
    
    try {
        text = read_text_from_file(args.text_file);
        pattern_strings = read_patterns_from_file(args.patterns_file);
        
        cout << "Successfully loaded:\n";
        cout << "  Text: " << text.length() << " characters from " << args.text_file << "\n";
        cout << "  Patterns: " << pattern_strings.size() << " pattern(s) from " << args.patterns_file << "\n";
        cout << "\n";
    } catch (const std::exception& e) {
        cerr << "Error: " << e.what() << "\n";
        return 1;
    }

    input_stats.elapsed_ms = elapsed_ms_since(step_start_time);
    print_step_stats("Input Loading", input_stats);

    // ==========================================
    // Variable Definitions
    // ==========================================
    int bit_length = 8; // L: To represent to 8 bit of each char
    size_t poly_modulus_degree;
    int num_patterns = pattern_strings.size(); // K

    // Detect user-supplied wildcards BEFORE we add our own padding wildcards,
    // so the reported matching mode reflects what the user actually asked for.
    bool has_wildcard = any_of(pattern_strings.begin(), pattern_strings.end(), [](const string& pattern) {
        return pattern.find('*') != string::npos;
    });

    // Real (unpadded) lengths drive match semantics: the valid track count
    // and the threshold/exactness comparison must be in terms of what the
    // user actually typed, not the padded buffer size.
    int real_text_length = text.length();
    int real_pattern_length = pattern_strings[0].length();

    int match_threshold = (args.threshold > 0) ? args.threshold : real_pattern_length;
    if (match_threshold > real_pattern_length) {
        cerr << "Error: threshold must be less than or equal to pattern length ("
             << real_pattern_length << ")\n";
        return 1;
    }
    bool use_exact_product = (match_threshold == real_pattern_length);

    // ------------------------------------------------------------------
    // Pad text and patterns up to the next power of two.
    //
    // Steps 3, 4, and 5 all fold ciphertext slots together with a
    // rotate-by-half-and-combine tree (see the rotate_slots calls below).
    // That reduction only lands on segment-aligned rotations when the
    // thing being folded (pattern_length in Step 3, num_copies in Step 4,
    // text_length in Step 5) is a power of two. A pattern_length or
    // text_length that isn't a power of two silently corrupts the result
    // instead of erroring — which is why e.g. 8-character patterns worked
    // but 3-character ones didn't.
    //
    // Patterns are padded with '*' (wildcard), which is a no-op for the
    // AND-product: xnor() against an all-wildcard slot always evaluates to
    // 1. Text is padded with '\0', a byte that will never appear in real
    // pattern characters, so it can never falsely match. The existing mask
    // (built from num_tracks, computed below from REAL lengths) already
    // zeroes out every track position past the real text/pattern boundary,
    // so the padded region is automatically excluded from the result.
    // ------------------------------------------------------------------
    size_t padded_text_length = next_power_of_two(static_cast<size_t>(real_text_length));
    size_t padded_pattern_length = next_power_of_two(static_cast<size_t>(real_pattern_length));

    if (padded_text_length > static_cast<size_t>(real_text_length)) {
        text.append(padded_text_length - real_text_length, '\0');
    }
    int wildcard_padding_count = static_cast<int>(padded_pattern_length) - real_pattern_length;
    if (wildcard_padding_count > 0) {
        for (auto& p : pattern_strings) {
            p.append(wildcard_padding_count, '*');
        }
    }

    int text_length = text.length();                  // n, now padded to a power of two
    int pattern_length = pattern_strings[0].length();  // m, now padded to a power of two
    int num_tracks = real_text_length - real_pattern_length + 1; // H, from REAL lengths only

    // Padding wildcards always contribute an automatic per-character match,
    // so in approximate mode the threshold needs to account for the
    // guaranteed extra hits contributed by the padded characters. (No
    // adjustment needed in exact mode: padding is already product-neutral.)
    if (!use_exact_product) {
        match_threshold += wildcard_padding_count;
    }

    string matching_case = has_wildcard ? "wildcard" : (use_exact_product ? "exact" : "approximate");
    try {
        poly_modulus_degree = choose_poly_modulus_degree(text_length, pattern_length, bit_length, num_patterns);
    } catch (const std::exception& e) {
        cerr << "Error: " << e.what() << "\n";
        return 1;
    }
    int num_copies = poly_modulus_degree / (bit_length * text_length * pattern_length); // d
    if (num_copies <= 0) {
        cerr << "Error: text length and pattern length do not fit in the selected BFV slot count\n";
        return 1;
    }
    size_t num_pattern_batches = (static_cast<size_t>(num_patterns) + static_cast<size_t>(num_copies) - 1)
        / static_cast<size_t>(num_copies);
    std::vector<int> coeff_modulus_bits;
    try {
        coeff_modulus_bits = coeff_modulus_bits_for_case(
            matching_case,
            poly_modulus_degree,
            num_pattern_batches,
            text_length
        );
    } catch (const std::exception& e) {
        cerr << "Error: " << e.what() << "\n";
        return 1;
    }
    
    // ==========================================
    // SET UP ENCRYPTION PARAMETERS
    // ==========================================
    StepStats setup_stats;
    step_start_time = Clock::now();

    cout << "Generating Encyption Parameters...\n";
    EncryptionParameters parms(scheme_type::bfv);
    parms.set_poly_modulus_degree(poly_modulus_degree);
    parms.set_coeff_modulus(CoeffModulus::Create(poly_modulus_degree, coeff_modulus_bits));
    parms.set_plain_modulus(PlainModulus::Batching(poly_modulus_degree, 20));

    int secure_max_bits = CoeffModulus::MaxBitCount(poly_modulus_degree);
    int coeff_modulus_total_bits = total_coeff_modulus_bits(coeff_modulus_bits);
    sec_level_type security_level = (secure_max_bits > 0 && coeff_modulus_total_bits <= secure_max_bits)
        ? sec_level_type::tc128
        : sec_level_type::none;
    SEALContext context(parms, true, security_level);
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
    cout << "Generated Encyption Parameters!\n";

    setup_stats.elapsed_ms = elapsed_ms_since(step_start_time);
    print_step_stats("Encryption Setup", setup_stats);

    bool verbose = args.verbose;

    cout << "=== Run Configuration ===" << endl;
    cout << left << setw(19) << "Text Length (n)"   << ": " << text_length
         << (text_length != real_text_length ? "  (padded from " + std::to_string(real_text_length) + ")" : "") << endl;
    cout << left << setw(19) << "Pattern Length (m)"<< ": " << pattern_length
         << (pattern_length != real_pattern_length ? "  (padded from " + std::to_string(real_pattern_length) + ")" : "") << endl;
    cout << left << setw(19) << "Num Patterns (K)"  << ": " << num_patterns << endl;
    cout << left << setw(19) << "Bit Length (L)"    << ": " << bit_length << endl;
    cout << left << setw(19) << "Num Tracks (H)"    << ": " << num_tracks << endl;
    cout << left << setw(19) << "Match Threshold"   << ": " << match_threshold << endl;
    cout << left << setw(19) << "Matching Mode"     << ": " << matching_case << endl;
    cout << left << setw(19) << "Coeff Mod Bits"    << ": " << total_coeff_modulus_bits(coeff_modulus_bits) << endl;
    cout << left << setw(19) << "Poly Degree"       << ": " << poly_modulus_degree << endl;
    cout << left << setw(19) << "Pattern Batches"   << ": " << num_pattern_batches << endl;
    cout << left << setw(19) << "Security Level"    << ": "
         << (security_level == sec_level_type::tc128 ? "tc128" : "none") << endl;

    if (verbose) {
        cout << "\nPatterns to search:\n";
        for (size_t i = 0; i < pattern_strings.size(); ++i) {
            cout << "  " << (i + 1) << ". \"" << pattern_strings[i] << "\"\n";
        }
        cout << "\n";
    }

    // ==========================================
    // Text Packing
    // ==========================================
    StepStats text_preprocessing_stats;
    StepStats text_encode_encrypt_stats;
    step_start_time = Clock::now();

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

    text_preprocessing_stats.elapsed_ms = elapsed_ms_since(step_start_time);

    step_start_time = Clock::now();
    batch_encoder.encode(full_plaintext, plaintext);
    encryptor.encrypt(plaintext, ciphertext);

    text_encode_encrypt_stats.elapsed_ms = elapsed_ms_since(step_start_time);
    text_encode_encrypt_stats.noise_budget_bits = decryptor.invariant_noise_budget(ciphertext);
    std::size_t encrypted_text_bytes = ciphertext.save_size(compr_mode_type::zstd);
    print_step_stats("Text Preprocessing", text_preprocessing_stats);
    print_step_stats("Input Encode + Encrypt", text_encode_encrypt_stats);
    print_memory_cost("Encrypted Text Ciphertext", encrypted_text_bytes);

    // Export encrypted text ciphertext if requested
    if (args.export_ciphertext) {
        std::string ct_path = args.output_dir + "/encrypted_text.bin";
        std::ofstream ct_file(ct_path, std::ios::binary);
        if (ct_file.is_open()) {
            ciphertext.save(ct_file, compr_mode_type::zstd);
            ct_file.close();
            cout << "CIPHERTEXT_EXPORTED: " << ct_path << "\n";
            cout << "CIPHERTEXT_SIZE_BYTES: " << encrypted_text_bytes << "\n";
            cout << "CIPHERTEXT_NOISE_BUDGET: " << text_encode_encrypt_stats.noise_budget_bits << "\n";
        } else {
            cerr << "Warning: Failed to save ciphertext to " << ct_path << "\n";
        }
    }

    // ==========================================
    // Pattern Evaluation in Batches
    // ==========================================
    StepStats mask_bit_equality_stats;
    StepStats char_equality_stats;
    StepStats summation_stats;
    StepStats threshold_stats;
    StepStats aggregation_stats;
    StepStats or_stats;
    Ciphertext result_ct;
    std::vector<Ciphertext> batch_result_ciphertexts;

    Plaintext encoded_mask;
    vector<uint64_t> mask = create_mask(num_tracks * bit_length, text_length * bit_length, pattern_length, poly_modulus_degree, verbose);
    batch_encoder.encode(mask, encoded_mask);

    std::vector<uint64_t> output_mask(poly_modulus_degree, 0);
    output_mask[0] = 1;
    Plaintext encoded_output_mask;
    batch_encoder.encode(output_mask, encoded_output_mask);

    for (size_t batch_start = 0; batch_start < pattern_strings.size(); batch_start += static_cast<size_t>(num_copies)) {
        size_t batch_end = std::min(pattern_strings.size(), batch_start + static_cast<size_t>(num_copies));
        size_t batch_pattern_count = batch_end - batch_start;

        // Step 1: mask + bit equality for this pattern batch.
        step_start_time = Clock::now();
        Ciphertext masked_ciphertext = ciphertext;
        evaluator.multiply_plain_inplace(masked_ciphertext, encoded_mask);

        std::vector<std::vector<uint64_t>> batch_patterns;
        std::vector<std::vector<uint64_t>> batch_inverse_patterns;
        for (size_t pattern_index = batch_start; pattern_index < batch_end; ++pattern_index) {
            auto pattern_pair = create_base_pattern_pair(
                pattern_strings[pattern_index],
                bit_length,
                num_tracks,
                text_length
            );
            batch_patterns.push_back(std::move(pattern_pair.first));
            batch_inverse_patterns.push_back(std::move(pattern_pair.second));
        }

        std::vector<uint64_t> packed_patterns = pack_patterns(batch_patterns, poly_modulus_degree, verbose && batch_start == 0);
        std::vector<uint64_t> packed_inverse_patterns = pack_patterns(batch_inverse_patterns, poly_modulus_degree, false);
        
        // Export encoded pattern plaintexts if requested
        if (args.export_ciphertext && batch_start == 0) {
            // Encode the entire batch as one plaintext
            Plaintext pattern_plaintext;
            batch_encoder.encode(packed_patterns, pattern_plaintext);
            
            // Save to one file for the batch
            std::string pattern_pt_path = args.output_dir + "/encoded_patterns_batch.bin";
            std::ofstream pattern_pt_file(pattern_pt_path, std::ios::binary);
            if (pattern_pt_file.is_open()) {
                std::size_t pattern_pt_size = pattern_plaintext.save(pattern_pt_file);
                pattern_pt_file.close();
                cout << "PATTERN_PLAINTEXT_EXPORTED: " << pattern_pt_path << "\n";
                cout << "PATTERN_PLAINTEXT_SIZE_BYTES: " << pattern_pt_size << "\n";
                cout << "PATTERN_BATCH_COUNT: " << batch_pattern_count << "\n";
            }
        }
        
        Ciphertext bit_equality_ciphertext = xnor(
            context,
            batch_encoder,
            evaluator,
            masked_ciphertext,
            packed_patterns,
            packed_inverse_patterns
        );
        mask_bit_equality_stats.elapsed_ms += elapsed_ms_since(step_start_time);
        mask_bit_equality_stats.noise_budget_bits = decryptor.invariant_noise_budget(bit_equality_ciphertext);

        // Step 2: character equality.
        step_start_time = Clock::now();
        Ciphertext rotated_L_over_2_ct;
        evaluator.rotate_rows(bit_equality_ciphertext, bit_length / 2, galois_keys, rotated_L_over_2_ct);
        char_equality_stats.rot_count++;
        evaluator.multiply_inplace(bit_equality_ciphertext, rotated_L_over_2_ct);
        evaluator.relinearize_inplace(bit_equality_ciphertext, relin_keys);

        Ciphertext rotated_L_over_4_ct;
        evaluator.rotate_rows(bit_equality_ciphertext, bit_length / 4, galois_keys, rotated_L_over_4_ct);
        char_equality_stats.rot_count++;
        evaluator.multiply_inplace(bit_equality_ciphertext, rotated_L_over_4_ct);
        evaluator.relinearize_inplace(bit_equality_ciphertext, relin_keys);

        Ciphertext rotated_L_over_8_ct;
        evaluator.rotate_rows(bit_equality_ciphertext, bit_length / 8, galois_keys, rotated_L_over_8_ct);
        char_equality_stats.rot_count++;
        evaluator.multiply_inplace(bit_equality_ciphertext, rotated_L_over_8_ct);
        evaluator.relinearize_inplace(bit_equality_ciphertext, relin_keys);
        char_equality_stats.elapsed_ms += elapsed_ms_since(step_start_time);
        char_equality_stats.noise_budget_bits = decryptor.invariant_noise_budget(bit_equality_ciphertext);

        // Step 3: exact/wildcard product or approximate threshold.
        Ciphertext threshold_result;
        if (use_exact_product) {
            step_start_time = Clock::now();
            threshold_result = bit_equality_ciphertext;

            for (size_t i = (pattern_length * text_length * bit_length) / 2; i >= (text_length * bit_length); i = i / 2) {
                Ciphertext rotated_ct;
                rotate_slots(threshold_result, i, poly_modulus_degree, evaluator, galois_keys, rotated_ct);
                summation_stats.rot_count++;
                evaluator.multiply_inplace(threshold_result, rotated_ct);
                evaluator.relinearize_inplace(threshold_result, relin_keys);
            }

            summation_stats.elapsed_ms += elapsed_ms_since(step_start_time);
            summation_stats.noise_budget_bits = decryptor.invariant_noise_budget(threshold_result);
        } else {
            step_start_time = Clock::now();
            for (size_t i = (pattern_length * text_length * bit_length) / 2; i >= (text_length * bit_length); i = i / 2) {
                Ciphertext rotated_ct;
                rotate_slots(bit_equality_ciphertext, i, poly_modulus_degree, evaluator, galois_keys, rotated_ct);
                summation_stats.rot_count++;
                evaluator.add_inplace(bit_equality_ciphertext, rotated_ct);
            }
            summation_stats.elapsed_ms += elapsed_ms_since(step_start_time);
            summation_stats.noise_budget_bits = decryptor.invariant_noise_budget(bit_equality_ciphertext);

            step_start_time = Clock::now();
            uint64_t plain_modulus = parms.plain_modulus().value();
            int threshold_domain = pattern_length;
            threshold_result = compute_homomorphic_threshold_paterson_stockmeyer(
                bit_equality_ciphertext,
                match_threshold,
                threshold_domain,
                plain_modulus,
                evaluator,
                batch_encoder,
                relin_keys
            );
            threshold_stats.elapsed_ms += elapsed_ms_since(step_start_time);
            threshold_stats.noise_budget_bits = decryptor.invariant_noise_budget(threshold_result);
        }

        // Step 4: aggregate patterns within this batch.
        step_start_time = Clock::now();
        if (batch_pattern_count > 1) {
            for (size_t i = (num_copies * pattern_length * text_length * bit_length) / 4;
                 i >= (pattern_length * text_length * bit_length); i = i / 2) {
                Ciphertext rotated_ct;
                rotate_slots(threshold_result, i, poly_modulus_degree, evaluator, galois_keys, rotated_ct);
                aggregation_stats.rot_count++;
                evaluator.add_inplace(threshold_result, rotated_ct);
            }
            Ciphertext rotated_ct2;
            evaluator.rotate_columns(threshold_result, galois_keys, rotated_ct2);
            aggregation_stats.rot_count++;
            evaluator.add_inplace(threshold_result, rotated_ct2);
        }
        aggregation_stats.elapsed_ms += elapsed_ms_since(step_start_time);
        aggregation_stats.noise_budget_bits = decryptor.invariant_noise_budget(threshold_result);

        // Step 5: OR over tracks for this batch.
        step_start_time = Clock::now();
        Ciphertext minus_ct = one_minus_ct(context, batch_encoder, evaluator, threshold_result, poly_modulus_degree);

        for (size_t i = (text_length * bit_length) / 2; i >= bit_length ; i = i / 2) {
            Ciphertext rotated_ct;
            rotate_slots(minus_ct, i, poly_modulus_degree, evaluator, galois_keys, rotated_ct);
            or_stats.rot_count++;
            evaluator.multiply_inplace(minus_ct, rotated_ct);
            evaluator.relinearize_inplace(minus_ct, relin_keys);
        }

        Ciphertext batch_result_ct = one_minus_ct(context, batch_encoder, evaluator, minus_ct, poly_modulus_degree);
        evaluator.multiply_plain_inplace(batch_result_ct, encoded_output_mask);
        or_stats.noise_budget_bits = decryptor.invariant_noise_budget(batch_result_ct);
        batch_result_ciphertexts.push_back(std::move(batch_result_ct));

        or_stats.elapsed_ms += elapsed_ms_since(step_start_time);
    }

    step_start_time = Clock::now();
    if (batch_result_ciphertexts.empty()) {
        throw std::runtime_error("No pattern batches were evaluated.");
    }

    result_ct = std::move(batch_result_ciphertexts.front());
    for (size_t i = 1; i < batch_result_ciphertexts.size(); ++i) {
        evaluator.add_inplace(result_ct, batch_result_ciphertexts[i]);
    }
    evaluator.multiply_plain_inplace(result_ct, encoded_output_mask);
    or_stats.elapsed_ms += elapsed_ms_since(step_start_time);
    or_stats.noise_budget_bits = decryptor.invariant_noise_budget(result_ct);

    print_step_stats("Step 1 Mask + Bit Equality", mask_bit_equality_stats);
    print_step_stats("Step 2 Character Equality", char_equality_stats);
    if (use_exact_product) {
        print_step_stats("Step 3 Exact/Wildcard Product", summation_stats);
    } else {
        print_step_stats("Step 3a Summation", summation_stats);
        print_step_stats("Step 3b Threshold", threshold_stats);
    }
    print_step_stats("Step 4 Pattern Aggregation", aggregation_stats);
    print_step_stats("Step 5 OR Evaluation", or_stats);

    StepStats final_decrypt_stats;
    step_start_time = Clock::now();
    Plaintext decrypted_result;
    decryptor.decrypt(result_ct, decrypted_result);

    std::vector<uint64_t> result_vector;
    batch_encoder.decode(decrypted_result, result_vector);
    final_decrypt_stats.elapsed_ms = elapsed_ms_since(step_start_time);
    print_step_stats("Final Decrypt + Decode", final_decrypt_stats);

    cout << "\n=== Final Result ===\n";
    if (result_vector[0] == 1) {
        cout << "Pattern FOUND: result_vector[0] = " << result_vector[0] << "\n";
    } else {
        cout << "Pattern NOT FOUND: result_vector[0] = " << result_vector[0] << "\n";
    }

    double total_step_time_ms = text_encode_encrypt_stats.elapsed_ms
        + mask_bit_equality_stats.elapsed_ms
        + char_equality_stats.elapsed_ms
        + summation_stats.elapsed_ms
        + threshold_stats.elapsed_ms
        + aggregation_stats.elapsed_ms
        + or_stats.elapsed_ms
        + final_decrypt_stats.elapsed_ms;

    print_time_cost_summary(
        matching_case,
        text_encode_encrypt_stats,
        mask_bit_equality_stats,
        char_equality_stats,
        summation_stats,
        threshold_stats,
        aggregation_stats,
        or_stats,
        final_decrypt_stats
    );

    cout << "\n=== Total Step Runtime Metrics ===\n";
    cout << "time_ms:   " << fixed << setprecision(3) << total_step_time_ms << "\n";

    return 0;
}