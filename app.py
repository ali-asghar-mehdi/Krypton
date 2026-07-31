import streamlit as st
import requests
import io
from PIL import Image

# Setup Tabs at the top of the app
tab1, tab2 = st.tabs(["💬 Chatbot", "🎨 Image Generator"])

with tab1:
    st.write("Your main chatbot code goes here!")

with tab2:
    st.header("Generate Images with AI")
    image_prompt = st.text_input("Describe the image you want to create:")
    
    if st.button("Generate Image"):
        if image_prompt:
            st.info("Generating your image... please wait!")
            
            # Example API call to a free Hugging Face model
            API_URL = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-2-1"
            # Add your Hugging Face API key in Streamlit Secrets as HF_TOKEN
            headers = {"Authorization": f"Bearer {st.secrets.get('HF_TOKEN', '')}"}
            
            response = requests.post(API_URL, headers=headers, json={"inputs": image_prompt})
            
            if response.status_code == 200:
                image_bytes = response.content
                image = Image.open(io.BytesIO(image_bytes))
                st.image(image, caption=image_prompt, use_container_width=True)
            else:
                st.error("Could not generate image. Please check your API key or try again later.")
                
