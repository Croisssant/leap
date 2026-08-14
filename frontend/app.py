import streamlit as st
import subprocess
import os
import tempfile
import re
import json
import time

from datetime import datetime

if 'run_pattern_matching' not in st.session_state:
    st.session_state.run_pattern_matching = False

if 'matching_results' not in st.session_state:
    st.session_state.matching_results = None  

if 'show_product_data' not in st.session_state:
    st.session_state.show_product_data = False

if 'product_data' not in st.session_state:
    st.session_state.product_data = None

if 'show_ciphertext' not in st.session_state:
    st.session_state.show_ciphertext = False

if 'ciphertext_content' not in st.session_state:
    st.session_state.ciphertext_content = None

if 'matched_patterns' not in st.session_state:
    st.session_state.matched_patterns = []

if 'seller_wallet_balance' not in st.session_state:
    st.session_state.seller_wallet_balance = "0.00"

def toggle_run_pattern_matching():
    st.session_state.run_pattern_matching = not st.session_state.run_pattern_matching 

def on_item_change():
    st.session_state.show_product_data = False
    st.session_state.matching_results = None
    st.session_state.show_ciphertext = False
    st.session_state.ciphertext_content = None
    st.session_state.matched_patterns = []
    st.session_state.seller_wallet_balance = "0.00"

def render_pattern_box_html(word, matched):
    css_class = "pattern-chip-matched" if matched else "pattern-chip"
    return f'<div class="{css_class}">{word}</div>'

def render_wallet_balance():
    """Redraws the seller's wallet balance from st.session_state.seller_wallet_balance.
    Relies on `wallet_balance_placeholder` (an st.empty()) already existing."""
    with wallet_balance_placeholder.container():
        st.markdown(
            '<div class="wallet-card-inner">'
            '<div class="wallet-label">Wallet Balance</div>'
            f'<div class="wallet-amount"><span class="wallet-currency">RM</span><div class="wallet-value-div"><span class="wallet-value">{st.session_state.seller_wallet_balance}</span></div></div>'
            '</div>',
            unsafe_allow_html=True,
        )

def render_ciphertext_card(hex_code, caption):
    st.markdown("### Encrypted Product Name")
    with st.container(key="ciphertext-card", border=True):
        st.code(hex_code, language="text", width="content")
    st.caption(caption)

def render_pattern_grid():
    """Redraws every pattern box, highlighting any word currently in
    st.session_state.matched_patterns. Relies on `patterns` and
    `pattern_placeholders` (dict of word -> st.empty()) already existing."""
    for word in patterns:
        with pattern_placeholders[word].container():
            st.markdown(
                render_pattern_box_html(word, word in st.session_state.matched_patterns),
                unsafe_allow_html=True,
            )

def render_spm_placeholder():
    """Draws the right thing into spm_button_placeholder for the current state:
    the button, an 'executing' message while the backend is running, or nothing
    once the ciphertext is already on screen."""
    if st.session_state.show_ciphertext:
        spm_button_placeholder.empty()
    elif st.session_state.run_pattern_matching:
        with spm_button_placeholder.container():
            st.html("""
                <style>
                .loader {
                    border: 4px solid #f3f3f3;
                    border-top: 4px solid #FF4B4B; /* Streamlit Red */
                    border-radius: 50%;
                    width: 30px;
                    height: 30px;
                    animation: spin 1s linear infinite;
                    display: inline-block;
                    vertical-align: middle;
                    margin-right: 10px;
                }
                @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }
                .loading-text {
                    font-family: sans-serif;
                    color: white;
                }
                </style>
                <div>
                    <div class="loader"></div>
                    <span class="loading-text">Executing secure pattern matching on encrypted data...</span>
                </div>
            """)
       
    elif st.session_state.show_product_data:
        with spm_button_placeholder.container():
            if st.button("Secure Pattern Matching", key="spm_btn", on_click=toggle_run_pattern_matching, width='stretch'):
                st.session_state.matching_results = None
    else:
        spm_button_placeholder.empty()

# Helper function to find project root
def find_project_root():
    """Find the project root by looking for CMakeLists.txt"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    current_dir = script_dir
    
    # Search upward for CMakeLists.txt (project root indicator)
    while current_dir != os.path.dirname(current_dir):  # Stop at filesystem root
        if os.path.exists(os.path.join(current_dir, 'CMakeLists.txt')):
            return current_dir
        current_dir = os.path.dirname(current_dir)
    
    # If not found, return the script's parent directory as fallback
    return os.path.dirname(script_dir)

# Get project root and executable path
PROJECT_ROOT = find_project_root()
EXECUTABLE_PATH = os.path.join(PROJECT_ROOT, 'build', 'pattern_matching')
IMAGE_PATH = os.path.join(PROJECT_ROOT, "frontend", "images", "vape.jpg")

# 1. Page Configuration
st.set_page_config(
    page_title="LEAP",
    layout="wide"
)

st.markdown(
    """
    <style>
    header[data-testid="stHeader"] {
        visibility: hidden;
    }
    .block-container {
        padding-top: 1rem;
        padding-bottom: 0rem;
    }
    div[data-testid="stJson"] span, 
    div[data-testid="stJson"] pre {
        font-size: 25px;
    }
    .st-key-item-card {
        background-color: #ffffff !important;
        border-radius: 12px !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05) !important;
        border: 1px solid #e0e0e0 !important;
        text-align: center;
    }
    /* Add padding to the inner block */
    div[data-testid="stVerticalBlockBorderWrapper"] > div {
        padding: 20px !important;
    }
    /* Style images within bordered containers */
    div[data-testid="stVerticalBlockBorderWrapper"] img {
        border-radius: 8px;
        margin-bottom: 10px;
    }
    .product-title {
        font-size: 25px;
        font-weight: 600;
        color: #1a1a1a;
        line-height: 1.4;
        margin: 1px 0;
    }
    .product-price {
        font-size: 18px;
        color: #ff4b4b;
        font-weight: 700;
        margin-bottom: 10px;
    }
    .product-desc {
        font-size: 14px;
        color: #666666;
        margin-bottom: 15px;
        line-height: 1.4;
    }
    /* Style the Streamlit button container to center it */
    div.stButton > button:first-child {
        background-color: #ff4b4b;
        color: white;
        border-radius: 8px;
        border: none;
        padding: 8px 24px;
        font-weight: 600;
        width: 100%;
        transition: all 0.3s ease;
    }
    div.stButton > button:first-child:hover {
        background-color: #e03e3e;
        color: white;
        border: none;
    }
    .st-key-spm_btn button {
        background-color: #8FAEEB !important;
       border-radius: 16px !important;
        overflow: hidden !important;
        
        /* 1. The Raised Border Trick */
        border-style: solid !important;
        border-width: 2px 4px 5px 2px !important;                 /* Thicker on bottom/right */
        border-color: #B2C9F3 #6385CE #4B6AA6 #A1BCEF !important; /* Top (light), Right (dark), Bottom (darkest), Left (light) */

        /* 2. Optimized Drop Shadow for depth */
        box-shadow: 
            0 8px 16px rgba(0, 0, 0, 0.3),
            inset 0 2px 3px rgba(255, 255, 255, 0.4) !important; /* Inner top glow for gloss */
            
        /* Smooth transformation physics */
        transition: transform 0.1s ease, box-shadow 0.1s ease !important;
    }
    .st-key-spm_btn button:active {
        transform: translateY(3px) translateX(1px) !important;
        border-width: 3px 3px 2px 3px !important;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2) !important;
    }
    .st-key-spm_btn button div p {
        font-size: 24px;
        font-weight: bold;
    }
    .st-key-wallet_balance {
        background: linear-gradient(135deg, #4f8cff 0%, #7b2ff7 100%);
        color: #ffffff;
        border-radius: 16px;
        overflow: hidden;
        border: 3px solid rgba(255, 255, 255, 0.15);
        border-width: 0 3px 3px 0;

        box-shadow: 
            0 15px 30px rgba(0, 0, 0, 0.6),
            0 5px 15px rgba(0, 0, 0, 0.4);
                
    }
    .wallet-card-inner {
        display: grid;
        height: 200px;
        box-sizing: border-box;
        padding: 24px;
    }
    .wallet-label {
        grid-area: 1 / 1;
        align-self: start;
        justify-self: start;
        font-size: 13px;
        font-weight: 600;
        color: rgba(255, 255, 255, 0.75);
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }
    .wallet-amount {
        display: flex;
        flex-direction: row;
        align-items: flex-start;
        width: 200px;
        grid-area: 1 / 1;
        align-self: center;
        justify-self: center;
        font-weight: 700;
        color: #ffffff;
        margin-top: 30px;
    }
    .wallet-currency {
        font-size: 30px;
        font-weight: 600;
        color: rgba(255, 255, 255, 0.75);
        margin-right: 40px;
        line-height: 1;
    }
    .wallet-value-div {
        display: flex;
        align-items: flex-start;
        align-self: center;
        justify-self: center;
        height: 70px;
    }
    .wallet-value {
        font-size: 60px;
        line-height: 1;
        margin-top: -10px;
    }
    .st-key-wallet-payment-panel {
        background-color: #181b20;
        border-radius: 16px !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        box-shadow:
            0 20px 40px rgba(0, 0, 0, 0.55),
            0 8px 16px rgba(0, 0, 0, 0.4),
            inset 0 1px 0 rgba(255, 255, 255, 0.06) !important;
    }
    .st-key-pattern-panel {
    
        border-radius: 16px !important;
        border: 4px solid #2d3139 !important;
        box-shadow:
            inset 6px 6px 14px rgba(0, 0, 0, 0.85),
            inset -4px -4px 10px rgba(255, 255, 255, 0.03) !important;
    }
    .pattern-chip {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 100%;
        height: 48px;
        margin-bottom: 14px;
        background: linear-gradient(135deg, #f8f9fb 0%, #edeff3 100%);
        border: 3px solid rgba(0, 0, 0, 0.3);
        border-width: 0 3px 3px 0;
        border-radius: 10px;
        box-shadow:
            inset 0 1px 0 rgba(255, 255, 255, 0.9),
            0 10px 18px rgba(0, 0, 0, 0.6);
        font-size: 20px;
        font-weight: 700;
        letter-spacing: 0.02em;
        color: #4b5160;
        transition: all 0.3s ease;
    }
    .pattern-chip-matched {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 100%;
        height: 48px;
        margin-bottom: 14px;
        border-radius: 10px;
        font-size: 20px;
        font-weight: 700;
        letter-spacing: 0.02em;
        transition: all 0.3s ease;
        background: linear-gradient(135deg, #ff6b6b 0%, #c62828 100%);
        border: 3px solid rgba(80, 0, 0, 0.5);
        border-width: 0 3px 3px 0;
        color: #ffffff;
        box-shadow:
            inset 0 1px 0 rgba(255, 255, 255, 0.5),
            0 10px 20px rgba(198, 40, 40, 0.7);
        animation: pattern-flag-pulse 1.4s ease-in-out infinite;
    }
    @keyframes pattern-flag-pulse {
        0%, 100% {
            box-shadow:
                inset 0 1px 0 rgba(255, 255, 255, 0.5),
                0 10px 20px rgba(198, 40, 40, 0.7);
        }
        50% {
            box-shadow:
                inset 0 1px 0 rgba(255, 255, 255, 0.55),
                0 12px 28px rgba(198, 40, 40, 1);
        }
    }
    [data-testid="stAlert"] p, 
    [data-testid="stNotification"] p {
        font-size: 25px;
    }
    .st-key-ciphertext-card {
        border-radius: 16px !important;
        border: 4px solid #2d3139 !important;
        box-shadow:
            inset 6px 6px 14px rgba(0, 0, 0, 0.85),
            inset -4px -4px 10px rgba(255, 255, 255, 0.03) !important;
    }
    .st-key-json-card {
        background: linear-gradient(135deg, #0e1117 0%, #0e1117 100%);
        color: #e2e8f0;
        border-radius: 16px;
   
        width: 100%;
        
        border: 4px solid #2d3139;
        box-shadow:
            inset 6px 6px 14px rgba(0, 0, 0, 0.85),
            inset -4px -4px 10px rgba(255, 255, 255, 0.03);
    }
    .glowing-text {
        margin-top: -10px;
        color: white;
        font-size: 35px;
        text-shadow:
            0 0 6px rgba(255, 255, 255, 0.60),  /* Crisp, half-transparent edge */
            0 0 20px rgba(255, 255, 255, 0.25), /* Very soft, faint outer glow */
            0 0 40px rgba(138, 153, 173, 0.15); /* Tiny hint of background matching grey */
    }
    </style>
    """,
    unsafe_allow_html=True,  # Fixed argument name here
)

# st.title("Digital Transaction Compliance Tool")
st.html("<h1 class='glowing-text'>Digital Transaction Compliance Tool</h1>")

threshold = -1
# 3. Text Input Fields in Main Layout - Two Column Layout
col1, combined_col, col4 = st.columns([1, 2, 1])

with col1:
    st.subheader("E-commerce Store")
  
    with st.container(height=900, border=False):
       
        ITEMS = {
            "Vape": {
                "display_name": "VapeVac(Registered AMZ Brand) – Pocket-Sized Personal Air Filter for Discreet Output Reduction | Minimizes Odor, Keeps Air Fresh | Not an Emission Device – 500+ Uses",
                "price": "99.99",
                "currency": "RM",
                "desc": "Features a sleek, pocket-friendly aluminum chassis paired with an optimized heating element. Delivers smooth, consistent vapor production with a long-lasting rechargeable battery.",
                "image": "vape.jpg",
            },
            "Lighter": {
                "display_name": "Lighter",
                "price": "19.99",
                "currency": "RM",
                "desc": "A compact, refillable butane lighter with a windproof flame and ergonomic grip.",
                "image": "lighter.jpg",
            },
        }
        selected_item = st.selectbox(
                "Choose an item:",
                options=list(ITEMS.keys()),
                key="selected_item",
                on_change=on_item_change,
        )
        item = ITEMS[selected_item]
        item_image_path = os.path.join(PROJECT_ROOT, "frontend", "images", item["image"])

        with st.container(border=True, key="item-card"):
            st.image(item_image_path, width="stretch")
            st.markdown(f'<div class="product-title">{item["display_name"]}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="product-price">{item["currency"]} {item["price"]}</div>', unsafe_allow_html=True)
            # st.markdown(f'<div class="product-desc">{item["desc"]}</div>', unsafe_allow_html=True)

            if st.button("Buy Now", key="buy_btn"):
                st.session_state.matching_results = None
                st.session_state.show_product_data = True
                st.session_state.show_ciphertext = False
                st.session_state.ciphertext_content = None
                st.session_state.matched_patterns = []
                TEXT_LIMIT = 10
                json_product_name = ITEMS[selected_item]["display_name"].lower()
                
                st.session_state.product_data = json.dumps(
                {
                    "product_name": json_product_name[:TEXT_LIMIT] + "..." if len(json_product_name) > TEXT_LIMIT else json_product_name,
                    "currency": ITEMS[selected_item]["currency"],
                    "price": ITEMS[selected_item]["price"],
                    "date": datetime.now(),
                    "location": "Singapore"
                },
                indent=4,
                default=str)
              


with combined_col:
    with st.container(border=True, key="wallet-payment-panel"):
        col2, col3 = st.columns([1, 1])
    
        with col2:
            st.subheader("Buyer's Wallet (PayNow)")
            with st.container(height=500, key="json-card"):
                if st.session_state.show_product_data:
                    st.json(st.session_state.product_data, expanded=True, width="stretch")

                

        with col3:
            patterns = ["vape", "drug", "njoy", "bomb", "vuse", "smok", "kpod", "juul"]
            st.subheader("Global Payment (AliPay+)")
            with st.container(border=True, key="pattern-panel"):
                num_cols = 2
                cols = st.columns(num_cols)
                pattern_placeholders = {}
                for index, word in enumerate(patterns):
                    col_idx = index % num_cols
                    pattern_placeholders[word] = cols[col_idx].empty()
                
                render_pattern_grid()
            st.markdown("<p style='font-size: 20px; color: #E3E4E5;'>Showing 8 out 1024 words</p>", unsafe_allow_html=True)
   

        spm_button_placeholder = st.empty()
        render_spm_placeholder()

        ciphertext_display = st.empty()

        # Re-render the ciphertext on subsequent reruns (st.empty() is recreated
        # fresh every script run, so its previous contents don't survive on their own)
        if st.session_state.show_ciphertext and st.session_state.ciphertext_content:
            with ciphertext_display.container():
                render_ciphertext_card(
                    st.session_state.ciphertext_content["hex"],
                    st.session_state.ciphertext_content["caption"],
                )


with col4:
   st.subheader("Seller's Wallet (TnG)")
   
   with st.container(height=700, border=False):
    with st.container(height=200, border=False, key="wallet_balance"):
        wallet_balance_placeholder = st.empty()
        render_wallet_balance()

    loading_placeholder = st.empty()
  

# 4. Execution Logic
if st.session_state.run_pattern_matching:
    # Input validation
    # text_input = ITEMS[selected_item]["display_name"].lower()
    text_input = st.session_state.product_data
    # print(text_input)

    pattern_lengths = [len(p) for p in patterns]

    with loading_placeholder.container():
       
        st.info("Awaiting payment...")

    if len(set(pattern_lengths)) > 1:
        st.error(f"❌ All patterns must have the same length. Found lengths: {set(pattern_lengths)}")
    else:
        # Validate threshold against pattern length
        pattern_length = len(patterns[0])
        effective_threshold = threshold if threshold > 0 else pattern_length
        
        if threshold > pattern_length:
            st.error(f"❌ Threshold ({threshold}) cannot be greater than pattern length ({pattern_length})")
            st.info(f"💡 Set threshold to -1 or {pattern_length} for exact matching, or a value between 1 and {pattern_length} for approximate matching")
        else:
            # Create a temporary directory to safely store input files for the binary to read
            with tempfile.TemporaryDirectory() as tmpdir:
                text_path = os.path.join(tmpdir, "text.txt")
                pattern_path = os.path.join(tmpdir, "patterns.txt")
                    
                # Write text inputs to temporary files
                with open(text_path, "w", encoding="utf-8") as f:
                    f.write(text_input)
                with open(pattern_path, "w", encoding="utf-8") as f:
                    f.write('\n'.join(patterns))
                    
                # Construct the C++ command line arguments
                cmd = [
                    EXECUTABLE_PATH,
                    "--text", text_path,
                    "--pattern", pattern_path,
                    "--threshold", str(threshold)
                ]
                
                    
                cmd.append("--export-ciphertext")
                cmd.append("--output-dir")
                cmd.append(tmpdir)
                    
                try:
                    # Run the binary and capture standard output/error
                    result = subprocess.run(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        check=True
                    )
                        
                    # Parse the output to extract match result and ciphertext info
                    output = result.stdout
                    match_found = False
                    result_value = None
                    matching_mode = "unknown"
                    ciphertext_path = None
                    ciphertext_size = None
                    ciphertext_noise_budget = None
                    pattern_plaintext_path = None
                    pattern_plaintext_size = None
                    pattern_batch_count = None
                        
                    # Look for the final result line and ciphertext info
                    for line in output.split('\n'):
                        if "Pattern FOUND" in line:
                            match_found = True
                            # Extract result_vector[0] value
                            match = re.search(r'result_vector\[0\]\s*=\s*(\d+)', line)
                            if match:
                                result_value = int(match.group(1))
                        elif "Pattern NOT FOUND" in line:
                            match_found = False
                            match = re.search(r'result_vector\[0\]\s*=\s*(\d+)', line)
                            if match:
                                result_value = int(match.group(1))
                        elif "Matching Mode" in line:
                            # Extract matching mode
                            match = re.search(r'Matching Mode\s*:\s*(\w+)', line)
                            if match:
                                matching_mode = match.group(1)
                        elif "CIPHERTEXT_EXPORTED:" in line:
                            ciphertext_path = line.split("CIPHERTEXT_EXPORTED:")[1].strip()
                        elif "CIPHERTEXT_SIZE_BYTES:" in line:
                            ciphertext_size = int(line.split("CIPHERTEXT_SIZE_BYTES:")[1].strip())
                        elif "CIPHERTEXT_NOISE_BUDGET:" in line:
                            ciphertext_noise_budget = int(line.split("CIPHERTEXT_NOISE_BUDGET:")[1].strip())
                        elif "PATTERN_PLAINTEXT_EXPORTED:" in line:
                            pattern_plaintext_path = line.split("PATTERN_PLAINTEXT_EXPORTED:")[1].strip()
                        elif "PATTERN_PLAINTEXT_SIZE_BYTES:" in line:
                            pattern_plaintext_size = int(line.split("PATTERN_PLAINTEXT_SIZE_BYTES:")[1].strip())
                        elif "PATTERN_BATCH_COUNT:" in line:
                            pattern_batch_count = int(line.split("PATTERN_BATCH_COUNT:")[1].strip())
                        
                    if match_found:
                        st.session_state.matching_results = True  

                        # The encrypted computation only confirms THAT a pattern
                        # matched, not which one - that's by design, since which
                        # pattern matched is itself sensitive. Since we're on the
                        # buyer's side and already hold the plaintext product data
                        # pre-encryption, we can do a cheap local substring check
                        # purely to decide which box to highlight in the UI.
                        try:
                            product_fields = json.loads(text_input)
                            searchable_text = " ".join(str(v) for v in product_fields.values()).lower()
                        except (json.JSONDecodeError, TypeError):
                            searchable_text = text_input.lower()
                        st.session_state.matched_patterns = [
                            p for p in patterns if p.lower() in searchable_text
                        ]

                    else:
                        st.session_state.matching_results = False
                        st.session_state.matched_patterns = []

                    if st.session_state.matching_results is not None:
                        if ciphertext_path:
                            # Read and display ciphertext
                            if os.path.exists(ciphertext_path):
                                with open(ciphertext_path, "rb") as f:
                                    ciphertext_data = f.read()
                                    
                                # Display hex preview in expandable section
                                hex_preview = ciphertext_data[:128].hex()
                                # Format hex in lines of 64 characters (32 bytes per line)
                                formatted_hex = '\n'.join([hex_preview[i:i+64] for i in range(0, len(hex_preview), 64)])

                                hex_code = formatted_hex + "\n..." if len(ciphertext_data) > 128 else formatted_hex
                                caption = f"Showing first {min(128, len(ciphertext_data))} bytes of {len(ciphertext_data)} total bytes"

                                with ciphertext_display.container():
                                    render_ciphertext_card(hex_code, caption)

                                # Remember this so it keeps rendering on future reruns,
                                # and so the "Secure Pattern Matching" button stays hidden
                                st.session_state.show_ciphertext = True
                                st.session_state.ciphertext_content = {
                                    "hex": hex_code,
                                    "caption": caption,
                                }

                                time.sleep(1)

                    if match_found:
                        loading_placeholder.error("Payment Rejected")

                    else:
                        loading_placeholder.success("Payment Accepted")
                        st.session_state.seller_wallet_balance = f"{ITEMS[selected_item]['price']}"
                        render_wallet_balance()
                

                    render_pattern_grid()
                except subprocess.CalledProcessError as e:
                    # Parse error message for specific issues
                    error_output = e.stderr if e.stderr else e.stdout if hasattr(e, 'stdout') else ""
                        
                    # Check for specific error types
                    if "threshold" in error_output.lower():
                        st.error("❌ Threshold validation error")
                        st.warning(f"The C++ backend rejected the threshold value.")
                        st.info(f"💡 **Tip:** Set threshold to 0 or {len(patterns[0])} for exact matching, or a value between 1 and {len(patterns[0])} for approximate matching")
                    elif "pattern length mismatch" in error_output.lower() or "same length" in error_output.lower():
                        st.error("❌ Pattern length mismatch error")
                        st.warning("All patterns must have the same length.")
                        st.info("💡 **Tip:** Check that all patterns in your input have exactly the same number of characters")
                    elif "failed to open" in error_output.lower() or "file" in error_output.lower():
                        st.error("❌ File reading error")
                        st.warning("The C++ binary couldn't read the input files.")
                        st.info("💡 **Tip:** This is usually a temporary issue. Try running again.")
                    else:
                        st.error("❌ The C++ binary encountered an error during execution.")
                        
                    # Show detailed error information
                    with st.expander("🐛 Error Details", expanded=True):
                        if e.stderr:
                            st.markdown("**Standard Error (stderr):**")
                            st.code(e.stderr, language="text")
                        if hasattr(e, 'stdout') and e.stdout:
                            st.markdown("**Standard Output (stdout):**")
                            st.code(e.stdout, language="text")
                        if not e.stderr and not (hasattr(e, 'stdout') and e.stdout):
                            st.code(f"Return code: {e.returncode}\nNo error output captured.", language="text")
                                
                except FileNotFoundError:
                    st.error(f"❌ Executable not found at: `{EXECUTABLE_PATH}`")
                    st.info(f"💡 **Project Root:** `{PROJECT_ROOT}`")
                    st.info("💡 **Tip:** Build the project first using:\n```bash\ncd " + PROJECT_ROOT + "\ncmake --build build\n```")
                except Exception as e:
                    st.error("❌ An unexpected error occurred")
                    st.warning(f"Error type: {type(e).__name__}")
                    with st.expander("🐛 Error Details", expanded=True):
                        st.code(str(e), language="text")

                # Whether it succeeded or hit an error above, we're done "executing" -
                # reset the flag and refresh the placeholder (button, or nothing if the
                # ciphertext is now showing) so the UI doesn't stay stuck mid-transition.
                st.session_state.run_pattern_matching = False
                render_spm_placeholder()