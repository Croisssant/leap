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

if 'pattern_panel_matched' not in st.session_state:
    st.session_state.pattern_panel_matched = False

if 'pattern_panel_call_id' not in st.session_state:
    st.session_state.pattern_panel_call_id = 0

if 'seller_wallet_balance' not in st.session_state:
    st.session_state.seller_wallet_balance = "0.00"

def toggle_run_pattern_matching():
    st.session_state.run_pattern_matching = not st.session_state.run_pattern_matching 

def on_item_change():
    st.session_state.show_product_data = False
    st.session_state.matching_results = None
    st.session_state.show_ciphertext = False
    st.session_state.ciphertext_content = None
    st.session_state.pattern_panel_matched = False
    st.session_state.seller_wallet_balance = "0.00"

def render_pattern_box_html(word):
    return f'<div class="pattern-chip">{word}</div>'

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

def render_pattern_panel():
    """Redraws the whole pattern panel into `pattern_panel_placeholder`
    (an st.empty() already existing). The panel's container key switches
    between the plain and "matched" styling depending on
    st.session_state.pattern_panel_matched, so the panel itself changes
    color when a match is found - individual chips are always plain.

    This can be called more than once within the same script run (e.g.
    once for the initial layout, again after the backend result comes
    back), and Streamlit requires explicit keys to be unique per run even
    across placeholder redraws - so a monotonically increasing call id is
    appended to the key. The CSS below matches on the key *prefix* rather
    than the exact key so styling still applies regardless of the suffix."""
    st.session_state.pattern_panel_call_id += 1
    call_id = st.session_state.pattern_panel_call_id
    key_prefix = "pattern-panel-matched" if st.session_state.pattern_panel_matched else "pattern-panel-plain"
    panel_key = f"{key_prefix}-{call_id}"
    with pattern_panel_placeholder.container():
        with st.container(border=True, key=panel_key):
            num_cols = 2
            cols = st.columns(num_cols)
            for index, word in enumerate(display_patterns):
                col_idx = index % num_cols
                with cols[col_idx]:
                    st.markdown(render_pattern_box_html(word), unsafe_allow_html=True)
            st.markdown("""
                <div style="display: flex; gap: 20px; justify-content: center; align-items: center; margin-bottom: 10px;">
                    <div style="width: 15px; height: 15px; background-color: white; border-radius: 50%;"></div>
                    <div style="width: 15px; height: 15px; background-color: white; border-radius: 50%;"></div>
                    <div style="width: 15px; height: 15px; background-color: white; border-radius: 50%;"></div>
                </div>""", unsafe_allow_html=True)

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

def custom_colored_json(json_str, target_key):
    # 🎨 CONFIGURATION: Set your exact colors here
    COLOR_KEYS = "#E5E8ED"
    COLOR_VALUES = "#FD971F"
    
    # Highlight style for the targeted value
    HIGHLIGHT_BG = "#FD971F" 
    HIGHLIGHT_TEXT = "#2A1D12"

    # 1. Generate formatted JSON string and escape safety tokens
    json_str = json_str.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    
    # 2. Match keys, string values, booleans, and numbers
    # Group 1 = Keys, Group 2 = Values
    pattern = r'("[^"]*"\s*:)|("[^"]*"|true|false|\b\d+\b)'
    
    def process_token(match):
        key_match = match.group(1)
        value_match = match.group(2)
        
        if key_match:
            # Colorize all keys uniformly
            return f'<span style="color: {COLOR_KEYS};">{key_match}</span>'
        elif value_match:
            # Colorize standard values uniformly
            return f'<span style="color: {COLOR_VALUES};">{value_match}</span>'
        return match.group(0)

    # First pass: Color all components uniformly
    processed_html = re.sub(pattern, process_token, json_str)
    
    # 3. Second pass: Locate the colorized target key and replace its following value span
    # This precisely finds our target key span, matches whitespace/colons, and grabs the next value span
    target_pattern = (
        r'(<span style="[^"]*">"' + re.escape(target_key) + r'"\s*:</span>)'  # Target Key Span
        r'(\s*)'                                                               # Space
        r'(<span style="[^"]*">)([^<]+)(</span>)'                             # Original Value Span
    )
    
    def inject_special_highlight(m):
        key_span = m.group(1)
        spacing = m.group(2)
        # Reconstruct the value span with your special highlight configuration
        new_value_span = (
            f'<span style="'
            f'background-color: {HIGHLIGHT_BG}; '
            f'color: {HIGHLIGHT_TEXT}; '
            f'font-weight: bold; '
            f'padding: 2px 6px; '
            f'border-radius: 4px; '
        
            f'">{m.group(4)}</span>'
        )
        return f"{key_span}{spacing}{new_value_span}"
        
    final_html = re.sub(target_pattern, inject_special_highlight, processed_html)
    
    # 4. Construct wrapper mirroring native st.json layout
    return (
        '<div style="'
        'font-family: monospace; '
        'font-size: 25px; '
        'font-weight: bold; '
        'background-color: transparent; '
        'padding: 10px 0px; '
        'line-height: 1.6;'
        '">'
        '<pre style="'
        'margin: 0; '
        'font-family: inherit; '
        'white-space: pre-wrap; '
        'word-wrap: normal;'
        '"><code>'
        + final_html +
        '</code></pre>'
        '</div>'
    )

   
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
    [class*="st-key-pattern-panel-plain-"] {
    
        border-radius: 16px !important;
        border: 4px solid #2d3139 !important;
        box-shadow:
            inset 6px 6px 14px rgba(0, 0, 0, 0.85),
            inset -4px -4px 10px rgba(255, 255, 255, 0.03) !important;
    }
    [class*="st-key-pattern-panel-matched-"] {
    
        border-radius: 16px !important;
        border: 4px solid #c62828 !important;
        box-shadow:
            inset 6px 6px 14px rgba(80, 0, 0, 0.85),
            inset -4px -4px 10px rgba(255, 107, 107, 0.08),
            0 0 24px rgba(198, 40, 40, 0.55) !important;
        transition: all 0.3s ease;
    }
    .pattern-chip {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 100%;
        height: 48px;
        margin-bottom: 14px;
        background: linear-gradient(135deg, #ffe3e3 0%, #ffc9c9 100%);
        border: 3px solid rgba(166, 25, 25, 0.4);
        border-width: 0 3px 3px 0;
        border-radius: 10px;
        box-shadow:
            inset 0 1px 0 rgba(255, 255, 255, 0.4),
            0 10px 18px rgba(139, 0, 0, 0.25);
        font-size: 20px;
        font-weight: 700;
        letter-spacing: 0.02em;
        color: #5c0f13;
        transition: all 0.3s ease;
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
st.html("<h1 class='glowing-text'>Fast Secure Multi-Pattern Matching for Alipay+ Risk Control Strategy</h1>")

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
                "display_name": "SUPRUS Electric Lighter Arc Windproof Flameless USB Rechargeable Lighter with Safety Lock",
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
                st.session_state.pattern_panel_matched = False
                TEXT_LIMIT = 30
                json_product_name = ITEMS[selected_item]["display_name"].lower()
                
                st.session_state.product_data = json.dumps(
                {
                    "product_name": json_product_name[:TEXT_LIMIT] + "..." if len(json_product_name) > TEXT_LIMIT else json_product_name,
                    "currency": ITEMS[selected_item]["currency"],
                    "price": ITEMS[selected_item]["price"],
                    "date": datetime.now(),
                    "location": "Singapore"
                },
                indent=2,
                default=str)
              


with combined_col:
    with st.container(border=True, key="wallet-payment-panel"):
        col2, col3 = st.columns([1, 1])
    
        with col2:
            st.subheader("Buyer's Wallet (PayNow)")
            with st.container(height=500, key="json-card"):
                if st.session_state.show_product_data:
                    
                    st.html(custom_colored_json(st.session_state.product_data, target_key="product_name")) 
                    #st.json(st.session_state.product_data, expanded=True, width="stretch")

                

        with col3:
            display_patterns = ["vape", "hookah", "njoy", "bomb", "e-juice", "smok", "kpod", "e-cigeratte"]
            st.subheader("Global Payment (AliPay+)")
            pattern_panel_placeholder = st.empty()
            render_pattern_panel()
            st.markdown("<p style='font-size: 25px; color: #E3E4E5;'>Showing 8 of 1024 <span style='font-size: 30px; color: #d92d35; font-weight: bold;'>restricted product names</span></p>", unsafe_allow_html=True)
   

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
    text_input = ITEMS[selected_item]["display_name"].lower()
    # text_input = st.session_state.product_data
    # print(text_input)
    patterns = ["vape", "drug", "njoy", "bomb", "vuse", "smok", "kpod", "juul"]
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
                        st.session_state.pattern_panel_matched = True
                    else:
                        st.session_state.matching_results = False
                        st.session_state.pattern_panel_matched = False

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
                

                    render_pattern_panel()
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