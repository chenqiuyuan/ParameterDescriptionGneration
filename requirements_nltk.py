import nltk
from IPython.display import display
nltk_data_path = nltk.data.path
print("NLTK data will be downloaded in this path:")
display(nltk_data_path)


nltk.download('averaged_perceptron_tagger')
