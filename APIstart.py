"""
Edited by Andrej Kruzliak,
based on Google API v3 free tutorial on how to setup
your first Google API python script
"""

from __future__ import print_function
import pickle
import os.path, io
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.http import MediaIoBaseDownload
import re
from extract_code import pdfparser

SCOPES = ['https://www.googleapis.com/auth/drive']
poetryStrengthList = []

def isPoetry(file_name):
    """
    This function takes a .txt file, traverses it and tries to decide,
    whether the content is, or is not a piece of poetry based on a 
    "PowerNewLine" which is just the number of ',\n' or ', \n' groups
    of characters, which are typical for a poetry format. This fnc
    does not comprehensively understand the text, it merely checks
    the formatting.

    Params:
    file_name : you guessed it, the name of the file (.txt)
    """
    numOfCommas = 0
    numOfNewlines = 0
    poetryRatio = 0
    powerPoetryRatio = 0
    numOfPowerNewLines = 0
    previousChar = None
    prePreviousChar = None
    with open(file_name) as f:
        data = f.read()
        
        for c in data:
            if previousChar is None:
                previousChar = c
            if c == ',':
                numOfCommas += 1
            elif c == '\n':
                numOfNewlines += 1
            # checks for the PowerNewLine combination of characters
            if (previousChar == ',' and c == '\n') or (prePreviousChar == ',' and previousChar == ' ' and c == '\n'):
                numOfPowerNewLines += 1  # for ignoring prosaic texts with lots of commas
            prePreviousChar = previousChar
            previousChar = c
            
    # print("Number of commas: ", numOfCommas)
    # print("Number of newline chars: ", numOfNewlines)
    # print("Number of POWER LINES: ", numOfPowerNewLines)
    
    if numOfNewlines > 4: # ignoring short poetry drafts and short shopping lists
        poetryRatio = (numOfCommas/numOfNewlines)
        if numOfPowerNewLines != 0:
            powerPoetryRatio = (numOfCommas/numOfPowerNewLines)
            print("Power Poetry Ratio: ", powerPoetryRatio)
        print("Poetry Ratio: ", poetryRatio)
        
        poetryStrengthList.append((poetryRatio, powerPoetryRatio)) 
        if  powerPoetryRatio >= 1:
            return True
        else:
            return False
    else:
        print("Poetry Ratio: ", poetryRatio)
        print("Power Poetry Ratio: ", powerPoetryRatio)
        poetryStrengthList.append((poetryRatio, powerPoetryRatio)) 
        return False

def spaceDestroyer(file_name):
    """
    Takes the name file and returns the name file back, with
    spaces replaced with underscore. (' ' replaced with '_')

    Params:
    file_name : you guessed it, the name of the file
    """
    counter = 0
    for c in file_name:
        if counter == 0:
            new_name = c
            counter += 1
            continue
        if c == ' ':
            new_name = new_name + "_"
        else:
            new_name = new_name + c
        counter += 1
    return new_name

def send2download(fileId, mimeType, serviceType):
    """
    Params:
    fileId: the long file ID obtained from the Google API
    mimeType: the official name of the document type (google MIME types)
    serviceType: jsut the config of your build type, such as "service = build('drive', 'v3', credentials=creds)" 
    """
    request = serviceType.files().export_media(fileId=fileId, mimeType=mimeType)  
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
        print("Download %d%%." % int(status.progress() * 100))
    fh.seek(0)  # wtf?

    return fh


def main():
    
    """
    Lists and then downloads all the documents from the dedicated drive as .txt file.
    Then each .txt file is traversed and classified based on "isPoetry()" classifier.
    Then only positively classified files byt "isPoetry()" are exported via the 
    Google API v3 as .pdf files and saved into the /from_drive folder.
    """
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'client_secret.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('drive', 'v3', credentials=creds)

    """
    the pageSize is set to maximum (1000), although its a better practice to set it to 100 and then
    traverse the files via "nexPageToken"
    The 'q' stands for query and specifies what to look for in the Drive.
    """
    results = service.files().list(pageSize = 1000, q="mimeType='application/vnd.google-apps.document'", spaces='drive',
                                          fields='nextPageToken, files(id, name)',
                                         ).execute()

    items = results.get('files', [])  # returns [], when a file with that key doesnt exist

    if not items:
        print('No files found.')
    else:
        print('Number of queued files: ', len(items))
        for item in items:
            print('Saving file {0}, with and ID {1}'.format(item['name'], item['id']))

            fh = send2download(fileId=item['id'], mimeType = 'text/plain', serviceType=service)
            new_name = spaceDestroyer(item['name'])  # returns name with '_' instead of ' '

            with open(os.path.join('./from_drive', new_name), 'wb') as f:
                f.write(fh.read())
                f.close
            
            path_name = 'from_drive/' + new_name 
            print("PATH NAME: ", path_name)
            if(isPoetry(path_name)):
                fh = send2download(fileId=item['id'], mimeType = 'application/pdf', serviceType=service)
                with open(os.path.join('./from_drive/poetry', new_name), 'wb') as f:
                    f.write(fh.read())
                    f.close

        minPR = float('Inf')
        maxPR = -float('Inf')
        minPPR = float('Inf')
        maxPPR = -float('Inf')
        results = open('results.txt', 'w')
        for tup in poetryStrengthList:
            print('pr: {0}, PPR: {1}'.format(tup[0], tup[1]))
            results.write('pr: {0}, PPR: {1}\n'.format(tup[0], tup[1]))
            if tup[0] != 0:
                if tup[0] < minPR:
                    minPR = tup[0]
                if tup[0] > maxPR:
                    maxPR = tup[0]
            if tup[1] != 0:
                if tup[1] < minPPR:
                    minPPR = tup[1]
                if tup[1] > maxPPR:
                    maxPPR = tup[1]
        
        # writes a 
        print("Max and Min of poetryRatio: ", maxPR, minPR)
        print("Max and Min of POWERpoetryRatio: ", maxPPR, minPPR)
        results.write('Max: {0} and Min: {1} of poetryRatio.\n'.format(maxPR, minPR))
        results.write('Max: {0} and Min: {1} of POWERpoetryRatio.\n'.format(maxPPR, minPPR))

if __name__ == '__main__':
    main()
