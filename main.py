import pandas as pd
import time
import os
from selenium import webdriver # for interacting with website
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import re
from openai import OpenAI
import aspose.words as aw
import keys

title = ""
question = "Hello! Can you help me format this transcript so that it shows who is speaking at which point in time? The first string of text are the timestamps and the second are the respective texts - they should match up. Ensure you include all text in the output - the output should be the entire transcript, no shortcuts. Clump text together and don't feel the need to repeat speaker title (name) until there is a speaker change. Also, please provide accurate timestamps consistantly. Note that the speaker might be referenced after they have spoken in words such as Thank you Steven or a similar phrase, but might not be properly introduced so do not get tricked by this. Try to be as accurate as possible when identifying speakers and use surrounding text as context. Output should also look professional (hopefully you have consistent definition of this that you can follow) and include the title, who is speaking at the top, and if you can when and where this is happening at the top. Please don't include a personalized message such as Yes, I can do this for you in response to my question."
question_2 = "Hello! Can you help me format this transcript so that it shows who is speaking at which point in time? The first string of text are the timestamps and the second are the respective texts - they should match up. Ensure you include all text in the output - the output should be the entire transcript, no shortcuts. Clump text together and don't feel the need to repeat speaker title (name) until there is a speaker change. Also, please provide accurate timestamps consistantly. Note that the speaker might be referenced after they have spoken in words such as Thank you Steven or a similar phrase, but might not be properly introduced so do not get tricked by this. Try to be as accurate as possible when identifying speakers and use surrounding text as context. Output should also look professional (hopefully you have consistent definition of this that you can follow). Please don't include a personalized message such as Yes, I can do this for you in response to my question. Also, this transcript is a continuation or ending of a longer video so don't bother including the details at the top."
client = OpenAI(
    api_key = keys.key_api
)

def split_string(string):
        return string[:119000], string[119000:]


# Remove special characters from string, allows to reformat title in future
def remove_special_characters_from_string(string):
    string_list = []
    for i in string:
        if i.isalnum() or i == " ":
            string_list.append(i)

    new_string = "".join(string_list)

    return new_string

# Use webdriver to open link in chrome and parse with beatifulsoup
def open_url_in_chrome(url):
    print('Opening ' + url)
    driver = webdriver.Chrome()
    driver.get(url)
    time.sleep(3)
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    return driver

#Dismiss pop up offer on Youtube, this offer has been known to change at some point, code will thus need to be modified here
def dismiss_offer(driver):
    # Click 'dismiss'
    driver.find_element(By.XPATH,"//*[@id='dismiss-button']/yt-button-shape").click()
    time.sleep(3)

#Click the necessary buttons to eventually get the auto-generated English transcript for the Youtube video
def get_transcript(driver):
    
    #If pop-up exists click if not continue
    try:
        print('Dismissing offer')
        dismiss_offer(driver)
    except:
        print("No offer to dismiss")
    
    print("Opening transcript")
    # Click 'More actions'
    time.sleep(15)
    driver.find_element(By.XPATH, "//*[@id='expand']").click() 
    time.sleep(50)
    # Click 'Open transcript'
    driver.find_element(By.XPATH, "//*[@aria-label='Show transcript']").click()
    time.sleep(15)

    # Get all transcript text
    print("Copying transcript ")
    transcript_element = driver.find_element(By.XPATH,"//*[@id='body']/ytd-transcript-segment-list-renderer")
    transcript = transcript_element.text

    return transcript

# Gets title of video
def get_title(driver):
    video_element = driver.find_element(By.XPATH, "//*[@id='title']/h1/yt-formatted-string")
    title = video_element.text
    title = remove_special_characters_from_string(title)
    title = title.replace(" ", "_")
    
    return title

# Creates a dataframe with timestamps and text from transcript
def transcript2df(transcript):
    transcript = transcript.split('\n')
    transcript_timestamps = transcript[::2]
    
    transcript_text = transcript[1::2]
    df = pd.DataFrame({'timestamp':transcript_timestamps, 
                   'text':transcript_text})
    
    return df

# Uses previous functions to return df of transcript of link provided
def webscrape_transcript(url):
    global title

    driver = open_url_in_chrome(url)
    
    transcript = get_transcript(driver)

    title = get_title(driver)

    driver.close()
    
    df = transcript2df(transcript)

    #create a csv version of the transcript
    #df.to_csv(title + '.csv', index=False)

    string_df = df.to_string()

    print(len(string_df))

    return string_df

# Takes dataframe of transcript and uses chatGPT LLM to analyze who's speaking when and return a properly formatted transcript in the form of string
def compile_new_transcript(text_transcript,title,question):

    completion = client.chat.completions.create(
        model = "gpt-4o-2024-08-06",
        messages = [
            {"role":"user","content": question + text_transcript + "The title of this video which can be found on youtube is " + title}
        ]   

    )
    return completion.choices[0].message.content

# Write new text file named the title of video and containing final transcript
def write_text_file(final_transcript, title):
    with open(title + '.txt', 'w') as file:
        file.write(final_transcript)
    #create a word doc -- 
    #doc = aw.Document(title + ".txt")
    #doc.save(title + ".docx")

# Take input as either a txt file with links or one link and output .txt transcripts
def main():
    text_file_question = input("Are you inputting a text file(Y or N): ")

    if (text_file_question == "Y"):
        link_file = input("Enter the name of your text file here: ")

        # Using readlines()
        file1 = open(link_file, 'r')
        Lines = file1.readlines()

        # Strips the newline character (String on each new line)
        for line in Lines:
            url = line.strip()
            text_transcript = webscrape_transcript(url)
            if len(text_transcript)>119000:
                a,b = split_string(text_transcript)    
                final_transcript_a,final_transcript_b = compile_new_transcript(a,title,question),compile_new_transcript(b,title,question_2)
                write_text_file(final_transcript_a + final_transcript_b,title)
            else:
                final_transcript = compile_new_transcript(text_transcript,title,question)
                write_text_file(final_transcript,title)        

    else:
        url = input("Enter Youtube video link: ")
        text_transcript = webscrape_transcript(url)
        if len(text_transcript)>119000:
                a,b = split_string(text_transcript)    
                final_transcript_a,final_transcript_b = compile_new_transcript(a,title,question),compile_new_transcript(b,title,question_2)
                write_text_file(final_transcript_a + final_transcript_b,title)
        else:
                final_transcript = compile_new_transcript(text_transcript,title,question)
                write_text_file(final_transcript,title)

    return "Finished:)"

main()
