import streamlit as st
import datetime

st.title("Streamlit Test App 🚀")

st.write("If you see this, Streamlit is awake and listening.")

name = st.text_input("What's your name?")
if name:
    st.success(f"Nice to meet you, {name}!")

number = st.slider("Choose a number", 0, 100, 50)
st.write(f"You chose: {number}")

if st.button("Show current time"):
    st.info(f"Current server time: {datetime.datetime.now()}")