#include <iostream>
#include <bitset>
#include <vector>
#include <string>
#include <algorithm>
#include "seal/seal.h"
#include "packing.h"

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
    // 2. Rotation
    // ==========================================
    string text = "Lorem ipsum dolor sit amet, consectetur adipiscing elit vivamus.";
    int pattern_length = 8;
    int bit_length = 8; // To represent to 8 bit of each char

    vector<uint64_t> text_in_bits = convert_text_to_bits(text, bit_length);

    // Double Checking if texts match
    cout << "Original Text: " << text << "\n";
    cout << "text_in_bits Text: ";
    print_bits_as_string(text_in_bits, bit_length);

    vector<uint64_t> base_plaintext = rotate_bits(text_in_bits, bit_length, pattern_length, true);

    // Final Verification
    cout << "\n=== Rotation End Result ===\n";
    print_bits_as_string(base_plaintext, bit_length);

    // ==========================================
    // 3. Multi-Block Packing & Zero-Padding
    // ==========================================
    vector<uint64_t> full_plaintext = pack_and_pad(base_plaintext, poly_modulus_degree, true);

    // ==========================================
    // 4. Microsoft SEAL Encoding
    // ==========================================
    Plaintext plaintext;
    Ciphertext ciphertext;

    batch_encoder.encode(full_plaintext, plaintext);
    encryptor.encrypt(plaintext, ciphertext);

    return 0;
}
 