import streamlit as st
import subprocess
import os
import tempfile
import re

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
    page_icon="🦈",
    layout="centered"
)

st.title("Lean and Efficient Homomorphic Multi-Pattern Matching")
st.write("A homomorphic encryption-based pattern matching.")

# 2. Sidebar Configuration Parameters
st.sidebar.header("⚙️ Execution Parameters")
threshold = st.sidebar.number_input(
    "Matching Threshold", 
    min_value=0, 
    max_value=100, 
    value=8, 
    step=1,
    help="Set to pattern length for exact matching, or lower for approximate matching"
)
quiet_mode = st.sidebar.checkbox("Quiet Mode", value=True, help="Suppress verbose debug output")

st.sidebar.markdown("---")
st.sidebar.markdown("### 📖 Pattern Format")
st.sidebar.markdown("- One pattern per line")
st.sidebar.markdown("- All patterns must have same length")
st.sidebar.markdown("- Use `*` for wildcard matching")
st.sidebar.markdown("- Example: `viv*mus.`")

# 3. Text Input Fields in Main Layout
st.subheader("📝 Input Text")
text_input = st.text_area(
    "Enter the text to search in:",
    value="Lorem ipsum dolor sit amet, consectetur adipiscing elit vivamus.",
    height=100,
    help="Enter the source text where patterns will be searched"
)

st.subheader("🔍 Search Patterns")
pattern_input = st.text_area(
    "Enter patterns to search for (one per line):",
    value="vivamus.\nvivaaus.",
    height=120,
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
                        if quiet_mode:
                            cmd.append("--quiet")
                        
                        try:
                            # Run the binary and capture standard output/error
                            result = subprocess.run(
                                cmd,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                text=True,
                                check=True
                            )
                            
                            # Parse the output to extract match result
                            output = result.stdout
                            match_found = False
                            result_value = None
                            matching_mode = "unknown"
                            
                            # Look for the final result line
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
                            
                            # Display Results
                            st.markdown("---")
                            st.subheader("📊 Pattern Matching Results")
                            
                            # Display match result with visual feedback
                            if match_found:
                                st.success(f"✅ **MATCH FOUND!** (result = {result_value})")
                                st.balloons()
                            else:
                                st.error(f"❌ **NO MATCH FOUND** (result = {result_value})")
                            
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
                            st.error("❌ The C++ binary encountered an error during execution.")
                            with st.expander("🐛 Error Details", expanded=True):
                                st.code(e.stderr, language="text")
                        except FileNotFoundError:
                            st.error(f"❌ Executable not found at: `{EXECUTABLE_PATH}`")
                            st.info(f"💡 **Project Root:** `{PROJECT_ROOT}`")
                            st.info("💡 **Tip:** Build the project first using:\n```bash\ncd " + PROJECT_ROOT + "\ncmake --build build\n```")
 