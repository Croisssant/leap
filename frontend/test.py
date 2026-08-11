import streamlit as st
import os

# Configure the page layout
st.set_page_config(page_title="Shopping Card Example", layout="centered")

# 1. Get the directory that this app.py file actually lives in
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 2. Build the absolute path to your image
IMAGE_PATH = os.path.join(SCRIPT_DIR, "images", "vape.jpg")

# Custom CSS for a polished, modern e-commerce card
st.markdown(
    """
    <style>
    /* Style all bordered containers */
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
        font-size: 20px;
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

# App Title
st.title("🛍️ Streamlit Product Showcase")
st.write("Below is a sample highly-scannable shopping item card.")

# Create columns to constrain the card width
col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    # Use Streamlit's bordered container to properly wrap all elements
    with st.container(border=True, key="item-card"):
        # 1. Product Image (Using a placeholder image)
        st.image(
            IMAGE_PATH,
            use_container_width=True,
        )

        # 2. Product Text Details
        st.markdown('<div class="product-title">Classic Red Sneakers</div>', unsafe_allow_html=True) # Fixed
        st.markdown('<div class="product-price">$89.99</div>', unsafe_allow_html=True) # Fixed
        st.markdown(
            '<div class="product-desc">Lightweight, breathable mesh upper with responsive cushioning for all-day comfort. Perfect for running or casual wear.</div>',
            unsafe_allow_html=True, # Fixed
        )

        # 3. Interactive Buy Button
        if st.button("Buy Now", key="buy_btn"):
            st.success("🎉 Added to cart successfully!")