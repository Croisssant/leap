import streamlit as st
import subprocess
import os
import tempfile
import re

from streamlit_extras.let_it_rain import rain

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

# 1. Page Configuration
st.set_page_config(
    page_title="LEAP",
    layout="wide"
)

st.title("Lean and Efficient Homomorphic Multi-Pattern Matching")
st.write("A homomorphic encryption-based pattern matching.")

# 2. Sidebar Configuration Parameters
st.sidebar.header("⚙️ Execution Parameters")

# Note: Threshold input - will be validated against pattern length later
threshold = st.sidebar.number_input(
    "Matching Threshold", 
    min_value=-1, 
    max_value=100, 
    value=-1, 
    step=1,
    help="Matching threshold (-1 = use pattern length for exact matching, or set to pattern length or lower for approximate matching)"
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 📖 Pattern Format")
st.sidebar.markdown("- One pattern per line")
st.sidebar.markdown("- All patterns must have same length")
st.sidebar.markdown("- Use `*` for wildcard matching")
st.sidebar.markdown("- Example: `viv*mus.`")

# 3. Text Input Fields in Main Layout - Two Column Layout
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📝 Text Owner (Party 1)")
    text_input = st.text_area(
        "Enter the text to search in:",
        value="Lorem ipsum dolor sit amet, consectetur adipiscing elit vivamus.",
        width=800,
        height=200,
        help="Enter the source text where patterns will be searched"
    )

with col2:
    st.subheader("🔍 Pattern Owner (Party 2)")
    pattern_input = st.text_area(
        "Enter patterns to search for (one per line):",
        value="vivamus.\nvivaaus.",
        width=800,
        height=200,
        help="Enter one or more patterns. All patterns must have the same length."
    )

# 4. Execution Logic
if st.button("🚀 Run Pattern Matching", type="primary", use_container_width=True):
    # Input validation
    if not text_input or not text_input.strip():
        st.error("❌ Please enter some text to search in.")
    elif not pattern_input or not pattern_input.strip():
        st.error("❌ Please enter at least one pattern to search for.")
    else:
        # Parse patterns
        patterns = [line.strip() for line in pattern_input.strip().split('\n') if line.strip()]
        
        if not patterns:
            st.error("❌ Please enter at least one valid pattern.")
        else:
            # Check if all patterns have the same length
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
                    
                    with st.spinner("🔐 Executing secure pattern matching on encrypted data..."):
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
                                    st.toast(f"MATCH FOUND", icon='✅')
                               
                                else:
                                    st.toast(f"NO MATCH FOUND", icon='❌')
                                
                                # Show ciphertext information if exported - Two Column Layout
                                if (ciphertext_path or pattern_plaintext_path):
                                    st.markdown("---")
                                    st.subheader("🔐 Encrypted Data Information")
                                    
                                    # Create two columns for Text Owner and Pattern Owner results
                                    result_col1, result_col2 = st.columns(2)
                                    
                                    # Left Column: Text Owner - Encrypted Text Ciphertext
                                    with result_col1:
                                        if ciphertext_path:
                                            st.markdown("### Encrypted Ciphertext")
                                            # Read and display ciphertext
                                            if os.path.exists(ciphertext_path):
                                                with open(ciphertext_path, "rb") as f:
                                                    ciphertext_data = f.read()
                                                
                                                # Display hex preview in expandable section
                                             
                                                hex_preview = ciphertext_data[:512].hex()
                                                # Format hex in lines of 64 characters (32 bytes per line)
                                                formatted_hex = '\n'.join([hex_preview[i:i+64] for i in range(0, len(hex_preview), 64)])
                                                st.code(formatted_hex + "\n..." if len(ciphertext_data) > 512 else formatted_hex, language="text")
                                                st.caption(f"Showing first {min(512, len(ciphertext_data))} bytes of {len(ciphertext_data)} total bytes")
                                            
                                            # Display ciphertext metadata
                                            if ciphertext_size:
                                                size_kb = ciphertext_size / 1024
                                                st.metric("Size", f"{size_kb:.2f} KB")
                                            if ciphertext_noise_budget is not None:
                                                st.metric("Noise Budget", f"{ciphertext_noise_budget} bits")
                                            st.metric("Compression", "ZSTD")
                                    
                                    # Right Column: Pattern Owner - Encoded Patterns Batch Plaintext
                                    with result_col2:
                                        if pattern_plaintext_path:
                                            st.markdown("### Encoded Plaintext")

                                              # Read and display pattern plaintext
                                            if os.path.exists(pattern_plaintext_path):
                                                with open(pattern_plaintext_path, "rb") as f:
                                                    pattern_pt_data = f.read()
                                                
                                                # Display hex preview in expandable section
                                          
                                                hex_preview = pattern_pt_data[:512].hex()
                                                # Format hex in lines of 64 characters (32 bytes per line)
                                                formatted_hex = '\n'.join([hex_preview[i:i+64] for i in range(0, len(hex_preview), 64)])
                                                st.code(formatted_hex + "\n..." if len(pattern_pt_data) > 512 else formatted_hex, language="text")
                                                st.caption(f"Showing first {min(512, len(pattern_pt_data))} bytes of {len(pattern_pt_data)} total bytes")
                                            
                                            # Display pattern plaintext metadata
                                            if pattern_plaintext_size:
                                                size_kb = pattern_plaintext_size / 1024
                                                st.metric("Size", f"{size_kb:.2f} KB")
                                            st.metric("Type", "Encoded")
                                            if pattern_batch_count:
                                                st.metric("Patterns in Batch", pattern_batch_count)
                                            
                                    
                                    st.info("💡 **Note:** The text is encrypted (ciphertext), while patterns are encoded as plaintexts for homomorphic operations.")


                                  # Display Results
                                    st.markdown("---")
                                    st.subheader("📊 Pattern Matching Results")
                                    
                                    # Display match result with visual feedback
                                    if match_found:
                                        st.success(f"✅ **MATCH FOUND!** (result = {result_value})")
                                        st.balloons()
                                    else:
                                        st.error(f"❌ **NO MATCH FOUND** (result = {result_value})")
                                        rain(emoji="❌", font_size=54, animation_length=1)
                                    
                                    # Display search details
                                    col1, col2, col3 = st.columns(3)
                                    with col1:
                                        st.metric("Text Length", len(text_input))
                                    with col2:
                                        st.metric("Pattern Length", len(patterns[0]))
                                    with col3:
                                        st.metric("Patterns Searched", len(patterns))
                                    
                                    # Display matching mode and threshold
                                    col1, col2 = st.columns(2)
                                    with col1:
                                        st.info(f"🔧 **Matching Mode:** {matching_mode.capitalize()}")
                                    with col2:
                                        st.info(f"🎯 **Threshold:** {threshold}")
                                    
                                    # Show patterns searched
                                    with st.expander("🔍 View Patterns Searched", expanded=False):
                                        for i, pattern in enumerate(patterns, 1):
                                            st.code(f"{i}. {pattern}", language="text")

                                                                        
                                # Show full execution output
                                with st.expander("📋 View Full Execution Output", expanded=False):
                                    st.code(output, language="text")
                                
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
 