import streamlit as st
import subprocess
import os
import tempfile
import re
import json

from datetime import datetime
from streamlit_extras.let_it_rain import rain

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

def toggle_run_pattern_matching():
    st.session_state.run_pattern_matching = not st.session_state.run_pattern_matching 

def on_item_change():
    st.session_state.show_product_data = False
    st.session_state.matching_results = None
    st.session_state.show_ciphertext = False
    st.session_state.ciphertext_content = None

def render_spm_placeholder():
    """Draws the right thing into spm_button_placeholder for the current state:
    the button, an 'executing' message while the backend is running, or nothing
    once the ciphertext is already on screen."""
    if st.session_state.show_ciphertext:
        spm_button_placeholder.empty()
    elif st.session_state.run_pattern_matching:
        with spm_button_placeholder.container():
            st.info("🔐 Executing secure pattern matching on encrypted data...")
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

st.title("Digital Transaction Compliance Tool")
st.write("Risk control stragegy to ban illegal transaction via homomorphic encryption-based pattern matching.")

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
        margin-top: 10px;
        margin-bottom: 5px;
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
    </style>
    """,
    unsafe_allow_html=True,  # Fixed argument name here
)



threshold = -1
# 3. Text Input Fields in Main Layout - Two Column Layout
col1, combined_col, col4 = st.columns([1, 2, 1])

with col1:
    st.subheader("🔍 E-commerce Store")
  
    with st.container(height=700, border=False):
       
        ITEMS = {
            "Vape": {
                "price": "RM99.99",
                "desc": "Features a sleek, pocket-friendly aluminum chassis paired with an optimized heating element. Delivers smooth, consistent vapor production with a long-lasting rechargeable battery.",
                "image": "vape.jpg",
            },
            "Lighter": {
                "price": "RM19.99",
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
            st.markdown(f'<div class="product-title">{selected_item}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="product-price">{item["price"]}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="product-desc">{item["desc"]}</div>', unsafe_allow_html=True)

            if st.button("Buy Now", key="buy_btn"):
                st.session_state.matching_results = None
                st.session_state.show_product_data = True
                st.session_state.show_ciphertext = False
                st.session_state.ciphertext_content = None
                st.session_state.product_data = json.dumps(
                {
                    "product_name": selected_item.lower(),
                    "date": datetime.now(),
                    "location": "Singapore"
                },
                indent=4,
                default=str)
              


with combined_col:
    with st.container(border=True):
        col2, col3 = st.columns([1, 1])
    
        with col2:
            st.subheader("📝 Buyer's Wallet (PayNow)")
            if st.session_state.show_product_data:
                st.json(st.session_state.product_data, expanded=True, width="stretch")

        with col3:
            patterns = ["vape", "drug", "acid", "bomb", "mace", "hemp"]
            st.subheader("🔍 Global Payment (AliPay+)")
            num_cols = 2
            cols = st.columns(num_cols)
            for index, word in enumerate(patterns):
                col_idx = index % num_cols

                with cols[col_idx].container():
                    st.markdown(
                        f"""
                            <div style='
                                display: flex;
                                align-items: center;
                                justify-content: center;
                                width: 100%;
                                height: 50px;
                                margin-bottom: 20px;
                                background-color: #f0f2f6;
                                border-radius: 8px;
                                font-size: 25px;
                                font-weight: bold;
                                color: #31333F;
                            '>
                            {word}
                            </div>
                        """, 
                        unsafe_allow_html=True)

        spm_button_placeholder = st.empty()
        render_spm_placeholder()

        ciphertext_display = st.empty()

        # Re-render the ciphertext on subsequent reruns (st.empty() is recreated
        # fresh every script run, so its previous contents don't survive on their own)
        if st.session_state.show_ciphertext and st.session_state.ciphertext_content:
            with ciphertext_display.container():
                st.markdown("### Ciphertext")
                st.code(st.session_state.ciphertext_content["hex"], language="text")
                st.caption(st.session_state.ciphertext_content["caption"])


with col4:
   st.subheader("🔍 Seller's Wallet (TnG)")
   
   with st.container(height=700, border=False):
    loading_placeholder = st.empty()
    with loading_placeholder.container():
        st.info("Awaiting payment...")
  

# 4. Execution Logic
if st.session_state.run_pattern_matching:
    # Input validation
    text_input = st.session_state.product_data

    pattern_lengths = [len(p) for p in patterns]
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
            # Show effective threshold info
            if threshold <= 0 or threshold == pattern_length:
                st.toast(f"exact matching mode (threshold: {pattern_length})", icon='ℹ️')
            else:
                st.toast(f"approximate matching mode (threshold: {threshold})", icon='ℹ️')
            
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
                        st.toast(f"MATCH FOUND")
                        st.session_state.matching_results = True  
                        loading_placeholder.error("Payment Rejected")
                        
                    else:
                        st.toast(f"NO MATCH FOUND")
                        st.session_state.matching_results = False
                        loading_placeholder.success("Payment Accepted")

                    if st.session_state.matching_results is not None:
                        if ciphertext_path:
                            # Read and display ciphertext
                            if os.path.exists(ciphertext_path):
                                with open(ciphertext_path, "rb") as f:
                                    ciphertext_data = f.read()
                                    
                                # Display hex preview in expandable section
                                hex_preview = ciphertext_data[:256].hex()
                                # Format hex in lines of 64 characters (32 bytes per line)
                                formatted_hex = '\n'.join([hex_preview[i:i+64] for i in range(0, len(hex_preview), 64)])

                                hex_code = formatted_hex + "\n..." if len(ciphertext_data) > 256 else formatted_hex
                                caption = f"Showing first {min(256, len(ciphertext_data))} bytes of {len(ciphertext_data)} total bytes"

                                with ciphertext_display.container():
                                    st.markdown("### Ciphertext")
                                    st.code(hex_code, language="text")
                                    st.caption(caption)

                                # Remember this so it keeps rendering on future reruns,
                                # and so the "Secure Pattern Matching" button stays hidden
                                st.session_state.show_ciphertext = True
                                st.session_state.ciphertext_content = {
                                    "hex": hex_code,
                                    "caption": caption,
                                }
                   
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