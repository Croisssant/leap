#include <iostream>
#include <bitset>
#include <vector>
#include <string>
#include <iomanip>
#include <algorithm>
#include "seal/seal.h"
#include "packing.h"
#include "equality.h"

using namespace seal;
using namespace std;


int main() {
    // ==========================================
    // 1. SET UP ENCRYPTION PARAMETERS
    // ==========================================
    EncryptionParameters parms(scheme_type::bfv);
    size_t poly_modulus_degree = 32768;
    parms.set_poly_modulus_degree(poly_modulus_degree);
    parms.set_coeff_modulus(CoeffModulus::BFVDefault(poly_modulus_degree));
    parms.set_plain_modulus(PlainModulus::Batching(poly_modulus_degree, 20));

    SEALContext context(parms);

    KeyGenerator keygen(context);
    SecretKey secret_key = keygen.secret_key();
    PublicKey public_key;
    keygen.create_public_key(public_key);

    Encryptor encryptor(context, public_key);
    BatchEncoder batch_encoder(context); 

    // ==========================================
    // Variable Definitions
    // ==========================================
    string text = "Lorem ipsum dolor sit amet, consectetur adipiscing elit vivamus.";
    string pattern = "vivamus.";
    int text_length = text.length(); // m
    int pattern_length = pattern.length(); // n
    int bit_length = 8; // L: To represent to 8 bit of each char
    int num_tracks = text_length - pattern_length + 1; // H
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
    // 2. Rotation
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

    // ==========================================
    // 3. Multi-Block Packing & Zero-Padding
    // ==========================================
    vector<uint64_t> full_plaintext = pack_and_pad(base_plaintext, poly_modulus_degree, verbose);

    Plaintext plaintext;
    Ciphertext ciphertext;

    batch_encoder.encode(full_plaintext, plaintext);
    encryptor.encrypt(plaintext, ciphertext);

    // ==========================================
    // 4. Mask + Bit Equality
    // ==========================================
    vector<uint64_t> mask = create_mask(num_tracks * bit_length, text_length * bit_length, pattern_length, poly_modulus_degree);


    return 0;
}
 