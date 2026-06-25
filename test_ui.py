import streamlit as st

st.set_page_config(page_title="Test", layout="wide")

st.markdown("""
<style>
.test-card {
    border: 1px solid rgba(148, 163, 184, 0.18);
    border-radius: 16px;
    background: linear-gradient(145deg, rgba(15, 23, 42, 0.86), rgba(30, 41, 59, 0.58));
    padding: 15px;
    color: white;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="test-card">
    <h3>Test Card</h3>
    <p>If you see this styled, HTML rendering works!</p>
</div>
""", unsafe_allow_html=True)

st.write("If the card above is styled with dark background, the UI is working correctly.")
