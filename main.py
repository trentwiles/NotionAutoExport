import requests
import time
import zipfile
import os
from dotenv import load_dotenv
import shutil

load_dotenv()

LOGIN_TOKENS = {"token_v2": os.getenv("LOGIN_TOKEN")}
FILE_TOKENS = {"file_token": os.getenv("FILE_TOKEN")}
# Space ID of your notion space
SPACE_ID = os.getenv("SPACE_ID")
# ID of the block, can be found in the notion url
BLOCK_ID = os.getenv("BLOCK_ID")
# Directory to drop the zip file in
DIRECTORY = "files"
OUTPUT_DIRECTORY = f"{DIRECTORY}/output"
# Prefix for debug messages
CLI_PREFIX = "[NOTION]:"

r = requests.post("https://www.notion.so/api/v3/enqueueTask",
                  json=
                      {"task":{"eventName":"exportBlock","request":{"block":{"id": BLOCK_ID,"spaceId": SPACE_ID},"recursive":True,"exportOptions":{"exportType":"html","timeZone":"America/New_York","locale":"en","collectionViewExportType":"currentView","flattenExportFiletree":False,"preferredViewMap":{}},"shouldExportComments":False}}},
                    cookies=LOGIN_TOKENS
                  )

if r.status_code != 200:
    raise ValueError("Error: non-200 HTTP status (" + str(r.status_code) + ")")


task = r.json()["taskId"]
print(f"{CLI_PREFIX} Begining export... ({task})")

exportURL = ""

while True:
    x = requests.post("https://www.notion.so/api/v3/getTasks", json={"taskIds": [task]}, cookies=LOGIN_TOKENS)
    
    result = x.json()["results"][0]["state"]
    
    if result == "success":
        exportURL = x.json()["results"][0]["status"]["exportURL"]
        print(f"{CLI_PREFIX} Success, file(s) stored at {exportURL}")
        break
    elif result == "in_progress":
        print(f"{CLI_PREFIX} Exporting... this may take a few minutes, spending on the size of your page. Waiting 15 seconds before checking again...")
    else:
        print(f"{CLI_PREFIX} Unknown status ({result}) while exporting. Below is debug information.")
        print(x.text)
    time.sleep(15)

filesReq = requests.get(exportURL, cookies=FILE_TOKENS, stream=True)

storage_location = f'{DIRECTORY}/{str(round(time.time()))}.zip'
# download zip file into storage directory
with open(storage_location, 'wb') as file:
            for chunk in filesReq.iter_content(chunk_size=8192):
                file.write(chunk)
print(f"{CLI_PREFIX} Downloaded zip file from CDN to {storage_location}")
                
# before we unzip, delete the contents of the output directory
for filename in os.listdir(OUTPUT_DIRECTORY):
    if filename == "README.md":
        continue
    file_path = os.path.join(OUTPUT_DIRECTORY, filename)
    try:
        if os.path.isfile(file_path) or os.path.islink(file_path):
            os.unlink(file_path)
        elif os.path.isdir(file_path):
            shutil.rmtree(file_path)
    except Exception as e:
        print('Failed to delete %s. Reason: %s' % (file_path, e))

print(f"{CLI_PREFIX} Cleaned output directory ({OUTPUT_DIRECTORY})")

# zip file is saved, now unzip it
with zipfile.ZipFile(storage_location, 'r') as zip_ref:
    zip_ref.extractall(OUTPUT_DIRECTORY)

print(f"{CLI_PREFIX} Unziped file(s) to {OUTPUT_DIRECTORY}")