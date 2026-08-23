import os
import keras
from keras.models import load_model
import streamlit as st
import tensorflow as tf
import numpy as np


model=load_model(r'C:\Users\DELL\Downloads\Model\road_damage_and_defect_recog_model_v2.h5') 
#replace the "C:\Users\DELL\Downloads\Model\road_damage_and_defect_recog_model_v2.h5" with your directory
road_defects=['D00', 'D10', 'D20', 'D30', 'D40', 'D50', 'D60', 'D70', 'D80', 'D90']
st.header('Road Damage and Defect Classification Model')

def classify_images(image_path):
    input_image = tf.keras.utils.load_img(image_path, target_size=(180,180))
    input_image_array= tf.keras.utils.img_to_array(input_image)
    input_image_exp_dim = tf.expand_dims(input_image_array,0)

    predictions = model.predict(input_image_exp_dim)
    result= tf.nn.softmax(predictions[0])
    outcome = f'The Image belongs to {road_defects[np.argmax(result)]} with a score of {np.max(result) * 100:.2f}%'
    return outcome

uploaded_file = st.file_uploader('Upload an Image', type=['jpg', 'jpeg', 'png'])
if uploaded_file is not None:
    if not os.path.exists('upload'):
        os.makedirs('upload')
    image_path = os.path.join('upload', uploaded_file.name)
    with open(image_path, 'wb') as f:
        f.write(uploaded_file.getbuffer())

    st.image(uploaded_file, width =200)
    result=classify_images(image_path)
    st.markdown(result)
