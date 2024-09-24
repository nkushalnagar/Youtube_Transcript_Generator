import pandas as pd
import time
import os
from selenium import webdriver # for interacting with website
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import re
from openai import OpenAI
import aspose.words as aw
import creds

title = ""

client = OpenAI(
    api_key = creds.api_key
)

def remove_special_characters_from_string(string):
    string_list = []
    for i in string:
        if i.isalnum() or i == " ":
            string_list.append(i)

    new_string = "".join(string_list)

    return new_string

def open_url_in_chrome(url):
    #print(f'Opening {url}')
    driver = webdriver.Chrome()
    driver.get(url)
    time.sleep(3)
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    return driver

def dismiss_offer(driver):
    # Click 'dismiss'
    driver.find_element(By.XPATH,"//*[@id='dismiss-button']/yt-button-shape").click()

def get_transcript(driver):
    try:
        print('Dismissing offer')
        dismiss_offer(driver)
    except:
        print("No offer to dismiss")
    
    print("Opening transcript")
    # Click 'More actions'
    driver.find_element(By.XPATH, "/html/body/ytd-app/div[1]/ytd-page-manager/ytd-watch-flexy/div[5]/div[1]/div/div[2]/ytd-watch-metadata/div/div[4]/div[1]/div/ytd-text-inline-expander/tp-yt-paper-button[1]").click() 
        
    # Click 'Open transcript'
    driver.find_element(By.XPATH, "/html/body/ytd-app/div[1]/ytd-page-manager/ytd-watch-flexy/div[5]/div[1]/div/div[2]/ytd-watch-metadata/div/div[4]/div[1]/div/ytd-text-inline-expander/div[2]/ytd-structured-description-content-renderer/div/ytd-video-description-transcript-section-renderer/div[3]/div/ytd-button-renderer/yt-button-shape/button").click()
    time.sleep(15)

    # Get all transcript text
    print("Copying transcript ")
    transcript_element = driver.find_element(By.XPATH,"//*[@id='body']/ytd-transcript-segment-list-renderer")
    transcript = transcript_element.text

    return transcript

def get_title(driver):
    video_element = driver.find_element(By.XPATH, "/html/body/ytd-app/div[1]/ytd-page-manager/ytd-watch-flexy/div[5]/div[1]/div/div[2]/ytd-watch-metadata/div/div[1]/h1/yt-formatted-string")
    title = video_element.text
    title = remove_special_characters_from_string(title)
    title = title.replace(" ", "_")
    
    return title

def transcript2df(transcript):
    transcript = transcript.split('\n')
    transcript_timestamps = transcript[::2]
    
    transcript_text = transcript[1::2]
    df = pd.DataFrame({'timestamp':transcript_timestamps, 
                   'text':transcript_text})
    
    return df

def webscrape_transcript(url):
    global title

    driver = open_url_in_chrome(url)
    
    transcript = get_transcript(driver)

    title = get_title(driver)

    driver.close()
    
    df = transcript2df(transcript)

    return df

#takes dataframe of transcript and uses chatGPT LLM to analyze who's speaking when and return a properly formatted transcript in the form of string
def compile_new_transcript(scraped_df,title):
    #create a csv version of the transcript
    #scraped_df.to_csv(title + '.csv', index=False)
    text_transcript = scraped_df.to_string()
    completion = client.chat.completions.create(
        model = "gpt-4o-2024-08-06",
        messages = [
            {"role":"user","content":"Hello! Can you help me format this transcript so that it shows who is speaking at which point in time? The first string of text are the timestamps and the second are the respective texts - they should match up. Reformat this so it is looks professional and include the title, who is speaking at the top, and if you can when and where this is happening at the top." + text_transcript + "The title of this video which can be found on youtube is " + title}
        ]   

    )
    return completion.choices[0].message.content

def write_text_file(final_transcript, title):
    with open(title + '.txt', 'w') as file:
        file.write(final_transcript)
    #create a word doc -- 
    #doc = aw.Document(title + ".txt")
    #doc.save(title + ".docx")

def main():
    text_file_question = input("Are you inputting a text file(Y or N): ")

    if (text_file_question == "Y"):
        link_file = input("Enter the name of your text file here: ")

        # Using readlines()
        file1 = open(link_file, 'r')
        print(file1)
        Lines = file1.readlines()
        print(Lines)

        # Strips the newline character (String on each new line)
        for line in Lines:
            url = line.strip()
            final_df = webscrape_transcript(url)
            final_transcript = compile_new_transcript(final_df,title)
            write_text_file(final_transcript,title)        

    else:
        url = input("Enter Youtube Video Link: ")
        final_df = webscrape_transcript(url)
        final_transcript = compile_new_transcript(final_df,title)
        write_text_file(final_transcript,title)

    return "Finished:)"

main()
